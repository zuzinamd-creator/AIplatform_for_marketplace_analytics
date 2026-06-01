"""Semantics domain errors (leaf module — no inventory imports)."""


class UnsupportedSemanticsVersionError(ValueError):
    """Row or policy references a semantics version that is not allowed."""

    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(f"Unsupported inventory semantics version: {version}")
