# Prompt contracts

Prompts are **versioned contracts**, not ad-hoc strings in code paths.

## Registry

`app/ai/prompts/registry.py` — `PromptRegistry.get(prompt_id)`

| prompt_id | version | Purpose |
|-----------|---------|---------|
| `analytics.summary.v1` | 1.0.0 | Report KPI summary |
| `anomaly.investigation.v1` | 1.0.0 | Anomaly investigation |
| `reporting.executive.v1` | 1.0.0 | Executive narrative |

## Contract fields

| Field | Meaning |
|-------|---------|
| `prompt_id` | Stable identifier stored on `ai_execution_runs` |
| `version` | Semantic version for audit diff |
| `purpose` | Human-readable scope |
| `output_schema` | Expected JSON/shape of model output |
| `deterministic_sections` | Must match platform data (no fabrication) |
| `probabilistic_sections` | Model-generated; require disclaimer in UI |

## Review rules (mandatory for changes)

- [ ] No instruction to bypass policy or RLS
- [ ] No instruction to mutate ledger/snapshots/queue
- [ ] Deterministic sections reference DTO fields only
- [ ] Probabilistic sections labeled as non-authoritative
- [ ] Version bump on any behavior change
- [ ] Unit test references new `prompt_id`
- [ ] README / ops docs updated if user-visible

## Runtime binding

`AIOrchestrationService.begin_run(prompt_id=...)` loads contract and stores `prompt_version` on audit row.

Future LLM adapters must log `prompt_id` + `prompt_version` on every provider call.
