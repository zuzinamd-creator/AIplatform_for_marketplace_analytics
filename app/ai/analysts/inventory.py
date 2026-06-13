"""Inventory domain analyst — slow movers, dead stock, frozen capital, concentration, risk."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.domain.inventory.intelligence import (
    DEAD_STOCK_THRESHOLD_DAYS,
    FROZEN_CAPITAL_HIGH_SHARE,
    INVENTORY_RISK_ITEM_THRESHOLD,
    SLOW_MOVER_THRESHOLD_DAYS,
    STOCK_CONCENTRATION_HIGH,
)
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
    InventorySkuRow,
)


class InventoryAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.INVENTORY

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        inv = package.inventory
        evidence = self._evidence_from_package(package)

        if not inv.inventory_signals_available:
            return self._output(
                [
                    DomainFindingDTO(
                        finding_id="inventory_limited_signals",
                        statement=(
                            f"Governed package lists {inv.sku_count} SKUs without warehouse snapshots; "
                            "inventory advisory is limited to catalog scale."
                        ),
                        confidence=Decimal("0.6"),
                        severity="low",
                        evidence_refs=evidence,
                        recommended_actions=[
                            "Загрузите отчёт реализации WB — ETL построит снимки остатков для советов по складу.",
                        ],
                    )
                ],
                insufficient_data=True,
            )

        findings: list[DomainFindingDTO] = []

        if inv.dead_stock_count >= 1:
            top = inv.top_dead_stock[:3]
            sku_hint = ", ".join(s.sku for s in top)
            frozen_hint = _frozen_hint(top)
            findings.append(
                DomainFindingDTO(
                    finding_id="inventory_dead_stock",
                    statement=(
                        f"Мёртвый сток: {inv.dead_stock_count} SKU без продаж "
                        f"{DEAD_STOCK_THRESHOLD_DAYS}+ дней при ненулевых остатках."
                    ),
                    confidence=Decimal("0.91"),
                    severity="high" if inv.dead_stock_count >= INVENTORY_RISK_ITEM_THRESHOLD else "medium",
                    evidence_refs=evidence + [f"sku:{s.sku}" for s in top[:2]],
                    recommended_actions=[
                        f"Мёртвый сток: {inv.dead_stock_count} SKU без продаж {DEAD_STOCK_THRESHOLD_DAYS}+ дней"
                        + (f" ({sku_hint})" if sku_hint else "")
                        + (f", заморожено {frozen_hint}." if frozen_hint else ".")
                        + " Распродайте, уберите из ассортимента или запустите акцию."
                    ],
                )
            )

        if inv.slow_mover_count >= 1:
            top = inv.top_slow_movers[:3]
            sku_hint = ", ".join(s.sku for s in top)
            findings.append(
                DomainFindingDTO(
                    finding_id="inventory_slow_movers",
                    statement=(
                        f"Медленная оборачиваемость: {inv.slow_mover_count} SKU без продаж "
                        f"{SLOW_MOVER_THRESHOLD_DAYS}+ дней при наличии остатков."
                    ),
                    confidence=Decimal("0.88"),
                    severity="medium" if inv.slow_mover_count < INVENTORY_RISK_ITEM_THRESHOLD else "high",
                    evidence_refs=evidence + [f"sku:{s.sku}" for s in top[:2]],
                    recommended_actions=[
                        f"Медленная оборачиваемость: {inv.slow_mover_count} SKU без продаж "
                        f"{SLOW_MOVER_THRESHOLD_DAYS}+ дней"
                        + (f" ({sku_hint})" if sku_hint else "")
                        + ". Снизьте закупку, проверьте цену и видимость карточки."
                    ],
                )
            )

        if inv.frozen_capital_available and inv.total_frozen_capital and inv.total_frozen_capital > 0:
            share = inv.frozen_capital_share_pct
            severity = "medium"
            if share is not None and share >= FROZEN_CAPITAL_HIGH_SHARE:
                severity = "high"
            top = inv.top_frozen_capital_skus[:2]
            sku_hint = ", ".join(s.sku for s in top)
            findings.append(
                DomainFindingDTO(
                    finding_id="inventory_frozen_capital",
                    statement=(
                        f"Заморожено {inv.total_frozen_capital:,.0f} ₽ в остатках на складе"
                        + (f" ({share:.1f}% выручки периода)." if share is not None else ".")
                    ),
                    confidence=Decimal("0.87"),
                    severity=severity,
                    evidence_refs=evidence,
                    recommended_actions=[
                        f"На складе заморожено {inv.total_frozen_capital:,.0f} ₽"
                        + (f" ({share:.1f}% выручки)" if share is not None else "")
                        + (f" — лидеры: {sku_hint}." if sku_hint else ".")
                        + " Ускорьте оборачиваемость или сократите избыточные закупки."
                    ],
                )
            )

        if (
            inv.stock_concentration_top3_pct is not None
            and inv.stock_concentration_top3_pct >= STOCK_CONCENTRATION_HIGH
        ):
            top = inv.top_frozen_capital_skus[:3]
            sku_hint = ", ".join(f"{s.sku} ({s.share_pct:.0f}%)" for s in top if s.share_pct > 0)
            findings.append(
                DomainFindingDTO(
                    finding_id="inventory_stock_concentration",
                    statement=(
                        f"Концентрация остатков: топ-3 SKU держат "
                        f"{inv.stock_concentration_top3_pct:.1f}% замороженного капитала."
                    ),
                    confidence=Decimal("0.86"),
                    severity="high" if inv.stock_concentration_top3_pct >= Decimal("70") else "medium",
                    evidence_refs=evidence,
                    recommended_actions=[
                        f"Капитал в остатках сконцентрирован: топ-3 SKU = "
                        f"{inv.stock_concentration_top3_pct:.0f}% замороженных средств"
                        + (f" ({sku_hint})." if sku_hint else ".")
                        + " Диверсифицируйте ассортимент и не докупайте перегруженные SKU."
                    ],
                )
            )

        if inv.inventory_risk_level in ("medium", "high"):
            drivers: list[str] = []
            if inv.dead_stock_count:
                drivers.append(f"мёртвый сток ({inv.dead_stock_count} SKU)")
            if inv.slow_mover_count:
                drivers.append(f"медленные SKU ({inv.slow_mover_count})")
            if inv.overstock_count:
                drivers.append(f"переизбыток ({inv.overstock_count} SKU)")
            if (
                inv.stock_concentration_top3_pct is not None
                and inv.stock_concentration_top3_pct >= STOCK_CONCENTRATION_HIGH
            ):
                drivers.append(
                    f"концентрация капитала ({inv.stock_concentration_top3_pct:.0f}%)"
                )
            if inv.frozen_capital_share_pct is not None and inv.frozen_capital_share_pct >= FROZEN_CAPITAL_HIGH_SHARE:
                drivers.append(f"замороженный капитал ({inv.frozen_capital_share_pct:.0f}% выручки)")
            driver_text = ", ".join(drivers) if drivers else "структурный складской риск"
            findings.append(
                DomainFindingDTO(
                    finding_id="inventory_risk_high",
                    statement=(
                        f"Складской риск ({inv.inventory_risk_level}): {driver_text}."
                    ),
                    confidence=Decimal("0.85"),
                    severity="high" if inv.inventory_risk_level == "high" else "medium",
                    evidence_refs=evidence,
                    recommended_actions=[
                        f"Риск склада ({inv.inventory_risk_level}): {driver_text}. "
                        "Проведите ревизию остатков, остановите закупку проблемных SKU "
                        "и перераспределите капитал в оборачиваемые позиции."
                    ],
                )
            )

        if not findings:
            return self._output(
                [
                    DomainFindingDTO(
                        finding_id="inventory_healthy",
                        statement=(
                            f"Остатки по {inv.total_skus or inv.sku_count} SKU в норме — "
                            "нет сигналов мёртвого стока, медленной оборачиваемости или концентрации."
                        ),
                        confidence=Decimal("0.75"),
                        severity="low",
                        evidence_refs=evidence,
                        recommended_actions=[
                            "Остатки в норме по текущим порогам — поддерживайте мониторинг оборачиваемости раз в неделю.",
                        ],
                    )
                ]
            )

        return self._output(findings)


def _frozen_hint(rows: tuple[InventorySkuRow, ...]) -> str:
    total = sum((r.frozen_capital or Decimal("0")) for r in rows)
    if total <= 0:
        return ""
    return f"{total:,.0f} ₽"
