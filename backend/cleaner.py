from typing import Any, Dict, Optional
from dateutil import parser as dtparser


def clean_city(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw = raw.strip()
    return raw if raw else None


def clean_date_iso(raw: Optional[str]) -> Optional[str]:
    """
    Converts date-ish strings like:
      'saturday 7th feb 2026'
      '7 feb 2026'
      '2026-02-07'
    into ISO:
      '2026-02-07'
    """
    if not raw:
        return None

    raw = raw.strip()
    if not raw:
        return None

    # If already ISO-ish, dateutil will parse it fine anyway.
    try:
        dt = dtparser.parse(raw, dayfirst=True, fuzzy=True)
        return dt.date().isoformat()  # YYYY-MM-DD
    except Exception:
        return None


def clean_shipment(shipment: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ship_from_city": clean_city(shipment.get("ship_from_city")),
        "ship_to_city": clean_city(shipment.get("ship_to_city")),
        "ship_date": clean_date_iso(shipment.get("ship_date")),
    }
