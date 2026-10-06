---
title: Google Chat app
order: 5.5
summary: Create a Chat app in your Google Cloud project, point its HTTP endpoint at Liyagent, and paste the project number, service account key and domains into a Google Chat trigger.
outcomes: Create the Chat app and its service account in Google Cloud; Create the Google Chat trigger in Liyagent; Test Liya in a direct message and in a space
---

Liya answers in Google Chat the same way it answers in Microsoft Teams. It uses the same access settings, sessions, recording, audit and feedback. With SAP connected, Liya shows the same **Confirm** and **Cancel** cards, and only the person who asked can confirm.

## Prerequisites

- A Google Workspace account. People must message Liya from your Workspace domains, not from personal Gmail accounts.
- A Google Cloud project that your Workspace admin can manage. In that project you need to be able to enable APIs and create service accounts. Your admin needs to be able to publish the Chat app to your domain.
- `TICKETIQ_PUBLIC_BASE_URL` set to your instance's public `https://` address. Google Chat must be able to reach it.

## 1. Create the Google Cloud project and service account

1. In the [Google Cloud console](https://console.cloud.google.com/), create a project or pick an existing one, for example `liya-chat`.
2. Note the **Project number**, a number like `123456789012`. It is on the project dashboard. Do not use the project ID.
3. Go to **APIs & Services → Library** and enable the **Google Chat API**.
4. Go to **IAM & Admin → Service accounts** and create a service account, for example `liya-chat-app`. It needs no IAM roles. The Chat app sends messages under its own authority (the `chat.bot` scope).
5. Open the service account, then **Keys → Add key → Create new key → JSON**. Save the file somewhere safe. You paste it into Liyagent in step 3 and can then delete your copy.

> [!WARNING]
> The key file is a credential. Store it only in the Liyagent secrets store and never in the trigger, a ticket or a chat. If it leaks, delete the key in Google Cloud and create a new one.

## 2. Configure the Chat app

In the same project, open **APIs & Services → Google Chat API → Configuration** and set:

| Setting | Value |
| --- | --- |
| App name / Avatar URL / Description | `Liya`, your icon, and a one-line description |
| Interactive features | On |
| Functionality | **Receive 1:1 messages** and **Join spaces and group conversations** |
| Connection settings | **HTTP endpoint URL**: `https://<host>/api/google-chat/events/<trigger-id>` |
| Authentication audience | **Project Number** (recommended) or **HTTP endpoint URL** |
| Visibility | Specific people and groups in your domain while you test, then the whole domain |
| Logs | Log errors to Logging (optional) |

The trigger id is the id you give the trigger in step 3, for example `liya-gchat`.

To make Liya available to everyone, a Workspace admin can allowlist the app. Go to **Admin console → Apps → Google Workspace → Google Chat → Chat apps** and check that people can install Chat apps.

## 3. Create the Google Chat trigger in Liyagent

1. Under **Secrets store**, create a secret such as `GOOGLE_CHAT_SA` and paste in the whole JSON key file.
2. Open the agent's **Triggers** tab, choose **Add trigger → Google Chat**, and fill in the fields:

   | Field | Value |
   | --- | --- |
   | Display name | Becomes the trigger id in the endpoint URL, for example `liya-gchat` |
   | Authentication audience | Must match step 2: **Project number** or **HTTP endpoint URL** |
   | Audience | The project number (digits). If you chose **HTTP endpoint URL**, the full endpoint URL instead |
   | Service account key (from the Secrets store) | `GOOGLE_CHAT_SA` from the secrets store |
   | Allowed Workspace domains | `example.com` and any others. Only people whose email is in one of these domains get an answer |
   | Who may use it | **Everyone in those domains**, **Only the people listed**, or **People with a Liyagent account**, whose Liyagent role and policies then also apply |
   | Default time zone | Used when Google Chat does not report a person's time zone, for example `Europe/Berlin` |

3. Save. The trigger list shows the endpoint URL. It must match the URL in the Chat app configuration exactly.

You can also create the trigger through the API:

```http
PUT /api/triggers/liya-gchat
{ "agent": "liya", "kind": "google_chat",
  "google_chat_audience_type": "project_number", "google_chat_audience": "123456789012",
  "google_chat_credential_ref": "GOOGLE_CHAT_SA", "google_chat_domains": ["example.com"],
  "google_chat_access": "domain", "google_chat_time_zone": "Europe/Berlin" }
```

## 4. Test it

1. In Google Chat, select **New chat**, find **Liya** under Apps, and send it a message. You first see *Working on it…* (or *Looking that up in SAP…*), and the answer then replaces it in place.
2. Add Liya to a space and @mention it. In a space, Liya answers only when mentioned and replies in the message's thread. Each person in a space has their own session.
3. With SAP connected, ask for something that calls SAP. A card shows exactly what will run, with **Confirm** and **Cancel**. The card then changes to *Confirmed* or *Cancelled*. The results arrive as a card with a table of records, next-step buttons, and 👍 / 👎 feedback buttons.

SAP actions are proposed only in a direct message, because a space has no single person to confirm them. Times show in the person's time zone, as Google Chat reports it, or the trigger's default.

## How requests are checked

- Every request must carry a token signed by Google. With **Project number**, it is the Chat service account's JWT (`iss` = `chat@system.gserviceaccount.com`, `aud` = your project number). With **HTTP endpoint URL**, it is a Google ID token for that URL, issued to `chat@system.gserviceaccount.com`. Any other token gets a 401.
- The sender must be a person, not another app, with an email in one of the allowed domains. People outside those domains get no answer, and every refusal is audited.
- Replies go only to `chat.googleapis.com`, authenticated with the service account key from the secrets store. The key is never logged or shown.
- Each answer is acknowledged at once and sent through the Chat API, so a long SAP lookup is not cut off by Google's 30-second response limit.
- The `googlechat` channel switch (`PUT /api/channels`) turns this door off for the whole instance or a tenant, without deleting the trigger.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Chat says the app is not responding | The audit log shows `trigger.google_chat.denied`. The audience type or value does not match the Chat app's **Authentication audience**. |
| No reply in a space | The message must @mention Liya. |
| No reply at all, and `trigger.google_chat.error` in the audit log | The service account key secret is missing or wrong, or the Google Chat API is not enabled. |
| "This assistant is not available here right now." | The sender's domain is not in **Allowed Workspace domains**. |

## Next steps

- [Connect SAP](/docs/connect/sap)
- [Secrets store](/docs/connect/secrets)
