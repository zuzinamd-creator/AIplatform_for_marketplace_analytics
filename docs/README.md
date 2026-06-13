# Documentation Hub

Central index for the Marketplace Analytics Platform (WB / Ozon).

**Project README:** [../README.md](../README.md)  
**Pre-v0.6 README archive:** [archive/README_pre_v06.md](archive/README_pre_v06.md)  
**Current release:** [release/v0.6-mvp-intelligence.md](release/v0.6-mvp-intelligence.md)

---

## Getting started

| Document | Purpose |
|----------|---------|
| [../README.md](../README.md) | Project overview, AI capabilities, metrics, quick start |
| [testing/local_runtime_testing.md](testing/local_runtime_testing.md) | Local dev, Docker, Windows setup |
| [testing/archetype_validation_framework.md](testing/archetype_validation_framework.md) | Archetype validation (6.5.2) |
| [release/multi_seller_replay_report.md](release/multi_seller_replay_report.md) | Multi-seller replay (6.5.3) |
| [release/v06_release_manifest.md](release/v06_release_manifest.md) | v0.6 pilot-validated manifest |
| [roadmap/v07_candidate_features.md](roadmap/v07_candidate_features.md) | v0.7 candidate features |
| [operations/environment_variables.md](operations/environment_variables.md) | Environment variable reference |
| [product/local_deployment.md](product/local_deployment.md) | MAIN vs LOCAL, Supabase, persistence |
| [operations/release_checklist.md](operations/release_checklist.md) | Pre-release checklist |

---

## AI & Intelligence

| Document | Purpose |
|----------|---------|
| [ai/ai_architecture.md](ai/ai_architecture.md) | AI system architecture |
| [ai/domain_analysts.md](ai/domain_analysts.md) | Domain analyst layer |
| [ai/executive_intelligence.md](ai/executive_intelligence.md) | Executive summary engine |
| [ai/usefulness_framework.md](ai/usefulness_framework.md) | Seller usefulness metrics |
| [ai/phase_63_architecture_blueprint.md](ai/phase_63_architecture_blueprint.md) | Phase 6.3 expansion blueprint |
| [ai/phase_630b_priority_calibration_report.md](ai/phase_630b_priority_calibration_report.md) | Priority calibration (6.3.0B) |
| [ai/inventory_priority_calibration_audit.md](ai/inventory_priority_calibration_audit.md) | Calibration root-cause audit |
| [ai/threshold_catalog.md](ai/threshold_catalog.md) | Threshold registry (6.5.1) |
| [ai/operating_director_architecture.md](ai/operating_director_architecture.md) | Operating Director (scaffold) |

---

## Platform & Architecture

| Document | Purpose |
|----------|---------|
| [architecture/invariants.md](architecture/invariants.md) | Platform invariants (normative) |
| [architecture/invariant_mapping.md](architecture/invariant_mapping.md) | Invariant → code → test mapping |
| [architecture/platform_layers.md](architecture/platform_layers.md) | Layer model |
| [architecture/ai_change_policy.md](architecture/ai_change_policy.md) | AI-safe modification policy |
| [architecture/adr/README.md](architecture/adr/README.md) | Architecture decision records |
| [PR_P0_ETL_STABILIZATION.md](PR_P0_ETL_STABILIZATION.md) | ETL worker stabilization |

---

## Analytics & Economics

| Document | Purpose |
|----------|---------|
| [analytics/financial_semantics.md](analytics/financial_semantics.md) | Financial KPI semantics |
| [economics/sku_unit_economics.md](economics/sku_unit_economics.md) | SKU unit economics |
| [economics/cost_coverage.md](economics/cost_coverage.md) | COGS coverage & trust gating |
| [economics/inventory_economics.md](economics/inventory_economics.md) | Inventory economics model |
| [economics/reconciliation_model.md](economics/reconciliation_model.md) | Payout reconciliation |

---

## Product & Frontend

| Document | Purpose |
|----------|---------|
| [product/refined_roadmap.md](product/refined_roadmap.md) | Product roadmap (seller-focused) |
| [product/seller_workflows.md](product/seller_workflows.md) | Seller workflows |
| [product/onboarding.md](product/onboarding.md) | Onboarding |
| [frontend/seller_dashboard.md](frontend/seller_dashboard.md) | Dashboard UX |
| [frontend/localization.md](frontend/localization.md) | UI localization |
| [ops/frontend-deploy.md](ops/frontend-deploy.md) | Frontend VPS deploy |

---

## Runtime & Operations

| Document | Purpose |
|----------|---------|
| [runtime/runtime_architecture.md](runtime/runtime_architecture.md) | Runtime automation |
| [runtime/queue_observability.md](runtime/queue_observability.md) | Queue observability |
| [operations/metrics_catalog.md](operations/metrics_catalog.md) | Metrics catalog |
| [operations/failure_modes.md](operations/failure_modes.md) | Failure modes |

---

## Release & Archive

| Document | Purpose |
|----------|---------|
| [release/v0.6-mvp-intelligence.md](release/v0.6-mvp-intelligence.md) | v0.6 release notes |
| [release/readme_cutover_report.md](release/readme_cutover_report.md) | README cutover report (6.4.2) |
| [archive/README_pre_v06.md](archive/README_pre_v06.md) | Full pre-v0.6 README snapshot (2923 lines) |
| [archive/README.md](archive/README.md) | Archive index |

---

## Audit scripts

```bash
# Phase 6.3.0 / 6.3.0B inventory + calibration
.venv/bin/python scripts/phase_630_inventory_audit.py --limit 4

# Phase 6.2 migration audit
.venv/bin/python scripts/phase_621_migration_audit.py --user-id <UUID> --limit 10

# General recommendation quality
.venv/bin/python scripts/ai_recommendation_quality_audit.py --user-id <UUID> --limit 10
```

Reports: `reports/phase_630_inventory_audit.json`
