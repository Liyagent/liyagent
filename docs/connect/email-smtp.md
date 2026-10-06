---
title: Email and SMTP
order: 8
summary: Receive mail as tickets or as agent conversations, reply in thread, and relay outbound notices through your SMTP server.
outcomes: Start the built-in SMTP listener and turn mail into tickets; Give an agent an email door with allowed senders; Configure an outbound relay
---

## Inbound: the built-in SMTP listener

Liyagent includes a small SMTP server. Mail it receives lands in an inbox table (5 MB per message limit).

| Variable | Default | Meaning |
| --- | --- | --- |
| `TICKETIQ_MAIL_HOST` | `127.0.0.1` | Listen address |
| `TICKETIQ_MAIL_PORT` | `2525` | Listen port |
| `TICKETIQ_MAIL_AUTOSTART` | off | Start with the server |
| `TICKETIQ_MAIL_AUTO_INGEST` | off | Turn inbox mail into tickets automatically |

Start, stop and test it with `POST /api/mailserver/start`, `/stop` and `/send-test`; ingest the inbox by hand with `POST /api/mailserver/ingest`.

## An email door for an agent

Mail addressed to an agent's email door becomes a conversation, and the agent replies in the same thread.

1. On the agent's **Triggers** tab, add an **Email** trigger, or use `PUT /api/triggers/{name}/email`.
2. Fill in **Allowed senders**, addresses or domains. An empty list means nobody is answered.
3. Keep **Require the receiving server to have authenticated the sender** on (the default): the receiving server's `Authentication-Results` header must show DMARC or DKIM pass.
4. Deliver mail either to the SMTP listener or by `POST /api/email/inbound/{name}` with the raw RFC 5322 message, signed with the door's signing secret (`X-TicketIQ-Signature` and `X-TicketIQ-Timestamp`).

> [!WARNING]
> Only trust `Authentication-Results` from your own relays. List their IP addresses in `TICKETIQ_EMAIL_TRUSTED_RELAYS`; mail from any other peer can't satisfy that check.

## Outbound relay

| Variable | Meaning |
| --- | --- |
| `TICKETIQ_MAIL_RELAY_HOST` / `TICKETIQ_MAIL_RELAY_PORT` | Your SMTP relay (port 25 by default). Unset, replies go to `TICKETIQ_MAIL_HOST`, the built-in listener, and never reach the sender. |
| `TICKETIQ_MAIL_RELAY_USER` / `TICKETIQ_MAIL_RELAY_PASSWORD` | Relay credentials |
| `TICKETIQ_MAIL_FROM` | The From address on notices and replies |

## Next steps

- [Lab: Route email to tickets with SMTP](/docs/labs/email-to-tickets)
