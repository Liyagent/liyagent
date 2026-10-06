---
title: Triage and categories
order: 3
summary: How categories, priorities, teams and SLAs are assigned, and how to replace the default categories with a taxonomy learned from your own tickets.
outcomes: Read and override the routing table and SLA hours; Discover, review and approve a learned taxonomy; Reclassify existing tickets after a change
---

## Default categories and teams

Out of the box, Liya Classify uses IT categories, and Liya Assign routes each to a team:

| Category | Team |
| --- | --- |
| Network | Network Operations |
| Database | Database Administration |
| Access & Identity | Identity & Access Management |
| Hardware | Field Services |
| Software | Application Support |
| Email & Collaboration | Messaging Team |
| Security | Security Operations |
| Storage | Storage Team |
| General Support (fallback) | Service Desk L1 |

| Priority | SLA hours |
| --- | --- |
| P1 | 4 |
| P2 | 8 |
| P3 | 24 |
| P4 | 72 |

Override either with `PUT /api/routing` (send only what differs), or manage named SLA policies at `/api/sla/policies` and preview their effect with `/api/sla/preview`.

## Learn categories from your tickets

A tenant that isn't an IT desk (HR, finance, facilities) can have categories learned from its own history.

1. Open **IT service desk › Categories** and choose **Learn from history** (`POST /api/taxonomy/discover`), or learn from a CSV export. TicketIQ embeds the tenant's tickets, clusters them and picks the number of clusters with the best separation.
2. Review the proposal. Each category has a name, description, count, examples, keywords and a suggested team taken from past assignments.
3. Rename, merge, split or delete categories and set teams (`POST /api/taxonomy/proposal/edit`).
4. Choose **Approve taxonomy** (`POST /api/taxonomy/approve`). Approval writes a new version and makes it live at once. To go back to an earlier version, choose **Activate** on it (`POST /api/taxonomy/activate`); **Use IT defaults** returns to the built-in categories.
5. Choose **Re-classify existing tickets** if you want history to use the new categories (`POST /api/taxonomy/reclassify`).

After activation, classification picks the nearest category centroid, with keyword and source-label hints.

> [!NOTE]
> A tenant with no approved taxonomy keeps the IT defaults. **Discard** on a proposal (`DELETE /api/taxonomy/proposal`) changes nothing live.

## Triage refinement

When a model is configured, Liya Triage runs after classification to correct the category and add a triage note. It runs off the critical path, so a slow or missing model never delays routing.

## Next steps

- [Known issues and duplicates](/docs/service-desk/known-issues)
- [Lab: Connect a Jira project and triage issues](/docs/labs/jira-triage)
