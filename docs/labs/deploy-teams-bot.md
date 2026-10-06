---
title: Deploy the Liya Teams bot
summary: Register an Azure bot, connect it to a Liya Teams trigger, build the app package and chat with Liya in Microsoft Teams.
category: Integrations
stack: [Teams, AWS]
level: Intermediate
time: 45 min
order: 3
outcomes: Create the Azure bot and store its secret; Build the Teams package from the trigger; Upload the app and get an answer from Liya
---

## Prerequisites

- Liyagent reachable over HTTPS, for example on a VM from [Deploy on a VM](/docs/get-started/deploy-vm), with `TICKETIQ_PUBLIC_BASE_URL` set. `deploy/vm/aws-launch.sh` starts a suitable EC2 VM.
- Azure CLI signed in to a subscription, and permission to upload custom Teams apps.

## Steps

1. Decide the trigger name, for example `liya-teams`. The messaging endpoint will be `https://<host>/api/teams/bots/liya-teams/messages`.
2. Run the setup script. Liya's agent id is `copilot`:

   ```bash
   deploy/teams/create-bot.sh --url https://<host> --agent copilot --name liya-teams
   ```

   It asks for a Liyagent admin's sign-in, then registers the Entra app, creates the client secret and stores it in the **Secrets store** as `TEAMS_BOT_LIYA_TEAMS` (it is never printed), creates the `liya-teams` trigger on Liya, creates the Azure Bot with its Teams channel, and saves `liya-teams-teams-app.zip`.
3. To do it by hand instead: create the bot in Azure, store its client secret in the **Secrets store**, then open the **Liya** agent → **Triggers** and add **Microsoft Teams** with the **Microsoft App ID**, the **Directory (tenant) ID** and the secret. **Set up in Teams** → **Build Teams package (.zip)** downloads the app (`GET /api/triggers/liya-teams/teams-app`).
4. In Teams, go to **Apps** → **Manage your apps** → **Upload an app**, and upload the zip.
5. Open a chat with Liya and write `My VPN keeps disconnecting`. Liya answers with suggested fixes and offers to file a ticket.
6. From a second account, report the same problem. That user gets a known-issue card instead of a new ticket.

> [!WARNING]
> Keep the manifest `id` the same for every update. Rebuild an update with `python deploy/teams/build-package.py --from <old.zip>`.

## Check your work

- The trigger's health (`POST /api/triggers/liya-teams/health`) reports OK.
- The conversation appears on the Liya agent's **Transcripts** tab.

## Next steps

- [Microsoft Teams app](/docs/connect/teams)
- [Add a known-issue banner](/docs/labs/known-issue-banner)
