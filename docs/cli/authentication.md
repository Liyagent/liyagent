---
title: Authenticate and environments
order: 2
summary: Log in with a token, a service account or a password, keep credentials safe, and switch between instances.
---

## Environments

An environment is a named instance URL. Two are built in:

| Name | URL |
|---|---|
| `local` | `http://127.0.0.1:8787` (the default): the server's own default port, as `run.py` starts it |
| `demo` | `https://liyagent.com` |

```bash
liya env list                                        # * marks the current one
liya env add staging --url https://staging.example.com --use
liya env use demo
liya --env local agents list                         # one command, another environment
```

For a single run, `LIYA_ENV=demo` or `--url https://…` overrides the current environment. The list is stored in `~/.liya/config`. Set `LIYA_HOME` to keep it somewhere else.

## Logging in

`liya auth login` stores one credential for each environment. It tries the following, in order:

1. **Device code.** If the server advertises a device authorization endpoint (RFC 8628), `liya` opens the browser and waits for you to approve the sign-in.
2. **`LIYA_TOKEN`.** If this is set, its value is checked and stored.
3. **A hidden prompt.** You paste a token and nothing is echoed. `--token-stdin` reads the token from a pipe instead.
4. **`--username NAME`.** You're prompted for the password, with input hidden, and `liya` signs in as the console does. It stores the resulting session and never the password. The session lasts as long as a console session does.

`liya` accepts two kinds of token:

- A **service account** credential, `svc/<name>:<secret>`, created on **Access** → **Service accounts** (or `POST /api/service-accounts`). On each run it is exchanged for a one-hour session scoped to that account's role. Use this for CI, and on instances where SSO is enforced. See [Service accounts](/docs/govern/identity-roles#service-accounts).
- A **session** token, from `--username` or minted by another step.

The instance API key is not accepted. It is scoped to the agent surface, while `liya` works on the governance plane.

```bash
liya auth login                                   # hidden prompt
printf %s "$CI_LIYA_TOKEN" | liya auth login --token-stdin
liya auth login --username admin                  # password prompt (hidden)
liya auth status                                  # who you are; never the token
liya auth logout                                  # ends the session server-side and forgets it
```

## Where credentials live

Credentials are kept in `~/.liya/credentials`:

- The file is created with mode `0600` inside a `0700` directory. It is written atomically, so there is never a moment when it is readable by others.
- The token is never printed by any command, including `auth status`, `doctor` and `-o json`.
- `liya doctor` fails if the file's permissions have been loosened.

In CI you don't need a file at all. Set `LIYA_TOKEN` (`TICKETIQ_TOKEN`, used by `tiq`, is also honoured), and it takes precedence over the stored credential.

## Secrets are never arguments

A secret value never goes on the command line, because anyone on the machine can read it with `ps`. `liya secrets set LABEL` reads the value from stdin when it is piped, or from a hidden prompt otherwise. `liya providers add … --api-key-stdin` (or `--prompt-key`) works the same way for provider keys.

```bash
vault kv get -field=pw db | liya secrets set db-password --about "ITSM DB"
```
