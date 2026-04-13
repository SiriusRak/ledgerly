from app.pipeline.confidence import classify


class TestClassify:
    def test_duplicate(self):
        dup = {"invoice_number": "FA-001"}
        result = classify({}, supplier={"id": "1"}, duplicate=dup)
        assert result == ("duplicate", "Duplicate of invoice FA-001")

    def test_new_supplier(self):
        result = classify(
            {"amount_ht": 100, "amount_tva": 20, "amount_ttc": 120},
            supplier=None,
            duplicate=None,
        )
        assert result == ("review", "New supplier")

    def test_vat_mismatch(self):
        result = classify(
            {"amount_ht": 100, "amount_tva": 20, "amount_ttc": 125},
            supplier={"id": "1"},
            duplicate=None,
        )
        assert result == ("review", "VAT mismatch: 100.0+20.0!=125.0")

    def test_auto(self):
        result = classify(
            {"amount_ht": 100, "amount_tva": 20, "amount_ttc": 120},
            supplier={"id": "1"},
            duplicate=None,
        )
        assert result == ("auto", None)
