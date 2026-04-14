"""Naming helpers for export files."""


def filename_for_month(month: str) -> str:
    """Return canonical xlsx filename for a month (YYYY-MM)."""
    return f"factures_{month}.xlsx"
