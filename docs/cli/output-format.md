---
title: Format output
order: 4
summary: Choose table, JSON or YAML output, and pipe liya into other tools.
outcomes: Switch output format per command; Script against JSON output with jq
---

Every command accepts `-o` (or `--output`):

| Format | For |
| --- | --- |
| `-o table` | Reading. The default, unless `LIYA_OUTPUT` sets another. |
| `-o json` | Scripts and `jq`. The server's full payload. |
| `-o yaml` | Reviewing. |

```bash
liya agents list -o json | jq -r '.agents[] | select(.stage=="assist") | .key'
liya budgets list -o yaml > budgets.yaml
```

Tables and data go to stdout; hints go to stderr, so a pipe only ever carries data. `liya export` writes YAML files for `liya apply` (see [GitOps with liya](/docs/cli/gitops)).

> [!TIP]
> Tables are for people and may change between releases. Scripts should always use `-o json`.

## Next steps

- [GitOps with liya](/docs/cli/gitops)
