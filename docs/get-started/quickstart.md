---
title: Quickstart
order: 2
summary: Run Liyagent on your machine, sign in to the console and file a ticket that the Liya agents triage.
outcomes: Start the Liyagent server locally; Sign in as the first admin; File a ticket and read how it was classified and routed
---

## Prerequisites

- Python 3.12 (the version the pinned dependencies and the container image use), Git, and Docker (for Postgres). To run the whole stack in containers instead, see [Deploy on a VM](/docs/get-started/deploy-vm).
- About 2 GB of free disk for the embedding model and the embedded vector store.
- Optional: an Anthropic API key, or any OpenAI-compatible endpoint, if you want the model-backed agents to answer.

## Run the server

1. Get the Liyagent release and install its runtime dependencies. Liyagent is licensed software: customers and evaluators get access to the release (the source bundle and the container images) from [sales@liyagent.com](mailto:sales@liyagent.com). To look around first with no install, [try Liya live](/try).

   ```bash
   cd liyagent        # the unpacked release
   python -m venv .venv && . .venv/bin/activate
   pip install -r requirements-2.0.txt
   ```

2. Start a PostgreSQL 16 database. Liyagent stores everything in Postgres and refuses to start without `TICKETIQ_DB_URL`. The quickest way is a throwaway container:

   ```bash
   docker run -d --name tiq-pg -p 5432:5432 -e POSTGRES_PASSWORD=tiq -e POSTGRES_DB=ticketiq postgres:16-alpine
   export TICKETIQ_DB_URL=postgresql://postgres:tiq@127.0.0.1:5432/ticketiq
   ```

3. Start the server. It listens on `http://127.0.0.1:8787` by default.

   ```bash
   python run.py
   ```

   `run.py` wraps `uvicorn ticketiq.api:app`. To change the address, set `TICKETIQ_HOST` and `TICKETIQ_PORT` (or pass `--port`).

4. Open `http://127.0.0.1:8787/login` and sign in with the first admin account: user `admin`, password `ticketiq`, unless you set `TICKETIQ_ADMIN_USER` and `TICKETIQ_ADMIN_PASSWORD` first.

> [!WARNING]
> The default password is accepted only on a loopback address. When the server binds any other address (`TICKETIQ_HOST` or `run.py --host`), it refuses to start until `TICKETIQ_ADMIN_PASSWORD` is changed.

> [!NOTE]
> Don't run uvicorn with `--reload`. The embedded Qdrant store allows one process at a time.

## File your first ticket

1. In the console, open **IT service desk › Tickets**, choose **New ticket**, fill in the title and description and choose **Run Pipeline**. Or sign in and send one with the API:

   ```bash
   curl -s -c cookies.txt -X POST http://127.0.0.1:8787/api/login \
     -H "Content-Type: application/json" -d '{"username":"admin","password":"ticketiq"}'
   curl -s -X POST http://127.0.0.1:8787/api/tickets \
     -H "Content-Type: application/json" -b cookies.txt \
     -d '{"title":"VPN drops every 10 minutes","description":"Since this morning the VPN client disconnects on Wi-Fi."}'
   ```

2. The pipeline result shows each agent's step. Open the ticket to see the category (for example **Network**), the priority, the team it was routed to (**Network Operations**) and the SLA due time. Its **Pipeline runs** and **History** tabs show how it got there.
3. File the same problem again from another user. Liya Correlate folds it into the first ticket and the second reporter is told it is a known issue.

## Connect a model (optional)

The pipeline works without a model. To let Liya answer and Liya Triage refine categories, add a provider:

1. Open **AI Gateway › LLM providers** and choose **+ Add provider**.
2. Give it a **Display name** and, under **Provider type**, pick **Anthropic**, or **OpenAI-compatible** for any endpoint that speaks the OpenAI API (set its **Base URL**).
3. Paste the key under **Credential**, choose **Test connection**, select the models agents may use under **Models**, and choose **Create provider**.
4. Point Liya at it: open **AI Gateway › Provider bindings** and choose **Bind** on Liya's row, or open Liya from **Agents › All agents** and, under **Settings › Model**, pick the provider and model and choose **Override**. Liya's sub-agents use Liya's model unless you override theirs.

## Next steps

- [Create an agent](/docs/agents/create)
- [Deploy on a VM](/docs/get-started/deploy-vm)
- [Triage and categories](/docs/service-desk/triage-categories)
