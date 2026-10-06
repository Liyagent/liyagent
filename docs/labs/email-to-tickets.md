---
title: Route email to tickets with SMTP
summary: Start Liyagent's SMTP listener, send mail to it with swaks or Python, and watch messages become classified tickets.
category: Integrations
stack: [Docker]
level: Beginner
time: 15 min
order: 9
outcomes: Start the built-in SMTP listener; Send test mail and ingest it; Turn on automatic ingestion
---

## Prerequisites

- A running Liyagent instance on your machine.
- `swaks`, or Python 3.

## Steps

1. Start the listener from **General** settings → **Dev mail server** → **Start**, or:

   ```bash
   curl -b cookies.txt -X POST http://127.0.0.1:8787/api/mailserver/start
   curl -b cookies.txt http://127.0.0.1:8787/api/mailserver
   ```

   It listens on `127.0.0.1:2525` by default.

2. Send a message.

   ```bash
   swaks --server 127.0.0.1:2525 --to helpdesk@example.test --from ana@example.test \
     --header "Subject: Shared drive S: not mapping" --body "Since the update, S: is missing."
   ```

   Or with Python:

   ```python
   import smtplib
   from email.message import EmailMessage
   m = EmailMessage(); m["From"] = "ana@example.test"; m["To"] = "helpdesk@example.test"
   m["Subject"] = "Shared drive S: not mapping"; m.set_content("Since the update, S: is missing.")
   smtplib.SMTP("127.0.0.1", 2525).send_message(m)
   ```

3. Ingest the inbox: `POST /api/mailserver/ingest`. Open **Tickets**: the mail is a ticket in **Storage**, with the sender as reporter.
4. To make this automatic, set `TICKETIQ_MAIL_AUTOSTART=true` and `TICKETIQ_MAIL_AUTO_INGEST=true` and restart.
5. For outbound notices, set `TICKETIQ_MAIL_RELAY_HOST`, `TICKETIQ_MAIL_RELAY_PORT` and `TICKETIQ_MAIL_FROM`.

> [!WARNING]
> Keep the listener on `127.0.0.1` unless it sits behind your own mail relay. For agent conversations over email, use an email trigger with **Allowed senders** and authenticated-mail checks.

## Next steps

- [Email and SMTP](/docs/connect/email-smtp)
