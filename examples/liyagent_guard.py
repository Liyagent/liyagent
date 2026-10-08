"""Use Liyagent as the policy decision point for your own agent's tools.

Your agent calls its own tools, retriever and memory, so Liyagent never sees
those calls directly. This module asks Liyagent's decision API before each
call, and screens what comes back. The policies, guardrails, data rules and
approval settings you configure in Liyagent then apply here as well.

The module uses only the Python standard library. Copy it into your project.

    guard = Guard("https://liyagent.example.com", token=os.environ["LIYAGENT_AGENT_TOKEN"])

    @guard.tool(writes=True)            # checks before and after the call
    def refund(order: str, amount: int) -> str: ...

    passages = guard.retrieval("kb", "\\n".join(docs))    # screened text
    note = guard.memory_write("notes", note)             # redacted text
    guard.handoff("billing-bot", summary)                # checked hand-off

A refused call raises Denied. A call that needs a person's approval raises
PendingApproval, which carries the approval ID. Call again with approval_id
once the request is approved.

The guard fails closed. If Liyagent cannot be reached, the call is not made.
"""

from __future__ import annotations

import functools
import inspect
import json
import urllib.error
import urllib.request
from typing import Any, Callable


class Denied(PermissionError):
    def __init__(self, decision: dict[str, Any]):
        super().__init__(f"{decision.get('deciding_policy')}: {decision.get('reason')}")
        self.decision = decision


class PendingApproval(Denied):
    @property
    def approval_id(self) -> str:
        return self.decision["approval_id"]


def _http_post(url: str, headers: dict[str, str], body: dict) -> dict:
    req = urllib.request.Request(url, json.dumps(body).encode(), headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:     # 401/403/422: never "allow"
        raise Denied({"deciding_policy": f"http_{e.code}",
                      "reason": e.read()[:300].decode(errors="replace")}) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # Unreachable is a refusal too (fail closed), and a Denied one, so
        # the framework wrappers tell the model rather than crash.
        raise Denied({"deciding_policy": "unreachable", "reason": str(e)[:300]}) from e


class Guard:
    def __init__(self, base_url: str, token: str, post: Callable = _http_post):
        self.url = base_url.rstrip("/") + "/api/gateway/v1/decide"
        self.token, self._post = token, post

    def decide(self, phase: str, name: str, **body: Any) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.token}",
                   "Content-Type": "application/json"}
        out = self._post(self.url, headers, {"phase": phase, "name": name, **body})
        if out.get("decision") == "pending_approval":
            raise PendingApproval(out)
        if out.get("decision") != "allow":
            raise Denied(out)
        return out

    def _text(self, phase: str, name: str, text: str) -> str:
        return self.decide(phase, name, text=text).get("redacted", {}).get("text", text)

    def retrieval(self, name: str, text: str) -> str:
        return self._text("retrieval", name, text)

    def memory_write(self, name: str, text: str, approval_id: str = "") -> str:
        extra = {"approval_id": approval_id} if approval_id else {}
        out = self.decide("memory_write", name, text=text, **extra)
        return out.get("redacted", {}).get("text", text)

    def handoff(self, agent: str, text: str) -> str:
        return self._text("handoff", agent, text)

    def before(self, name: str, arguments: dict, *, writes: bool = False,
               approval_id: str = "") -> dict:
        """pre_tool: the arguments as they may be sent (masked, clamped)."""
        extra = {"approval_id": approval_id} if approval_id else {}
        out = self.decide("pre_tool", name, arguments=arguments, writes=writes, **extra)
        return out.get("redacted", {}).get("arguments", arguments)

    def after(self, name: str, result: Any) -> Any:
        """post_tool: the answer as the model may read it. None (a write
        that returns nothing) has nothing to screen and is not asked about:
        the side effect has happened, and refusing it now would report a
        call that ran as one that did not."""
        if result is None:
            return None
        if isinstance(result, str):
            return self._text("post_tool", name, result)
        out = self.decide("post_tool", name, result=result)
        return out.get("redacted", {}).get("result", result)

    def tool(self, name: str = "", *, writes: bool = False):
        """Decorate a tool function: its keyword arguments go through
        pre_tool, its return value through post_tool. An `approval_id`
        keyword is spent on the call, never passed to the function. The
        function is called with keyword arguments only (the shaped ones), so
        positional-only and *args parameters are refused here, up front."""
        def wrap(fn: Callable) -> Callable:
            tool_name = name or fn.__name__
            sig = inspect.signature(fn)
            if any(p.kind in (p.POSITIONAL_ONLY, p.VAR_POSITIONAL)
                   for p in sig.parameters.values()):
                raise TypeError(f"{tool_name}: a guarded tool is called with keyword "
                                "arguments only, so no positional-only or *args parameters")

            @functools.wraps(fn)
            def call(*args: Any, approval_id: str = "", **kwargs: Any) -> Any:
                bound = sig.bind(*args, **kwargs)
                shaped = self.before(tool_name, dict(bound.arguments), writes=writes,
                                     approval_id=approval_id)
                return self.after(tool_name, fn(**shaped))
            return call
        return wrap


# ---- LangGraph: guard every tool a ToolNode runs ----

def langgraph_tool_node(guard: Guard, tools: list, writes: set[str] = frozenset()):
    """A ToolNode whose tools are each asked about first. A refusal becomes
    the tool's answer, so the model is told rather than the graph crashing."""
    from langchain_core.tools import StructuredTool
    from langgraph.prebuilt import ToolNode

    def guarded(t):
        def run(**kwargs: Any) -> Any:
            try:
                shaped = guard.before(t.name, kwargs, writes=t.name in writes)
                return guard.after(t.name, t.invoke(shaped))
            except PendingApproval as e:
                return f"Not executed. Waiting for approval {e.approval_id}."
            except Denied as e:
                return f"refused by policy: {e}"
        return StructuredTool.from_function(run, name=t.name, description=t.description,
                                            args_schema=t.args_schema)
    return ToolNode([guarded(t) for t in tools])


# ---- OpenAI Agents SDK: a guarded function tool ----

def openai_agents_tool(guard: Guard, fn: Callable, *, writes: bool = False):
    """function_tool over a guarded function: the SDK builds the schema from
    `fn`'s signature, and each call is decided first."""
    from agents import function_tool

    @functools.wraps(fn)
    def run(*args: Any, **kwargs: Any) -> Any:
        try:
            return guard.tool(fn.__name__, writes=writes)(fn)(*args, **kwargs)
        except PendingApproval as e:
            return f"Not executed. Waiting for approval {e.approval_id}."
        except Denied as e:
            return f"refused by policy: {e}"
    return function_tool(run)


if __name__ == "__main__":     # a smoke run: python ticketiq_guard.py URL TOKEN
    import sys
    g = Guard(sys.argv[1], sys.argv[2])

    @g.tool()
    def lookup_order(order: str) -> str:
        return f"order {order}: shipped"
    print(lookup_order(order="A-1"))
