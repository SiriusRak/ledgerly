import re
import unicodedata

from Levenshtein import distance as levenshtein_distance

from app.db import get_supabase

_LEGAL_SUFFIXES = re.compile(r"\b(sarl|sas|sa|eurl|sasu|eirl)\b")


def normalize_name(name: str) -> str:
    s = name.lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = _LEGAL_SUFFIXES.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def find_client(fields: dict, *, db=None) -> dict | None:
    """Match the invoice recipient (dossier client) against the clients table.

    Priority: SIRET exact, then normalized name equality, then Levenshtein < 3.
    Returns None if no confident match.
    """
    db = db or get_supabase()

    siret = (fields.get("client_siret") or "").strip()
    if siret:
        resp = db.table("clients").select("*").eq("siret", siret).limit(1).execute()
        if resp.data:
            return resp.data[0]

    name = fields.get("client_name") or ""
    if not name.strip():
        return None

    norm = normalize_name(name)
    resp = db.table("clients").select("*").execute()
    for row in resp.data:
        candidate_norm = normalize_name(row.get("name") or "")
        if candidate_norm == norm:
            return row
        if levenshtein_distance(norm, candidate_norm) < 3:
            return row

    return None


def find_supplier(fields: dict, *, db=None) -> dict | None:
    db = db or get_supabase()

    siret = (fields.get("siret") or "").strip()
    if siret:
        resp = db.table("suppliers").select("*").eq("siret", siret).limit(1).execute()
        if resp.data:
            return resp.data[0]

    name = fields.get("supplier_name") or ""
    if not name.strip():
        return None

    norm = normalize_name(name)

    resp = db.table("suppliers").select("*").execute()
    for row in resp.data:
        candidate_norm = normalize_name(row.get("name") or "")
        if candidate_norm == norm:
            return row
        if levenshtein_distance(norm, candidate_norm) < 3:
            return row

    return None
