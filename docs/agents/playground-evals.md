---
title: Playground and evals
order: 5
summary: Try an agent interactively, compare variants, and measure it against versioned datasets before you ship a change.
outcomes: Run and compare prompts in the playground; Build an eval dataset from JSONL, transcripts or tickets; Run an eval against a baseline and gate CI on it; Red-team an agent and gate its release on the result
---

## Playground

The agent's **Playground** tab sends a message through the same governed path real traffic uses: guardrails, budgets and the audit log all apply.

| Action | Endpoint | Use it to |
| --- | --- | --- |
| Run | `POST /api/agents/{key}/playground` | Try a message |
| Compare | `POST /api/agents/{key}/playground/compare` | Run variants side by side (instructions, model) |
| Replay | `POST /api/agents/{key}/playground/replay` | Re-run a past conversation with edits |
| Simulate | `POST /api/agents/{key}/playground/simulate` | Check whether a given person could run the agent, from a channel and context. A dry run: nothing is sent to a model and nothing runs as them |

Simulated users (`/api/agents/{key}/simulations`) let a model play a user with a hidden goal for multi-turn tests.

### Attach files

**Attach** (or drop or paste) up to 5 files on a message. Each is uploaded as soon as you pick it, with `POST /api/agents/{key}/playground/files`, and shows its preview or the reason it was refused; **Send** waits until every file has uploaded.

| | |
| --- | --- |
| Images | PNG, JPEG, GIF or WebP, up to 5 MB. Sent to the model as an image |
| Documents | PDF, Word, Excel, PowerPoint, text, Markdown, CSV, TSV, JSON, log, XML, YAML, and zip or gzip archives, up to 10 MB. The agent is given the text read from them, marked as data you supplied |

A file's contents must match its name, and programs and scripts are refused whatever they are called. Archives are read under the same bounded extraction as email attachments, so a decompression bomb cannot exhaust the server. A document with no readable text (a scanned PDF, an empty file) is refused, since the agent could not use it. Files are kept for 7 days, or until their session is deleted, and only you can open yours; a reopened session shows each message's files and says which have expired.

### What else the Playground shows

- **Tables and charts** in replies, when the agent's instructions say how to write them; see [Tables and charts in replies](/docs/agents/instructions-model#tables-and-charts-in-replies).
- **Outputs**: the charts, tables and code the agent wrote, results its tools kept for you and resources they returned, each downloadable, and the sources it used — links it cited and tools it read — each tied to its turn.
- **Requests waiting for you**: an approval, a connection, an answer or a form an MCP server sent is pinned above the message box, asked one question at a time. A send that fails keeps what you typed; once settled, a request folds into one line in its turn as answered or declined.
- **Context**: an estimate of what the next request will carry, against the model's input and output limits from the model catalogue, kept apart from the token counts the provider reported.

## Datasets

Datasets are versioned and append-only. Each has a kind:

| Kind | Measures |
| --- | --- |
| `retrieval` | Did the right knowledge come back? |
| `triage` | Category, priority and team against expected values |
| `agent_turn` | An agent's reply, scored by evaluators |

Create one from **Agents › Evaluations** or with the API:

1. `POST /api/evals/datasets` with a name, a kind and its cases, as `items` or as JSONL text in `jsonl`. Posting again writes the next version; `append: true` adds to the latest instead of replacing it.
2. Add cases from a transcript (`POST /api/evals/datasets/{name}/from-transcript`, redacted), or from tickets (`.../from-tickets`).
3. Optionally split it into calibrate and holdout sets with a fixed seed (`.../split`).

## Runs

1. Start a run with `POST /api/evals/runs`, naming the dataset and agent. The run pins the dataset version and the agent's config version.
2. Open the run on **Agents › Evaluations**. Scores are compared with the baseline run.
3. When you are happy, mark it as the new baseline with `POST /api/evals/runs/{run_id}/baseline`.

> [!TIP]
> In CI, `liya eval run --dataset <name> --fail-on-regression` (the `tiq eval run` verb, forwarded) exits 1 when a run fails or regresses against its baseline. `liya agents eval <agent> --dataset <name>` runs a dataset against one agent and exits 1 on a failure or regression.

Evaluators (`/api/evals/evaluators`) include built-in checks and LLM-judge evaluators. `POST /api/agents/{key}/evals/generate` drafts cases from an agent's description to get you started.

## Red teaming

**Agents › Red teaming** throws known attacks at an agent: instruction override, role-play jailbreaks, system-prompt extraction, PII exfiltration and tool abuse, each obfuscated (base64, homoglyphs, zero-width characters and more) and sent directly or planted in content the agent reads. A run reports the attack success rate (ASR) overall and by category, transform and vector, each with a 95% interval.

| Target | What it measures |
| --- | --- |
| `guardrails` | Each attempt screened by the agent's own guardrails. No model is called; a run takes seconds. |
| `agent` | Each attempt asked of the agent through the governed path, and its answer judged. Needs `transcripts.content.read`. |

A run records the configuration it measured: the agent's version fingerprint. Successes in **PII exfiltration** and **tool abuse** are *critical* findings; the report counts them.

1. Start a run from the page, or with `POST /api/redteam/runs` (`governance.write`) naming the agent, the target and optionally a subset of categories, transforms and vectors.
2. Open it on **Agents › Red teaming**. Compared with the latest earlier run, it lists the attacks that newly get through.
3. Export the attempts with `GET /api/redteam/runs/{run_id}?format=csv`.

> [!TIP]
> In CI, `python -m ticketiq.redteam --agent <id> --max-asr 0.1` exits 1 when the ASR is over the bar; add `--baseline latest` to fail on a rise against the last run as well.

### Release gate

With the release gate on, an agent configuration is released only after a red-team run of exactly that configuration passed. These are refused with `409` (`code: redteam_gate`) until it has:

- restoring a version (`POST /api/agents/{key}/versions/{id}/restore`);
- promoting a candidate that restores a version or adopts an optimizer proposal (`POST /api/settings/candidates/{id}/promote`);
- publishing the agent's card for the first time (`PUT /api/agents/{key}/spec`).

The refusal names each failed criterion and links the run it judged. The criteria:

| Setting | Default | The release passes when |
| --- | --- | --- |
| `required` | off | — (the gate is on) |
| `max_asr` | 0.1 | the run's overall ASR is at most this |
| `no_critical` | on | no PII-exfiltration or tool-abuse attack got through |
| `max_age_days` | 14 | the run finished at most this many days ago |
| `target` | `any` | the run's target is this (`guardrails`, `agent`) |

The run must be of the configuration being released: its fingerprint is the agent's version snapshot without the card, so publishing a card does not void the run made just before it. The newest completed run of that configuration is the one judged. An optimizer proposal has never been in force, so no run can have measured it; with the gate on it is adopted only through an override. Agents a run cannot target (the built-in pipeline steps) are outside the gate.

Set the organisation default on **Agents › Red teaming** (`PUT /api/redteam/gate`), and an agent's own policy on its **History** tab (`PUT /api/agents/{key}/redteam-gate`, or `{"inherit": true}` to follow the default again). Both need `governance.write`; loosening a gate that is on also needs `governance.weaken` and a reason. The History tab shows whether the agent's current configuration would pass.

An owner can release past a refusal: send `override_redteam_gate: true` and a `reason` with the release. It needs `governance.weaken`, and is audited as `redteam.gate.override` with the criteria that failed. Refusals are audited as `redteam.gate.refused`.

## Next steps

- [Lab: Write an eval set for Triage](/docs/labs/eval-set-triage)
- [Transcripts](/docs/monitor/transcripts)
