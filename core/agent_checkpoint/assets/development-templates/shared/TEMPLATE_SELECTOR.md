# TEMPLATE_SELECTOR.md

Choose the workflow by the primary intent of the work.

| Intent | Template |
|---|---|
| Build a new product/system | `project/` |
| Add/change user-visible functionality | `feature/` |
| Correct incorrect behavior | `bugfix/` |
| Improve internal structure without intended behavior change | `refactor/` |
| Upgrade framework/runtime/dependencies | `upgrade/` |
| Change persistent data/schema/format | `migration/` |
| Improve latency/throughput/resource usage | `performance/` |
| Connect an external API/service/provider | `integration/` |
| Ship an already-developed change to an environment | `release/` |
| Investigate feasibility/choose an approach | `spike/` |

## Mixed Work

When a request spans multiple intents, choose the template that owns the highest-risk irreversible concern, and create explicit subordinate Steps for the rest.

Examples:

```text
Upgrade PostgreSQL + migrate schema
-> MIGRATION if data safety dominates
-> UPGRADE if schema is unchanged and compatibility is the main risk

Add Stripe payment
-> INTEGRATION, even though it is also a feature

Make API faster by adding cache
-> PERFORMANCE, because measurement and regression thresholds are central

Refactor auth module while fixing logout bug
-> BUGFIX first
-> separate REFACTOR after bug is verified fixed
```

Do not combine unrelated work merely to reduce the number of plans.
