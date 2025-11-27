from decimal import Decimal
from typing import Dict, List

from django.db.models import Q

from ..models import (
    DFM,
    Entlueftung,
    Kugelhahn,
    Sondenverschlusskappe,
    StumpfschweissEndkappe,
)
from ..utils import calculate_formula, check_compatibility, format_artikelnummer


def _decimal(value) -> Decimal:
    return Decimal(str(value))


def _compatibility_match(compat_value: str, hvb_size: str, sonden_durchmesser: str) -> bool:
    if not compat_value:
        return True
    hvb_formatted = f"DA {hvb_size}" if hvb_size else ""
    sonden_formatted = f"DA {sonden_durchmesser}" if sonden_durchmesser else ""
    allowed = [part.strip() for part in compat_value.split("|")]
    return hvb_formatted in allowed or sonden_formatted in allowed


def build_sondenverschlusskappen(config, context) -> List[Dict]:
    """Two caps per probe, matching the probe diameter."""
    diameter = str(config.sonden_durchmesser or "").strip()
    queryset = Sondenverschlusskappe.objects.filter(
        Q(sonden_durchmesser__iexact=diameter) | Q(name__icontains=diameter)
    )
    if not queryset.exists():
        return []

    items: List[Dict] = []
    for cap in queryset:
        quantity = cap.menge_statisch
        if cap.menge_formel:
            quantity = calculate_formula(cap.menge_formel, context)
        if quantity is None:
            continue
        if quantity == 0:
            continue
        items.append(
            {
                "artikelnummer": format_artikelnummer(cap.artikelnummer),
                "artikelbezeichnung": cap.artikelbezeichnung,
                "menge": _decimal(quantity),
                "source_table": "Sondenverschlusskappe",
            }
        )
    return items


def build_stumpfschweiss_endkappen(config) -> List[Dict]:
    """Rule set described in the requirements document."""
    items: List[Dict] = []
    hvb_size = str(config.hvb_size)

    def add_cap(cap_obj, qty):
        if not cap_obj or qty <= 0:
            return
        items.append(
            {
                "artikelnummer": format_artikelnummer(cap_obj.artikelnummer),
                "artikelbezeichnung": cap_obj.artikelbezeichnung,
                "menge": _decimal(qty),
                "source_table": "Stumpfschweiss-Endkappe",
            }
        )

    if config.schachttyp == "Verteiler":
        cap = StumpfschweissEndkappe.objects.filter(artikelnummer="2000569").first()
        add_cap(cap, 2)
        return items

    if hvb_size == "63":
        short_cap = StumpfschweissEndkappe.objects.filter(
            hvb_durchmesser="63", is_short_version=True
        ).first()
        normal_cap = StumpfschweissEndkappe.objects.filter(
            artikelnummer="2000569"
        ).first()
        add_cap(short_cap, 1)
        add_cap(normal_cap, 1)
        return items

    caps = StumpfschweissEndkappe.objects.filter(hvb_durchmesser=hvb_size)
    for cap in caps:
        qty = cap.menge_statisch or Decimal("2")
        add_cap(cap, qty)
    return items


def build_entlueftung_components(config) -> List[Dict]:
    """Entlüftung parts – most always included, some with HVB dependencies."""
    items: List[Dict] = []
    hvb_size = str(config.hvb_size)

    for part in Entlueftung.objects.all():
        compat_value = getattr(part, "et_hvb", "")
        if not _compatibility_match(compat_value, hvb_size, config.sonden_durchmesser):
            continue
        qty = part.menge_statisch or Decimal("1")
        items.append(
            {
                "artikelnummer": format_artikelnummer(part.artikelnummer),
                "artikelbezeichnung": part.artikelbezeichnung,
                "menge": qty,
                "source_table": "Entlüftung",
            }
        )
    return items


def build_manifold_components(config) -> List[Dict]:
    """Placeholder for future manifold-specific logic driven by data."""
    return []


def build_plastic_dfm_components(config, context) -> List[Dict]:
    """Build plastic DFM components - only main flowmeter, accessories handled by Kugelhahn"""
    items: List[Dict] = []
    if not config.dfm_type or not config.dfm_type.startswith('K-DFM'):
        return items

    dfm_entries = DFM.objects.filter(durchflussarmatur=config.dfm_type)
    for entry in dfm_entries:
        if not entry.artikelnummer:
            continue
        if entry.et_hvb and not check_compatibility(entry.et_hvb, config.hvb_size, config.sonden_durchmesser, 'hvb'):
            continue
        if entry.et_sonden and not check_compatibility(entry.et_sonden, config.hvb_size, config.sonden_durchmesser, 'sonden'):
            continue
        if entry.dfm_hvb and not check_compatibility(entry.dfm_hvb, config.hvb_size, config.sonden_durchmesser, 'hvb'):
            continue

        quantity = entry.menge_statisch
        if entry.menge_formel:
            quantity = calculate_formula(entry.menge_formel, context)
        if quantity is None:
            continue

        items.append(
            {
                "artikelnummer": format_artikelnummer(entry.artikelnummer),
                "artikelbezeichnung": entry.artikelbezeichnung,
                "menge": _decimal(quantity),
                "source_table": "DFM",
            }
        )
    return items


def build_kugelhahn_components(config, context) -> List[Dict]:
    """Build Kugelhahn components based on specification rules"""
    items: List[Dict] = []
    
    # If no Kugelhahn selected but DFM is plastic, use DN 25 / DA 32 rules
    kugelhahn_type = config.kugelhahn_type
    if not kugelhahn_type and config.dfm_type and config.dfm_type.startswith('K-DFM'):
        kugelhahn_type = "DN 25 / DA 32"  # Default for plastic DFM

    if not kugelhahn_type:
        return items

    da_mapping = {
        "DN 25 / DA 32": "32",
        "DN 32 / DA 40": "40", 
        "DN 40 / DA 50": "50",
        "DN 50 / DA 63": "63",
    }
    da_value = da_mapping.get(kugelhahn_type)
    if not da_value:
        return items

    per_probe = _decimal(config.sondenanzahl)
    hvb_size = str(config.hvb_size)
    probe_size = str(config.sonden_durchmesser)

    def resolve_description(article_number: str, fallback: str) -> str:
        kugelhahn_entry = Kugelhahn.objects.filter(artikelnummer=article_number).first()
        if kugelhahn_entry:
            return kugelhahn_entry.artikelbezeichnung
        dfm_entry = DFM.objects.filter(artikelnummer=article_number).first()
        if dfm_entry:
            return dfm_entry.artikelbezeichnung
        return fallback

    def add_entry(entry):
        quantity = entry.menge_statisch
        if entry.menge_formel:
            quantity = calculate_formula(entry.menge_formel, context)
        if quantity is None or quantity <= 0:
            return
        items.append(
            {
                "artikelnummer": format_artikelnummer(entry.artikelnummer),
                "artikelbezeichnung": entry.artikelbezeichnung,
                "menge": _decimal(quantity),
                "source_table": "Kugelhahn",
            }
        )

    entries = Kugelhahn.objects.filter(kugelhahn=kugelhahn_type)
    for entry in entries:
        if not entry.artikelnummer:
            continue
        if entry.et_hvb and not check_compatibility(entry.et_hvb, hvb_size, probe_size, 'hvb'):
            continue
        if entry.et_sonden and not check_compatibility(entry.et_sonden, hvb_size, probe_size, 'sonden'):
            continue
        if entry.kh_hvb and not check_compatibility(entry.kh_hvb, hvb_size, probe_size, 'hvb'):
            continue
        add_entry(entry)

    return items

