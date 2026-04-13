from app.pipeline.duplicate import find_duplicate


def _make_fetch(rows):
    """Return a fake _fetch function that returns pre-set rows."""
    def fetch(supplier_id, fields, db):
        return rows
    return fetch


class TestFindDuplicate:
    def test_same_invoice_number(self):
        dup_row = {"id": "10", "invoice_number": "FA-001", "amount_ttc": 100.0, "invoice_date": "2025-01-15"}
        result = find_duplicate(
            {"invoice_number": "FA-001", "amount_ttc": 200.0, "invoice_date": "2025-03-01"},
            supplier_id="sup-1",
            _fetch=_make_fetch([dup_row]),
        )
        assert result == dup_row

    def test_same_amount_within_7_days(self):
        dup_row = {"id": "11", "invoice_number": "FA-099", "amount_ttc": 500.00, "invoice_date": "2025-01-10"}
        # _fetch returns it because the real fetch logic matched amount+date
        result = find_duplicate(
            {"invoice_number": "FA-200", "amount_ttc": 500.00, "invoice_date": "2025-01-12"},
            supplier_id="sup-1",
            _fetch=_make_fetch([dup_row]),
        )
        assert result == dup_row

    def test_same_amount_date_too_far(self):
        # 8 days apart, different invoice number -> no match
        result = find_duplicate(
            {"invoice_number": "FA-200", "amount_ttc": 500.00, "invoice_date": "2025-01-20"},
            supplier_id="sup-1",
            _fetch=_make_fetch([]),  # fetch returns nothing because real logic filters it out
        )
        assert result is None

    def test_different_supplier(self):
        # Different supplier -> fetch returns nothing
        result = find_duplicate(
            {"invoice_number": "FA-001"},
            supplier_id="sup-2",
            _fetch=_make_fetch([]),
        )
        assert result is None

    def test_supplier_none(self):
        result = find_duplicate(
            {"invoice_number": "FA-001", "amount_ttc": 100.0},
            supplier_id=None,
        )
        assert result is None


class TestFetchCandidatesIntegration:
    """Test the actual _fetch_candidates logic with a mock DB."""

    def test_invoice_number_match(self):
        from unittest.mock import MagicMock
        from app.pipeline.duplicate import _fetch_candidates

        db = MagicMock()
        query = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.neq.return_value = query
        query.execute.return_value = MagicMock(data=[
            {"id": "1", "invoice_number": "FA-001", "amount_ttc": 100, "invoice_date": "2025-01-15", "state": "done"},
        ])
        result = _fetch_candidates("sup-1", {"invoice_number": "FA-001"}, db)
        assert len(result) == 1

    def test_amount_date_match(self):
        from unittest.mock import MagicMock
        from app.pipeline.duplicate import _fetch_candidates

        db = MagicMock()
        query = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.neq.return_value = query
        query.execute.return_value = MagicMock(data=[
            {"id": "2", "invoice_number": "FA-099", "amount_ttc": 500.0, "invoice_date": "2025-01-10", "state": "done"},
        ])
        result = _fetch_candidates("sup-1", {"invoice_number": "FA-200", "amount_ttc": 500.0, "invoice_date": "2025-01-12"}, db)
        assert len(result) == 1

    def test_amount_date_too_far(self):
        from unittest.mock import MagicMock
        from app.pipeline.duplicate import _fetch_candidates

        db = MagicMock()
        query = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.neq.return_value = query
        query.execute.return_value = MagicMock(data=[
            {"id": "3", "invoice_number": "FA-099", "amount_ttc": 500.0, "invoice_date": "2025-01-01", "state": "done"},
        ])
        result = _fetch_candidates("sup-1", {"invoice_number": "FA-200", "amount_ttc": 500.0, "invoice_date": "2025-01-20"}, db)
        assert len(result) == 0
