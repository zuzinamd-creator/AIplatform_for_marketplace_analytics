# Release Documentation

| Release | Document | Status |
|---------|----------|--------|
| **Phase 9.6B-2A — Trust Integration Deploy** | [phase_96b2a_deployment_certification.md](phase_96b2a_deployment_certification.md) | **CERTIFIED** (`7aedd90`, bundle `index-BqjAbDai.js`) |
| Scope | Frontend trust on period compare, economics, SKU drilldown; smoke PASS; DEPLOY == GIT | 2026-07-10 |
| **Phase 9.3A — Invite System** | *(this index)* | **Runtime deployed** — commit pending 9.3X-C |
| Workspace | `registration_invites`, admin invites API/UI, invite registration | Migration `0035` applied in production DB |
| **Phase 9.2C — Admin Panel (read-only users)** | *(this index)* | **Committed** (`b85854c`) |
| Scope | `GET /api/v1/admin/users`, `/app/admin/users`, `platform_admin` nav gates | Read-only user list |
| **Phase 9.2B-R1 — Recovery assess alignment** | `scripts/production-recovery.sh` | **In repo** — `CERTIFIED_SHA` update in 9.3X-C |
| Scope | Recovery script SHA pointer for Phase 9.2 deployment | Assess-only; no runtime change |
| **Phase 9.2B — Platform roles** | Migration `0034_user_role_platform_admin` | **Committed** (`b85854c`) |
| Scope | `users.role` (`seller` \| `platform_admin`), `require_platform_admin` dep | Seed platform admin by email |
| **Phase 9.1A — Registration gate** | `REGISTRATION_MODE=invite_only` | **Committed** (`83daf8c`) |
| Scope | Blocks open `POST /register` without invite flow | Production default |
| **Phase 8.1 — Promotion Expenses MVP** | **[phase_81_production_release.md](phase_81_production_release.md)** | **CERTIFIED** |
| Tag `v8.1-promotion-expenses-mvp` | Feature `48a8d7c` · CI `53d730b` · Run `28944603932` | Production accepted 2026-07-07 · CI GREEN 2026-07-08 |
| v0.6-mvp-intelligence | [v0.6-mvp-intelligence.md](v0.6-mvp-intelligence.md) | Superseded for profit KPI scope |
| CHANGELOG | [CHANGELOG.md](CHANGELOG.md) | 6.5.1 |
| Release readiness (6.5.0) | [v0.6_release_readiness_report.md](v0.6_release_readiness_report.md) | Complete |
| Hardening readiness (6.5.1) | [hardening_readiness.md](hardening_readiness.md) | Complete |
| Archetype framework (6.5.2) | [phase_652_archetype_framework_report.md](phase_652_archetype_framework_report.md) | Complete |
| Archetype validation readiness | [archetype_validation_readiness.md](archetype_validation_readiness.md) | Complete |
| Archetype validation design | [../testing/archetype_validation_framework.md](../testing/archetype_validation_framework.md) | 6.5.2 |
| Multi-seller replay (6.5.3) | [multi_seller_replay_report.md](multi_seller_replay_report.md) | Complete |
| Release preparation (6.6.0) | [phase_660_release_preparation_report.md](phase_660_release_preparation_report.md) | Complete |
| v0.6 manifest | [v06_release_manifest.md](v06_release_manifest.md) | 6.6.0 |
| v0.6 readiness | [v06_release_readiness.md](v06_release_readiness.md) | 6.6.0 |
| Technical debt | [technical_debt_register.md](technical_debt_register.md) | 6.6.0 |
| v0.6 pilot validated release notes | [v06_pilot_validated_release_notes.md](v06_pilot_validated_release_notes.md) | 6.6.1 |
| Milestone freeze (6.6.1) | [phase_661_milestone_freeze_report.md](phase_661_milestone_freeze_report.md) | Complete |
| Production testing baseline (6.8.2) | [production_testing_baseline_6.8.2.md](production_testing_baseline_6.8.2.md) | RC frozen |
| v0.7 roadmap | [../roadmap/v07_candidate_features.md](../roadmap/v07_candidate_features.md) | Draft |
| Test stabilization (6.5.1) | [test_stabilization_report.md](test_stabilization_report.md) | Complete |
| MVP hardening plan | [mvp_hardening_plan.md](mvp_hardening_plan.md) | Complete |
| Threshold catalog | [../ai/threshold_catalog.md](../ai/threshold_catalog.md) | 6.5.1 |
| README cutover (6.4.2) | [readme_cutover_report.md](readme_cutover_report.md) | Complete |

**Tag:** `v8.1-promotion-expenses-mvp` — **CERTIFIED** (Phase 8.1 closed 2026-07-08).  
**Phase 9.x:** committed through 9.2 (`b85854c`); 9.3A in working tree — baseline certification in Phase 9.3X-C.  
**Entry point:** [README.md](../../README.md) · **Manifest:** [phase_81_production_release.md](phase_81_production_release.md)  
**Tag:** `v0.6-pilot-validated` — **GO** (milestone frozen 6.6.1).
