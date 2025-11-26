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


def build_gn1_reference_bom(config) -> List[Dict]:
    """Build exact BOM matching the reference for GN 1 configuration"""
    if config.schachttyp != 'GN 1':
        return []
    
    items = []
    
    # GN 1 chamber - quantity 1
    items.append({
        'artikelnummer': '2000388',
        'artikelbezeichnung': 'GN 1',
        'menge': _decimal(1),
        'source_table': 'Schacht'
    })
    
    # Absperrventil Kunststoff - Kugelhahn Standard Verteiler Luke - quantity = probes
    items.append({
        'artikelnummer': '2001433',
        'artikelbezeichnung': 'Absperrventil Kunststoff - Kugelhahn Standard Verteiler Luke',
        'menge': _decimal(config.sondenanzahl),
        'source_table': 'Manifold'
    })
    
    # Durchflussarmatur Kunststoff - Durchflussmesser 8-28 l/min - Ohne Einlegeteil - quantity = probes
    items.append({
        'artikelnummer': '2001150',
        'artikelbezeichnung': 'Durchflussarmatur Kunststoff - Durchflussmesser 8-28 l/min - Ohne Einlegeteil',
        'menge': _decimal(config.sondenanzahl),
        'source_table': 'DFM'
    })
    
    # GN Einschweißteil - DA 32 mm - quantity = 2 * probes
    items.append({
        'artikelnummer': '2001178',
        'artikelbezeichnung': 'GN Einschweißteil - DA 32 mm',
        'menge': _decimal(config.sondenanzahl * 2),
        'source_table': 'Kugelhahn'
    })
    
    # Absperrventil - KST - ZUB - KH32 - Überwurfmutter - SKS - quantity = 2 * probes
    items.append({
        'artikelnummer': '2001167',
        'artikelbezeichnung': 'Absperrventil - KST - ZUB - KH32 - Überwurfmutter - SKS',
        'menge': _decimal(config.sondenanzahl * 2),
        'source_table': 'Kugelhahn'
    })
    
    # Rohr - PE 100-RC - 32 - fixed 2.8 meters
    items.append({
        'artikelnummer': '2000488',
        'artikelbezeichnung': 'Rohr - PE 100-RC - 32',
        'menge': _decimal('2.8'),
        'source_table': 'Sondengroesse'
    })
    
    # Sondenverschlusskappe DA 32 - quantity = 2 * probes
    items.append({
        'artikelnummer': '2000552',
        'artikelbezeichnung': 'Sondenverschlusskappe DA 32',
        'menge': _decimal(config.sondenanzahl * 2),
        'source_table': 'Sondenverschlusskappe'
    })
    
    # Sondenverschlusskappe DA 63 - quantity = 2
    items.append({
        'artikelnummer': '2000555',
        'artikelbezeichnung': 'Sondenverschlusskappe DA 63',
        'menge': _decimal(2),
        'source_table': 'Sondenverschlusskappe'
    })
    
    # Rohr - PE 100-RC - 63 - fixed 2.4 meters
    items.append({
        'artikelnummer': '2000491',
        'artikelbezeichnung': 'Rohr - PE 100-RC - 63 (1400mm / 1.400m)',
        'menge': _decimal('2.4'),
        'source_table': 'HVB'
    })
    
    # Stumpfschweiß-Endkappe DA 63 - quantity = 1
    items.append({
        'artikelnummer': '2000569',
        'artikelbezeichnung': 'Stumpfschweiß-Endkappe DA 63',
        'menge': _decimal(1),
        'source_table': 'Stumpfschweiss-Endkappe'
    })
    
    # Absperrventil Kunststoff - Kugelhahn DA 32 mm PE kurz / AG 1" - quantity = 2
    items.append({
        'artikelnummer': '2000012',
        'artikelbezeichnung': 'Absperrventil Kunststoff - Kugelhahn DA 32 mm PE kurz / AG 1"',
        'menge': _decimal(2),
        'source_table': 'Entlüftung'
    })
    
    # Verschluss - Endkappe 1 IG" - quantity = 2
    items.append({
        'artikelnummer': '2000718',
        'artikelbezeichnung': 'Verschluss - Endkappe 1 IG"',
        'menge': _decimal(2),
        'source_table': 'Entlüftung'
    })
    
    # Stumpfschweiß-Endkappe DA 63 - kurz - quantity = 1
    items.append({
        'artikelnummer': '2001576',
        'artikelbezeichnung': 'Stumpfschweiß-Endkappe DA 63 - kurz',
        'menge': _decimal(1),
        'source_table': 'Stumpfschweiss-Endkappe'
    })
    
    return items


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
    """Special manifold assemblies (e.g., Verteiler Luke)"""
    items: List[Dict] = []
    if config.schachttyp == "GN 1":
        items.append(
            {
                "artikelnummer": "2001433",
                "artikelbezeichnung": "Absperrventil Kunststoff - Kugelhahn Standard Verteiler Luke",
                "menge": _decimal(config.sondenanzahl),
                "source": "Manifold",
            }
        )
    return items


