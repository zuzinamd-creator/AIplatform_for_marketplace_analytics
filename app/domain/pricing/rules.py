from decimal import Decimal


class PricingRules:
    """
    Pure domain rules for marketplace pricing optimization and cost analysis.
    """

    @staticmethod
    def calculate_break_even_price(cost: Decimal, target_markup_percent: Decimal) -> Decimal:
        """
        Calculate recommended selling price to achieve target markup percentage.
        """
        if target_markup_percent < Decimal("0"):
            raise ValueError("Target markup percent cannot be negative")
        return cost * (Decimal("1.0") + target_markup_percent / Decimal("100"))
