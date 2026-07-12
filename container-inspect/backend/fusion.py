"""Conflict reconciliation. LOCKED precedence: Human > Metrology > Vision.

Every finding records which source produced it and whether a human overrode it.
"""

PRECEDENCE = ("human", "metrology", "vision")  # highest first


def reconcile(findings: list) -> list:
    """Apply precedence to conflicting findings; human override wins always."""
    raise NotImplementedError("M3: fusion/reconcile")
