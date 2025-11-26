from decimal import Decimal
from typing import Dict, List

from ..models import (
    DFM,
    Entlueftung,
    Kugelhahn,
    Sondenverschlusskappe,
    StumpfschweissEndkappe,
)


def _decimal(value) -> Decimal:
    return Decimal(str(value))


def _compatibility_match(compat_value: str, hvb_size: str, sonden_durchmesser: str) -> bool:
    if not compat_value:
        return True
    hvb_formatted = f"DA {hvb_size}" if hvb_size else ""
    sonden_formatted = f"DA {sonden_durchmesser}" if sonden_durchmesser else ""
    allowed = [part.strip() for part in compat_value.split("|")]
    return hvb_formatted in allowed or sonden_formatted in allowed


def build_sondenverschlusskappen(config) -> List[Dict]:
    """Two caps per probe, matching the probe diameter."""
    diameter = str(config.sonden_durchmesser or "").strip()
    cap = (
        Sondenverschlusskappe.objects.filter(sonden_durchmesser=diameter).first()
        or Sondenverschlusskappe.objects.filter(name__icontains=diameter).first()
    )
    if not cap:
        return []
    quantity = _decimal(config.sondenanzahl * 2)
    caps = [
        {
            "artikelnummer": cap.artikelnummer,
            "artikelbezeichnung": cap.artikelbezeichnung,
            "menge": quantity,
            "source": "Sondenverschlusskappe",
        }
    ]

    if str(config.hvb_size) == "63":
        hvb_cap = (
            Sondenverschlusskappe.objects.filter(sonden_durchmesser="63").first()
            or Sondenverschlusskappe.objects.filter(name__icontains="63").first()
        )
        if hvb_cap:
            caps.append(
                {
                    "artikelnummer": hvb_cap.artikelnummer,
                    "artikelbezeichnung": hvb_cap.artikelbezeichnung,
                    "menge": _decimal(2),
                    "source": "Sondenverschlusskappe",
                }
            )

    return caps


def build_stumpfschweiss_endkappen(config) -> List[Dict]:
    """Rule set described in the requirements document."""
    items: List[Dict] = []
    hvb_size = str(config.hvb_size)

    def add_cap(cap_obj, qty):
        if not cap_obj or qty <= 0:
            return
        items.append(
            {
                "artikelnummer": cap_obj.artikelnummer,
                "artikelbezeichnung": cap_obj.artikelbezeichnung,
                "menge": _decimal(qty),
                "source": "Stumpfschweiss-Endkappe",
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
                "artikelnummer": part.artikelnummer,
                "artikelbezeichnung": part.artikelbezeichnung,
                "menge": qty,
                "source": "Entlüftung",
            }
        )
    return items


def build_manifold_components(config) -> List[Dict]:
    """Special manifold assemblies based on chamber type and configuration"""
    items: List[Dict] = []
    
    # For GN chambers, add manifold components based on configuration
    if config.schachttyp.startswith("GN"):
        # Standard Verteiler Luke for GN chambers with specific configurations
        # This is based on the specification requirements
        items.append(
            {
                "artikelnummer": "2001433",
                "artikelbezeichnung": "Absperrventil Kunststoff - Kugelhahn Standard Verteiler Luke",
                "menge": _decimal(config.sondenanzahl),
                "source_table": "Manifold",
            }
        )
    
    return items


def build_plastic_dfm_components(config) -> List[Dict]:
    """Build plastic DFM components - only main flowmeter, accessories handled by Kugelhahn"""
    items: List[Dict] = []
    if not config.dfm_type or not config.dfm_type.startswith('K-DFM'):
        return items

    # Only add the main flowmeter article
    dfm_main = DFM.objects.filter(durchflussarmatur=config.dfm_type).first()
    if dfm_main:
        items.append({
            "artikelnummer": dfm_main.artikelnummer.split(".")[0],
            "artikelbezeichnung": dfm_main.artikelbezeichnung,
            "menge": _decimal(config.sondenanzahl),
            "source_table": "DFM",
        })
    
    return items


def build_kugelhahn_components(config) -> List[Dict]:
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

    def add(article_number, fallback_bez, quantity):
        if quantity <= 0:
            return
        bezeichnung = resolve_description(article_number, fallback_bez)
        items.append(
            {
                "artikelnummer": article_number,
                "artikelbezeichnung": bezeichnung,
                "menge": quantity,
                "source_table": "Kugelhahn",
            }
        )

    # DN 25 / DA 32 - Most common for plastic DFM
    if da_value == "32":
        # Only add if explicit Kugelhahn selected (not for plastic DFM default)
        if config.kugelhahn_type:
            add("2000852", "Absperrventil Kunststoff - Kugelhahn DA 32 mm ohne Einlegeteil", per_probe)
        
        # Always add accessories for DA 32 (per spec)
        add("2001167", "Absperrventil - KST - ZUB - KH32 - Überwurfmutter - SKS", per_probe * 2)
        
        # HVB 63 specific part
        if hvb_size == "63":
            add("2001179", "GN Einschweißteil - DA 63 mm", per_probe)
        
        # Probe diameter specific parts
        if probe_size == "32":
            add("2001178", "GN Einschweißteil - DA 32 mm", per_probe)
        elif probe_size in {"40", "50"}:
            add("2001177", "GN Einschweißteil - DA 40 mm", per_probe)
            
        if probe_size == "50":
            add("8000415", "Special component for DA 50", per_probe)
            
    elif da_value == "40":
        add("2000819", "Absperrventil Kunststoff - Kugelhahn DA 40 mm ohne Einlegeteil", per_probe)
        add("2001286", "Absperrventil Kunststoff - Kugelhahn DA 40 mm PE Stutzen kurz - Einlegeteil", per_probe * 2)
        if probe_size == "50":
            add("8000416", "Heizdorn-Reduktion DA 50 / 40", per_probe)
            
    elif da_value == "50":
        add("2000821", "Absperrventil Kunststoff - Kugelhahn DA 50 mm ohne Einlegeteil", per_probe)
        add("2000791", "Absperrventil Kunststoff - Kugelhahn DA 50 mm PE Stutzen kurz - Einlegeteil", per_probe * 2)
        
    elif da_value == "63":
        add("2000820", "Absperrventil Kunststoff - Kugelhahn DA 63 mm ohne Einlegeteil", per_probe)
        add("2000793", "Absperrventil Kunststoff - Kugelhahn DA 63 mm PE Stutzen - Einlegeteil", per_probe * 2)

    return items

