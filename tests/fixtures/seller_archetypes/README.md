# Seller Archetype Fixtures

P0 seller archetypes for AI quality validation (Phase 6.5.2).

| File | Purpose |
|------|---------|
| [manifest.json](manifest.json) | Archetype definitions, metric bands, insight expectations |

**Usage:**

```bash
# Validate single archetype (pilot — requires DB)
.venv/bin/python scripts/archetype_audit_runner.py --archetype high_inventory_seller

# Inventory audit with archetype bands
.venv/bin/python scripts/phase_630_inventory_audit.py --archetype high_inventory_seller --skip-migrate

# All archetypes (pending ones SKIP without user_id)
.venv/bin/python scripts/archetype_audit_runner.py --all
```

See [docs/testing/archetype_validation_framework.md](../../docs/testing/archetype_validation_framework.md).
