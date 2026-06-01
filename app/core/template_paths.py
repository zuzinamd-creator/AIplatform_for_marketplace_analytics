"""Static file templates bundled with the API (survives Docker COPY app)."""

from pathlib import Path

# app/core/template_paths.py -> app
APP_ROOT = Path(__file__).resolve().parents[1]
RESOURCES_DIR = APP_ROOT / "resources"

# Seller-facing download name (keep stable for users).
# NOTE: underlying on-disk template may have a different filename.
COST_IMPORT_TEMPLATE_FILENAME = "Шаблон Себестоимости.xlsx"

# Deterministic resolution order (local/prod packaging):
# 1) app/resources/cost_template.xlsx  (production template drop-in)
# 2) app/resources/Шаблон Себестоимости.xlsx
# 3) app/resources/cost_import_template.xlsx (ASCII fallback for packaging)
COST_IMPORT_TEMPLATE_PRIMARY = RESOURCES_DIR / "cost_template.xlsx"
COST_IMPORT_TEMPLATE_BUNDLE_RU = RESOURCES_DIR / COST_IMPORT_TEMPLATE_FILENAME
COST_IMPORT_TEMPLATE_BUNDLE_ASCII = RESOURCES_DIR / "cost_import_template.xlsx"

# Optional project-level override (local dev / custom template drop-in).
PROJECT_TEMPLATES_DIR = APP_ROOT.parent / "templates"
PROJECT_COST_IMPORT_TEMPLATE = PROJECT_TEMPLATES_DIR / COST_IMPORT_TEMPLATE_FILENAME


def cost_import_template_path() -> Path:
    """Resolve cost import template with deterministic priority."""
    if COST_IMPORT_TEMPLATE_PRIMARY.is_file():
        return COST_IMPORT_TEMPLATE_PRIMARY.resolve()
    if PROJECT_COST_IMPORT_TEMPLATE.is_file():
        return PROJECT_COST_IMPORT_TEMPLATE.resolve()
    if COST_IMPORT_TEMPLATE_BUNDLE_RU.is_file():
        return COST_IMPORT_TEMPLATE_BUNDLE_RU.resolve()
    if COST_IMPORT_TEMPLATE_BUNDLE_ASCII.is_file():
        return COST_IMPORT_TEMPLATE_BUNDLE_ASCII.resolve()
    raise FileNotFoundError(COST_IMPORT_TEMPLATE_FILENAME)


def cost_import_template_resolution() -> dict[str, str | bool]:
    """Debug helper: which candidates exist and which one is selected."""
    candidates = [
        ("primary", COST_IMPORT_TEMPLATE_PRIMARY),
        ("project_override", PROJECT_COST_IMPORT_TEMPLATE),
        ("bundle_ru", COST_IMPORT_TEMPLATE_BUNDLE_RU),
        ("bundle_ascii", COST_IMPORT_TEMPLATE_BUNDLE_ASCII),
    ]
    selected = ""
    for _key, path in candidates:
        if path.is_file():
            selected = str(path.resolve())
            break
    return {
        "selected": selected,
        "primary_exists": COST_IMPORT_TEMPLATE_PRIMARY.is_file(),
        "primary_path": str(COST_IMPORT_TEMPLATE_PRIMARY),
        "ru_exists": COST_IMPORT_TEMPLATE_BUNDLE_RU.is_file(),
        "ru_path": str(COST_IMPORT_TEMPLATE_BUNDLE_RU),
        "ascii_exists": COST_IMPORT_TEMPLATE_BUNDLE_ASCII.is_file(),
        "ascii_path": str(COST_IMPORT_TEMPLATE_BUNDLE_ASCII),
        "project_override_exists": PROJECT_COST_IMPORT_TEMPLATE.is_file(),
        "project_override_path": str(PROJECT_COST_IMPORT_TEMPLATE),
    }
