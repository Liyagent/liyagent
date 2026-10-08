---
title: Triggers
order: 6
summary: Connect an agent to Teams, Google Chat, a schedule, email, a webhook, Slack or ticket events, each with its own authentication and loop guard.
outcomes: Choose the right trigger kind for a channel; Secure a webhook trigger with HMAC; Understand how scheduled runs behave across downtime
---

A trigger is an inbound channel bound to one agent. Manage them on the agent's **Triggers** tab or at `/api/triggers`.

| Kind | Label in the console | Inbound endpoint |
| --- | --- | --- |
| `webhook` | Webhook | `POST /api/hook/{token}` |
| `teams` | Microsoft Teams | `POST /api/teams/bots/{name}/messages` |
| `slack` | Slack | `POST /api/slack/events/{name}` |
| `google_chat` | Google Chat | `POST /api/google-chat/events/{name}` |
| `email` | Email | SMTP, or `POST /api/email/inbound/{name}` |
| `cron` | Schedule | None: runs on the schedule |
| `ticket` | Ticket event | None: runs when a matching ticket event happens |

## Create a webhook trigger

1. Open the agent's **Triggers** tab, add a trigger and pick the **Webhook** card under **Trigger type**.
2. Choose **Caller authentication**:

   | Option | How the caller proves itself |
   | --- | --- |
   | `token_url` | The secret token in the URL is enough. |
   | `hmac` | Signs the body, using headers `X-TicketIQ-Signature` and `X-TicketIQ-Timestamp`, with 300 seconds tolerance. |
   | `bearer` | An `Authorization: Bearer` token. |

3. Set **Loop guard** to `off`, `warn` or `enforce` (the default). It caps fires per trigger and per record, such as the same Jira issue or email thread. To have a trigger that keeps looping switched off, tick **Switch the trigger off after 3 refused windows in a row**. It is off unless you tick it.
4. Choose **Create trigger**, then copy the endpoint URL. The token in it is stored hashed. Rotate it with `POST /api/triggers/{name}/token`.
5. Fire it: `liya trigger fire <token> "disk full on db-02"` (the `tiq` verb, which `liya` forwards), or `POST` to the URL.

> [!WARNING]
> Treat the URL as a secret. Anyone who has a `token_url` endpoint can invoke the agent.

## Schedules

- A timezone is required, as an IANA name such as `Europe/London`.
- Each tick is claimed so it fires at most once, even with several replicas.
- After downtime only the latest missed tick runs, and older ones are recorded as `missed`.
- A tick that comes due while the previous run is still going is recorded as `skipped_overlap`.

## Teams and email

- **Teams:** needs the Azure bot's **Microsoft App ID**, **Directory (tenant) ID** and either a **Client secret** or a **Certificate and private key**, both from the Secrets store. See [Microsoft Teams app](/docs/connect/teams).
- **Email:** replies go back in the same thread. Only **Allowed senders** are answered, and an empty list means nobody. See [Email and SMTP](/docs/connect/email-smtp).

## Operate triggers

`POST /api/triggers/{name}/pause`, `/resume` and `/run` (fire now). List runs with `GET /api/triggers/{name}/runs` and cancel one with `POST /api/triggers/{name}/runs/{run_id}/cancel`. A trigger's kind is fixed at creation: change it with `POST /api/triggers/{name}/convert`, with a reason.

From the command line, `liya triggers list`, `create` and `delete` manage triggers. Use the server's kind names with `--kind` (`cron`, `ticket`, `webhook`, `email`, `teams`, `slack`, `google_chat`), for example `liya triggers create nightly --agent copilot --kind cron --schedule "0 2 * * *" --timezone Europe/London --input "Summarise yesterday"`.

## Next steps

- [Transcripts](/docs/monitor/transcripts)
- [Lab: Deploy the Liya Teams bot](/docs/labs/deploy-teams-bot)
