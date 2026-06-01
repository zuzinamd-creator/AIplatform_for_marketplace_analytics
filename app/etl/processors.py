"""
ETL processing placeholders.

MVP: structure only — marketplace-specific transforms and KPI rules
will be implemented in the next iteration.
"""

from typing import Any

import pandas as pd

from app.models.report import Marketplace


def normalize_marketplace_data(df: pd.DataFrame, marketplace: Marketplace) -> pd.DataFrame:
    """Placeholder: normalize WB/Ozon column names and types."""
    # TODO: marketplace-specific column mapping
    _ = marketplace
    return df.copy()


def extract_products_placeholder(
    df: pd.DataFrame,
    marketplace: Marketplace,
) -> list[dict[str, Any]]:
    """Placeholder: derive product records from report rows."""
    _ = marketplace
    return []


def extract_costs_placeholder(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Placeholder: derive cost_history records from cost file."""
    return []


def aggregate_kpis_placeholder(
    df: pd.DataFrame,
    marketplace: Marketplace,
) -> list[dict[str, Any]]:
    """Placeholder: aggregate revenue, orders, margin into metrics rows."""
    _ = df, marketplace
    return []
