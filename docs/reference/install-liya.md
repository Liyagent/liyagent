---
title: Install liya
order: 2
summary: Install the liya command line from the TicketIQ repository and check it can reach your instance.
outcomes: Install liya; Confirm the version and connectivity
---

## Install

`liya` is not published to a package index. Install it from a checkout of the TicketIQ repository:

```bash
pip install .            # installs the liya (and legacy tiq) commands
# or, without installing:
./liya --version         # or: python -m ticketiq.cli --version
```

It needs Python 3.10 or later, `httpx` and `pyyaml`, and nothing else.

## Check it

```bash
liya --version
liya env add dev --url http://127.0.0.1:8787 --use
liya auth login
liya doctor
```

`liya doctor` checks your Python version and the `httpx` and `pyyaml` modules, the permissions on the credentials file, whether the instance is reachable and healthy, whether your credential is accepted, and whether the client and server versions match. It exits `1` if any check fails.

## Next steps

- [Authenticate and choose an environment](/docs/cli/authentication)
