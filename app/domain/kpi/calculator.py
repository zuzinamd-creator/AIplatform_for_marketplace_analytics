from decimal import Decimal


class KPICalculator:
    """
    Pure domain logic for financial and performance calculations.
    No framework dependencies.
    """

    @staticmethod
    def calculate_margin(revenue: Decimal, cost: Decimal) -> Decimal:
        """
        Calculate margin percentage: ((revenue - cost) / revenue) * 100
        """
        if revenue <= Decimal("0"):
            return Decimal("0")
        return ((revenue - cost) / revenue) * Decimal("100")

    @staticmethod
    def calculate_profit(revenue: Decimal, cost: Decimal) -> Decimal:
        """
        Calculate absolute net profit.
        """
        return revenue - cost
