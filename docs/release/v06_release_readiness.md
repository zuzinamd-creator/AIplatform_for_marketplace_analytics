# v0.6 Release Readiness — `v0.6-pilot-validated`

**Date:** 2026-06-07  
**Phase:** 6.6.0  
**Target tag:** `v0.6-pilot-validated`  
**Scope:** Pilot client milestone — **not** external multi-tenant MVP

---

## Executive summary

The repository is ready to freeze a **pilot-validated milestone**. Period Intelligence MVP is stable on the production pilot seller with zero AI metric regression. Test suite is green (299/299). Documentation, validation framework, and release artifacts are complete.

Multi-archetype generalization remains incomplete but is **explicitly out of scope** for this tag per product direction (single primary client).

### Decision preview

| Tag | Recommendation |
|-----|----------------|
| **`v0.6-pilot-validated`** | **GO** |
| External MVP | **NO-GO** (unchanged, not a goal) |

---

## Dimension scores

| Dimension | Score | Weight | Weighted | Evidence |
|-----------|-------|--------|----------|----------|
| **Architecture** | 88 | 15% | 13.2 | Layer model, ADRs, governance check, RLS |
| **AI** | 90 | 25% | 22.5 | Pilot metrics stable; 0 regression; threshold catalog |
| **Testing** | 92 | 20% | 18.4 | 299/299 unit tests; archetype manifest tests |
| **Security** | 85 | 15% | 12.8 | RLS, protected user guards, `rls_leak_test.py` |
| **Documentation** | 86 | 15% | 12.9 | Hub, release bundle, cutover, replay reports |
| **Maintainability** | 82 | 10% | 8.2 | Audit scripts, replay harness; doc debt tracked |

### **Overall release readiness: 88 / 100**

**Interpretation:**

| Score | Meaning |
|-------|---------|
| ≥ 85 | **GO** for pilot-validated milestone tag |
| 70–84 | GO for internal milestone with caveats |
| < 70 | NO-GO |

---

## 1. Architecture — 88/100

### Strengths

- Clear layer model (`docs/architecture/platform_layers.md`)
- 8 ADRs for core decisions (ledger, queue, semantics)
- `architecture_governance_check.py` with domain allowlists
- Tenant isolation via RLS (`TenantSession`)
- Deterministic ETL → governed snapshots → analysts pipeline

### Gaps

- Domain layer SQLAlchemy exceptions (allowlisted, TD-M04)
- Operating Director scaffold not integrated (TD-M08)
- Some services large (report_service, pipeline) — grandfathered

---

## 2. AI — 90/100

### Strengths

- 10 domain analysts, priority engine, inventory intelligence
- Phase 6.3.0B calibration validated (SU 80.3, AI Readiness 86.1)
- Dashboard Echo 0%, Actionable 100%
- Replay confirms bit-stable metrics vs pilot baseline
- Threshold catalog documents ~70 constants

### Gaps

- Single-seller validation (accepted for pilot tag)
- Business Coverage 50%
- Thresholds not config-externalized (TD-H02)
- 4 archetype GAPs documented, not blocking pilot client

---

## 3. Testing — 92/100

### Strengths

- **299/299** unit tests pass (Phase 6.5.1 stabilization)
- Archetype manifest schema tests (8 tests)
- AI governance, insight engine, inventory intelligence unit coverage
- Integration test suite present
- Protected production user/email in `conftest.py`

### Gaps

- Line coverage ~62% (acceptable for MVP)
- Multi-seller replay not in CI (DB-dependent)
- 3 pytest warnings (mock hygiene, TD-L06)

---

## 4. Security — 85/100

### Strengths

- RLS enforced on tenant tables
- `scripts/rls_leak_test.py` available
- Protected production identities in tests
- Auth JWT, password recovery implemented
- No bypass RLS outside allowlist (governance check)

### Gaps

- Ops JSON pages exist (hidden in MVP mode)
- `.env` not in repo (correct) — secrets management operator-dependent
- SMTP credentials file pattern (gitignored)

---

## 5. Documentation — 86/100

### Strengths

- v0.6 README (491 lines), documentation hub
- Complete Phase 6 release trail (6.2.1 → 6.5.3)
- Threshold catalog, archetype framework, replay report
- Archive for pre-v0.6 README

### Gaps

- Root CHANGELOG stale (TD-M01)
- ~140 docs not in hub index (TD-M02)
- Trust doc triplication (TD-M03)

---

## 6. Maintainability — 82/100

### Strengths

- Phase audit scripts with JSON output
- `multi_seller_replay.py` orchestrator
- `archetype_validation.py` reusable module
- Technical debt register (this phase)
- v0.7 roadmap drafted

### Gaps

- Reports JSON accumulation (TD-M05)
- 59 script files — some legacy validation scripts rarely run
- Frontend 219MB (mostly node_modules) — normal for SPA

---

## Pilot validation summary

| Check | Status |
|-------|--------|
| AI metrics stable on replay | ✅ |
| Zero AI regression | ✅ |
| Insight expectations PASS (high_inventory) | ✅ |
| Unit tests green | ✅ |
| RLS enforced | ✅ |
| Production AI unchanged in 6.5.x–6.6.0 | ✅ |
| Documentation complete for pilot scope | ✅ |

---

## Comparison to Phase 6.5.0 scores

| Metric | 6.5.0 | 6.6.0 | Delta |
|--------|-------|-------|-------|
| Overall readiness | 74 | **88** | +14 |
| Test health | 78 | 92 | +14 |
| Documentation | 84 | 86 | +2 |
| Pilot generalization | 42 | N/A* | scoped out |

\*Generalization removed from pilot tag criteria; tracked in debt register instead.

---

## Related documents

- [v06_release_manifest.md](v06_release_manifest.md)
- [technical_debt_register.md](technical_debt_register.md)
- [phase_660_release_preparation_report.md](phase_660_release_preparation_report.md)
- [multi_seller_replay_report.md](multi_seller_replay_report.md)
