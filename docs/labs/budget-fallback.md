---
title: Set a budget and watch the fallback
summary: Put a tiny daily budget on an agent that falls back to a cheaper model at the limit, then watch calls re-route and the audit trail record it.
category: Governance
stack: [Docker]
level: Intermediate
time: 25 min
order: 7
outcomes: Create a scoped budget with the fall back action; Trigger it on purpose; Find the budget.fallback events and the spend they saved
---

## Prerequisites

- A running Liyagent instance with two models configured, one cheaper than the other.
- An agent bound to the more expensive model (for example `hr-helper` from [Build a custom sub-agent](/docs/labs/custom-sub-agent)).

## Steps

1. Open **Budgets** and fill in the scoped-budget row:

   | Field | Value |
   | --- | --- |
   | Name | `hr-lab` |
   | Scope | **An agent**, `hr-helper` |
   | USD | 0.02 |
   | Period | **per day** |
   | At the limit | **At the limit: fall back** |
   | Provider / model | leave the provider blank (same provider) and enter the cheaper model |

2. Choose **Add scoped budget**. The row shows **Capped**, its spend this day and "falls back to …".
3. Ask the agent a few long questions on its **Playground** tab until the status reads **Exhausted**.
4. Ask one more. The answer still arrives, from the cheaper model.
5. Open **Audit log** and type `action=budget.fallback` in the search. Each re-routed call is there with the original and the fallback model.
6. Add the budget again under the same name with **At the limit: refuse** (saving a name that exists replaces it) and ask again: the call is refused with a budget error.

> [!NOTE]
> A budget can't fall back to the same or a more expensive model, and when any budget covering a call is exhausted the call is refused.

## Clean up

Delete the budget (`DELETE /api/budgets/scoped/{name}`) or raise its limit.

## Next steps

- [Budgets](/docs/ai-gateway/budgets)
