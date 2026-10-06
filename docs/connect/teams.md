---
title: Microsoft Teams app
order: 5
summary: Register an Azure bot, create a Teams trigger, build the app package from the console and upload it to Teams.
outcomes: Collect the Azure bot values Liyagent needs; Build the Teams app package with the package builder; Upload the package and test Liya in Teams
---

## Prerequisites

- An Azure subscription where you can create an **Azure Bot** and an Entra app registration.
- Teams admin rights, or permission to upload custom apps.
- `TICKETIQ_PUBLIC_BASE_URL` set to your instance's public `https://` address. Teams must be able to reach it.

## 1. Register the bot in Azure

1. Create an Azure Bot, single-tenant. Note the **Microsoft App ID** and the **Directory (tenant) ID**.
2. Create a client secret on the app registration, or upload a certificate.
3. Set the bot's messaging endpoint to `https://<host>/api/teams/bots/<trigger-name>/messages`.
4. Turn on the Microsoft Teams channel for the bot.

`deploy/teams/create-bot.sh` does these steps with the Azure CLI.

## 2. Store the credential

Save the client secret, or the PEM certificate and key, in the [secrets store](/docs/connect/secrets), for example as `teams-bot-secret`.

## 3. Create the Teams trigger

1. Open the Liya agent's **Triggers** tab and add a **Microsoft Teams** trigger.

   | Field | Value |
   | --- | --- |
   | Microsoft App ID | The bot's app id (a GUID) |
   | Directory (tenant) ID | Your Entra tenant id |
   | Client secret (from the Secrets store) | `secret://teams-bot-secret` |
   | Certificate and private key (from the Secrets store) | Use instead of the client secret; not both |

2. Save. Incoming messages are accepted only with a valid Bot Framework token; replies go only to Microsoft conversation hosts.

## 4. Build the app package

The package builder turns the trigger into a Teams app zip, with the manifest and the Liya icons.

1. On the trigger, choose to download the Teams app. This calls `GET /api/triggers/{name}/teams-app`.
2. The manifest points at `TICKETIQ_PUBLIC_BASE_URL`, or the request's host when that is unset.

> [!NOTE]
> Set `TICKETIQ_TEAMS_COPILOT_AGENT=true` to also declare the bot as a Microsoft 365 Copilot agent.

Offline, `python deploy/teams/build-package.py --app-id <id> --bot-app-id <bot id> --base-url https://<host>` writes the same package to `deploy/teams/dist/`. To update an app already in Teams, use `--from <old.zip>`: an update must keep the manifest `id` and the bot id.

## 5. Upload and test

1. In the Teams admin center, upload the zip as a custom app (`deploy/teams/UPLOAD.md` walks through it), or sideload it for yourself.
2. Open a chat with Liya and ask a question. A known issue arrives as a card; a new problem becomes a ticket.

> [!WARNING]
> Keep the app `id` stable across versions. A new id is a different app to Teams, and users lose their chat history with the bot.

Optional: single sign-on (`PUT /api/triggers/{name}/teams-sso`) and access limits by user or group (`PUT /api/triggers/{name}/teams-access`).

## Next steps

- [Lab: Deploy the Liya Teams bot](/docs/labs/deploy-teams-bot)
- [Known issues and duplicates](/docs/service-desk/known-issues)