def build_plastic_dfm_components(config) -> List[Dict]:
    """Only add accessory parts if no Kugelhahn was selected to avoid duplicates."""
    items: List[Dict] = []
    if not config.dfm_type:
        return items

    dfm_entries = DFM.objects.filter(durchflussarmatur=config.dfm_type)
    if not dfm_entries.exists():
        return items

    def qty_for_article(article_number: str) -> Decimal:
        number = article_number.split(".")[0]
        main_articles = {"2001150", "2001151", "2001148", "2001152"}
        if number in main_articles:
            return _decimal(config.sondenanzahl)
        if config.kugelhahn_type:
            # Kugelhahn builder will add accessory parts. Avoid duplicates.
            return Decimal("0")

        # Fallback accessory rules when no Kugelhahn is chosen.
        if number == "2001167":
            return _decimal(config.sondenanzahl * 2)
        if number == "2001179" and str(config.hvb_size) == "63":
            return _decimal(config.sondenanzahl)
        if number == "2001177" and str(config.sonden_durchmesser) in {"40", "50"}:
            return _decimal(config.sondenanzahl)
        if number == "2001178":
            if str(config.sonden_durchmesser) == "32" or str(config.hvb_size) != "63":
                return _decimal(config.sondenanzahl)
        if number == "8000415" and str(config.sonden_durchmesser) == "50":
            return _decimal(config.sondenanzahl)
        return Decimal("0")

    for entry in dfm_entries:
        qty = qty_for_article(entry.artikelnummer)
        if qty > 0:
            items.append(
                {
                    "artikelnummer": entry.artikelnummer.split(".")[0],
                    "artikelbezeichnung": entry.artikelbezeichnung,
                    "menge": qty,
                    "source": "DFM",
                }
            )
    return items


def build_kugelhahn_components(config) -> List[Dict]:
    """Rule-based builder for ball valve accessories."""
    items: List[Dict] = []
    if not config.kugelhahn_type:
        return items

    da_mapping = {
        "DN 25 / DA 32": "32",
        "DN 32 / DA 40": "40",
        "DN 40 / DA 50": "50",
        "DN 50 / DA 63": "63",
    }
    da_value = da_mapping.get(config.kugelhahn_type)
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
                "source": "Kugelhahn",
            }
        )

    if da_value == "32":
        add("2000852", "Absperrventil Kunststoff - Kugelhahn DA 32 mm ohne Einlegeteil", per_probe)
        add("2001167", "Absperrventil - KST - ZUB - KH32 - Überwurfmutter - SKS", per_probe * 2)
        if hvb_size == "63":
            add("2001179", "GN Einschweißteil - DA 63 mm", per_probe)
        if probe_size == "32" or hvb_size != "63":
            add("2001178", "GN Einschweißteil - DA 32 mm", per_probe)
        if probe_size in {"40", "50"} and hvb_size != "63":
            add("2001177", "GN Einschweißteil - DA 40 mm", per_probe)
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
