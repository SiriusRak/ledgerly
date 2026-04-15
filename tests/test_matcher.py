from unittest.mock import MagicMock

from app.pipeline.matcher import normalize_name, find_supplier, find_client


class TestNormalize:
    def test_legal_suffix_stripped(self):
        assert normalize_name("Orange SARL") == "orange"

    def test_case_and_suffix(self):
        assert normalize_name("EDF SA") == "edf"

    def test_plain_lower(self):
        assert normalize_name("edf") == "edf"

    def test_accent_stripping(self):
        assert normalize_name("Electricite") == "electricite"
        assert normalize_name("Electricite") == normalize_name("Electricite")

    def test_accent_complex(self):
        assert normalize_name("\u00c9lectricit\u00e9") == "electricite"

    def test_multiple_suffixes(self):
        assert normalize_name("Dupont SAS") == "dupont"

    def test_edf_variants_equal(self):
        a = normalize_name("EDF SA")
        b = normalize_name("edf")
        assert a == b


class TestFindSupplier:
    def _mock_db(self, siret_rows=None, all_rows=None):
        db = MagicMock()
        table = MagicMock()
        db.table.return_value = table

        # Chain for siret lookup
        select = MagicMock()
        table.select.return_value = select
        eq = MagicMock()
        select.eq.return_value = eq
        limit = MagicMock()
        eq.limit.return_value = limit

        if siret_rows is not None:
            limit.execute.return_value = MagicMock(data=siret_rows)
            select.execute.return_value = MagicMock(data=all_rows or [])
        else:
            limit.execute.return_value = MagicMock(data=[])
            select.execute.return_value = MagicMock(data=all_rows or [])

        return db

    def test_siret_exact_match(self):
        row = {"id": "1", "siret": "12345678901234", "name": "EDF"}
        db = self._mock_db(siret_rows=[row])
        result = find_supplier({"siret": "12345678901234", "supplier_name": "EDF"}, db=db)
        assert result == row

    def test_levenshtein_fallback(self):
        row = {"id": "2", "siret": None, "name": "Electricite de France"}
        db = self._mock_db(siret_rows=[], all_rows=[row])
        result = find_supplier({"supplier_name": "Electricite de Franc"}, db=db)
        assert result == row

    def test_no_match(self):
        db = self._mock_db(siret_rows=[], all_rows=[{"id": "3", "name": "Totally Different Corp"}])
        result = find_supplier({"supplier_name": "EDF"}, db=db)
        assert result is None

    def test_no_siret_exact_name_match(self):
        row = {"id": "4", "name": "Orange"}
        db = self._mock_db(siret_rows=[], all_rows=[row])
        result = find_supplier({"supplier_name": "orange"}, db=db)
        assert result == row


class TestFindClient:
    def _mock_db(self, siret_rows=None, all_rows=None):
        db = MagicMock()
        table = MagicMock()
        db.table.return_value = table
        select = MagicMock()
        table.select.return_value = select
        eq = MagicMock()
        select.eq.return_value = eq
        limit = MagicMock()
        eq.limit.return_value = limit
        limit.execute.return_value = MagicMock(data=siret_rows or [])
        select.execute.return_value = MagicMock(data=all_rows or [])
        return db

    def test_client_siret_match(self):
        row = {"id": "c1", "siret": "99999999900001", "name": "Boulangerie Dupont"}
        db = self._mock_db(siret_rows=[row])
        result = find_client({"client_siret": "99999999900001", "client_name": "Dupont"}, db=db)
        assert result == row

    def test_client_name_fuzzy(self):
        row = {"id": "c2", "name": "Cafe du Centre"}
        db = self._mock_db(all_rows=[row])
        result = find_client({"client_name": "Cafe du Centr"}, db=db)
        assert result == row

    def test_no_client_info(self):
        db = self._mock_db(all_rows=[{"id": "c3", "name": "Other"}])
        result = find_client({}, db=db)
        assert result is None

    def test_no_match(self):
        db = self._mock_db(all_rows=[{"id": "c4", "name": "Totally Different"}])
        result = find_client({"client_name": "Nowhere"}, db=db)
        assert result is None
