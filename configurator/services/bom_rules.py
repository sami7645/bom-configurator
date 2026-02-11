from decimal import Decimal
from typing import Dict, List

from django.db.models import Q

from ..models import (
    DFM,
    Entlueftung,
    Kugelhahn,
    Sondenverschlusskappe,
    StumpfschweissEndkappe,
    HVBStuetze,
    WPVerschlusskappe,
    WPA,
)
from ..utils import calculate_formula, check_compatibility, format_artikelnummer


def _decimal(value) -> Decimal:
    return Decimal(str(value))


def _extract_da_from_kugelhahn_type(kugelhahn_type: str) -> str:
    """
    Dynamically extract DA size from Kugelhahn type name.
    Examples:
        "DN 25 / DA 32" -> "32"
        "DN 32 / DA 40" -> "40"
        "DN 50 / DA 63" -> "63"
    """
    if not kugelhahn_type:
        return None
    import re
    # Extract DA size from pattern like "DN XX / DA YY"
    match = re.search(r'DA\s+(\d{2,3})', kugelhahn_type, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _compatibility_match(compat_value: str, hvb_size: str, sonden_durchmesser: str) -> bool:
    if not compat_value:
        return True
    hvb_formatted = f"DA {hvb_size}" if hvb_size else ""
    sonden_formatted = f"DA {sonden_durchmesser}" if sonden_durchmesser else ""
    allowed = [part.strip() for part in compat_value.split("|")]
    return hvb_formatted in allowed or sonden_formatted in allowed


def build_sondenverschlusskappen(config, context) -> List[Dict]:
    """Sondenverschlusskappe (probe closure caps) - TWO separate items:
    1. HVB Sondenverschlusskappe: 2 pieces based on HVB size
    2. Probe Sondenverschlusskappe: sondenanzahl * 2 pieces based on probe diameter
    
    Business rules:
    - HVB: Always 2 pieces, selected by HVB size (for HVB 63mm, use DA 110)
    - Probes: sondenanzahl * 2 pieces, selected by probe diameter (sonden_durchmesser)
    - These are TWO SEPARATE items in the BOM
    """
    items: List[Dict] = []
    
    sondenanzahl = context.get('sondenanzahl', 0) if context else 0
    if not sondenanzahl:
        sondenanzahl = config.sondenanzahl or 0
    
    # ============================================
    # 1. HVB Sondenverschlusskappe (always 2 pieces)
    # ============================================
    hvb_size = str(config.hvb_size or "").strip()
    if hvb_size:
        # Remove 'mm' suffix if present
        if hvb_size.lower().endswith('mm'):
            hvb_size = hvb_size[:-2].strip()
        
        # Business rule: For HVB 63mm, use DA 110 Sondenverschlusskappe
        # For other HVB sizes, match by HVB size
        if hvb_size == "63":
            target_da_size = "110"
        else:
            target_da_size = hvb_size
        
        # Find Sondenverschlusskappe that matches the target DA size for HVB
        hvb_cap = Sondenverschlusskappe.objects.filter(
            sonden_durchmesser__iexact=target_da_size
        ).first()
        
        if hvb_cap:
            items.append(
                {
                    "artikelnummer": format_artikelnummer(hvb_cap.artikelnummer),
                    "artikelbezeichnung": f"{hvb_cap.artikelbezeichnung} (HVB)",
                    "menge": _decimal("2"),  # Always 2 pieces for HVB
                    "source_table": "Sondenverschlusskappe",
                    "is_finalized": True,  # Mark as finalized
                }
            )
    
    # ============================================
    # 2. Probe Sondenverschlusskappe (sondenanzahl * 2 pieces)
    # ============================================
    sonden_durchmesser = str(config.sonden_durchmesser or "").strip()
    if sonden_durchmesser and sondenanzahl > 0:
        # Remove 'mm' suffix if present
        if sonden_durchmesser.lower().endswith('mm'):
            sonden_durchmesser = sonden_durchmesser[:-2].strip()
        
        # Find Sondenverschlusskappe that matches the probe diameter
        probe_cap = Sondenverschlusskappe.objects.filter(
            sonden_durchmesser__iexact=sonden_durchmesser
        ).first()
        
        if probe_cap:
            # Quantity = sondenanzahl * 2 (2 pieces per probe)
            probe_quantity = sondenanzahl * 2
            
            items.append(
                {
                    "artikelnummer": format_artikelnummer(probe_cap.artikelnummer),
                    "artikelbezeichnung": f"{probe_cap.artikelbezeichnung} (Sonden)",
                    "menge": _decimal(str(probe_quantity)),
                    "source_table": "Sondenverschlusskappe",
                    "is_finalized": True,  # Mark as finalized
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
        # Dynamic: Find normal version (not short) for Verteiler
        # Look for caps that are NOT short version (is_short_version=False or None)
        cap = StumpfschweissEndkappe.objects.filter(
            is_short_version=False
        ).first()
        if not cap:
            # Fallback: if no is_short_version field, get first available
            cap = StumpfschweissEndkappe.objects.first()
        add_cap(cap, 2)
        return items

    if hvb_size == "63":
        # Dynamic: Find short version for HVB 63mm
        short_cap = StumpfschweissEndkappe.objects.filter(
            hvb_durchmesser="63", is_short_version=True
        ).first()
        # Dynamic: Find normal version (not short) for HVB 63mm
        normal_cap = StumpfschweissEndkappe.objects.filter(
            hvb_durchmesser="63", is_short_version=False
        ).first()
        if not normal_cap:
            # Fallback: if no is_short_version field, get first non-short by description
            normal_cap = StumpfschweissEndkappe.objects.filter(
                hvb_durchmesser="63"
            ).exclude(
                artikelbezeichnung__icontains="kurz"
            ).exclude(
                artikelbezeichnung__icontains="short"
            ).first()
        add_cap(short_cap, 1)
        add_cap(normal_cap, 1)
        return items

    caps = StumpfschweissEndkappe.objects.filter(hvb_durchmesser=hvb_size)
    for cap in caps:
        qty = cap.menge_statisch or Decimal("2")
        add_cap(cap, qty)
    return items


def build_entlueftung_components(config, context=None) -> List[Dict]:
    """Entlüftung parts – ALL articles from Entlüftung.csv are included.
    Business rules:
    - ALL Entlüftung articles are included (they are ventilation/bleeding components)
    - Articles that also appear in Kugelhahn/DFM are still included (cross-referenced)
    - Kugelhahn articles (those with "Kugelhahn" in description) should be labeled based on which Kugelhahn type they belong to
    - Quantity uses menge_statisch from CSV (as per Entlüftung CSV structure)"""
    items: List[Dict] = []
    hvb_size = str(config.hvb_size)
    probe_size = str(config.sonden_durchmesser)
    
    from ..models import Kugelhahn, DFM
    
    # Build sets of article numbers from Kugelhahn and DFM (for cross-reference check and labeling)
    kugelhahn_artikelnummern = set(
        Kugelhahn.objects.exclude(artikelnummer__isnull=True)
        .exclude(artikelnummer='')
        .values_list('artikelnummer', flat=True)
    )
    dfm_artikelnummern = set(
        DFM.objects.exclude(artikelnummer__isnull=True)
        .exclude(artikelnummer='')
        .values_list('artikelnummer', flat=True)
    )
    
    # Kugelhahn articles that should be labeled based on Kugelhahn type
    # Dynamically detect: articles with "Kugelhahn" in description that also exist in Kugelhahn table
    def is_kugelhahn_article(part):
        artikelnummer = format_artikelnummer(part.artikelnummer)
        beschreibung = (part.artikelbezeichnung or "").lower()
        return artikelnummer in kugelhahn_artikelnummern and "kugelhahn" in beschreibung
    
    # Determine which Kugelhahn type to use for labeling
    # DA 32 articles belong to regular Kugelhahn (DN 25 / DA 32)
    # DA 40/50 articles would belong to D-Kugelhahn if they existed
    kugelhahn_source = None
    if config.kugelhahn_type:
        # Dynamically extract DA size and check if regular Kugelhahn is DA 32
        regular_da = _extract_da_from_kugelhahn_type(config.kugelhahn_type)
        if regular_da == "32":
            kugelhahn_source = "Kugelhahn"
    
    # Also check D-Kugelhahn type
    if not kugelhahn_source and config.dfm_kugelhahn_type:
        # Dynamically extract DA size and check if D-Kugelhahn is DA 32
        dfm_da = _extract_da_from_kugelhahn_type(config.dfm_kugelhahn_type)
        if dfm_da == "32":
            kugelhahn_source = "D-Kugelhahn"
    
    # Include ALL Entlüftung articles (they are all ventilation/bleeding components)
    for part in Entlueftung.objects.all():
        # Check ET-HVB compatibility (if specified)
        compat_value = getattr(part, "et_hvb", "")
        if not _compatibility_match(compat_value, hvb_size, config.sonden_durchmesser):
            continue
        
        artikelnummer = format_artikelnummer(part.artikelnummer)
        
        # Determine source_table: Kugelhahn articles should be labeled based on Kugelhahn type
        # Dynamically detect if this is a Kugelhahn article (appears in Kugelhahn table and has "Kugelhahn" in description)
        if is_kugelhahn_article(part) and kugelhahn_source:
            source_table = kugelhahn_source
        else:
            source_table = "Entlüftung"
            
        # Use menge_statisch from CSV (as per Entlüftung CSV structure)
        qty = part.menge_statisch or Decimal("1")
        items.append(
            {
                "artikelnummer": artikelnummer,
                "artikelbezeichnung": part.artikelbezeichnung,
                "menge": qty,
                "source_table": source_table,
            }
        )
    return items


def build_manifold_components(config) -> List[Dict]:
    """Placeholder for future manifold-specific logic driven by data."""
    return []


def build_plastic_dfm_components(config, context) -> List[Dict]:
    """Build DFM components (plastic and brass).

    Original behaviour:
    - Only handled plastic DFM types where dfm_type starts with "K-DFM".
    - Brass flowmeter selections (e.g. HC VTR, IMI STAD, IMI TA) were ignored.

    Updated behaviour:
    - Process ANY selected dfm_type (both plastic and brass), as long as it is
      not empty.
    - We still retain the plastic-specific default Kugelhahn mapping
      (DN 25 / DA 32) only for K-DFM series to keep previous logic intact.
    """
    items: List[Dict] = []
    # If no DFM type selected, nothing to build
    if not config.dfm_type:
        return items

    # Determine kugelhahn_type for checking formulas
    kugelhahn_type = config.kugelhahn_type
    # For plastic DFM (K-DFM) we keep the old default behaviour:
    # if no Kugelhahn was explicitly chosen, assume DN 25 / DA 32.
    if not kugelhahn_type and config.dfm_type and config.dfm_type.startswith('K-DFM'):
        kugelhahn_type = "DN 25 / DA 32"

    # Build a map of article numbers to their formulas from Kugelhahn
    kugelhahn_formula_map = {}
    if kugelhahn_type:
        hvb_size = str(config.hvb_size)
        probe_size = str(config.sonden_durchmesser)
        kugelhahn_entries = Kugelhahn.objects.filter(kugelhahn=kugelhahn_type)
        for kh_entry in kugelhahn_entries:
            if not kh_entry.artikelnummer:
                continue
            # Apply same compatibility checks
            if kh_entry.et_hvb and not check_compatibility(kh_entry.et_hvb, hvb_size, probe_size, 'hvb'):
                continue
            if kh_entry.et_sonden and not check_compatibility(kh_entry.et_sonden, hvb_size, probe_size, 'sonden'):
                continue
            if kh_entry.kh_hvb and not check_compatibility(kh_entry.kh_hvb, hvb_size, probe_size, 'hvb'):
                continue
            # Store formula if it exists
            if kh_entry.menge_formel:
                kugelhahn_formula_map[format_artikelnummer(kh_entry.artikelnummer)] = kh_entry.menge_formel

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

        # Calculate quantity: use formula if available, otherwise static value
        quantity = entry.menge_statisch
        if entry.menge_formel:
            quantity = calculate_formula(entry.menge_formel, context)
        elif not entry.menge_formel and entry.menge_statisch:
            # If DFM has only static value but no formula, check if same article
            # exists in Kugelhahn with a formula - if so, use that formula instead
            artikelnummer = format_artikelnummer(entry.artikelnummer)
            if artikelnummer in kugelhahn_formula_map:
                formula = kugelhahn_formula_map[artikelnummer]
                quantity = calculate_formula(formula, context)
        
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


def build_wp_components(config, context) -> List[Dict]:
    """Build WP (heat pump connection) components based on HVB and WP diameters.

    Uses:
    - WPA (excel_files/WPA.csv): Stumpfschweiß-Reduktion DA <HVB> / <WP> kurz
    - WPVerschlusskappe (excel_files/WP-Verschlusskappen.csv): Sondenverschlusskappe DA <WP>

    Business rules (from Excel):
    - For each valid combination of HVB diameter and WP diameter:
      - 2 pieces of the corresponding Stumpfschweiß-Reduktion (from WPA).
      - 2 pieces of the corresponding WP-Verschlusskappe (from WP-Verschlusskappen.csv).
    """
    items: List[Dict] = []

    # HVB size from configuration (may contain "mm" suffix)
    hvb_size = str(config.hvb_size or "").strip()
    if hvb_size.lower().endswith("mm"):
        hvb_size = hvb_size[:-2].strip()

    # WP diameter is passed from the frontend but not stored in the model;
    # we attach it dynamically to the config in generate_bom.
    wp_diameter = str(getattr(config, "wp_diameter", "") or "").strip()

    if not hvb_size or not wp_diameter:
        return items

    # 1) Stumpfschweiß-Reduktion from WPA (reduction DA <HVB> / <WP> kurz)
    import re

    wpa_entries = WPA.objects.filter(name=hvb_size)
    for entry in wpa_entries:
        desc = entry.artikelbezeichnung or ""
        # Expect pattern like "Stumpfschweiß-Reduktion DA 110 / 50 kurz"
        match = re.search(r"DA\s+\d{2,3}\s*/\s*(\d{2,3})", desc)
        if match and match.group(1) == wp_diameter:
            qty = entry.menge_statisch if entry.menge_statisch is not None else Decimal("2")
            items.append(
                {
                    "artikelnummer": format_artikelnummer(entry.artikelnummer),
                    "artikelbezeichnung": entry.artikelbezeichnung,
                    "menge": _decimal(qty),
                    "source_table": "WPA",
                    "is_finalized": True,
                }
            )
            break  # Only one WPA reduction per HVB/WP combination

    # 2) WP-Verschlusskappe for the selected WP diameter
    cap = WPVerschlusskappe.objects.filter(name=wp_diameter).first()
    if cap:
        qty = cap.menge_statisch if cap.menge_statisch is not None else Decimal("2")
        items.append(
            {
                "artikelnummer": format_artikelnummer(cap.artikelnummer),
                "artikelbezeichnung": cap.artikelbezeichnung,
                "menge": _decimal(qty),
                "source_table": "WP-Verschlusskappe",
                "is_finalized": True,
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

    # Dynamically extract DA size from Kugelhahn type name
    da_value = _extract_da_from_kugelhahn_type(kugelhahn_type)
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
        # Only use menge_formel, ignore menge_statisch as per client requirement
        if not entry.menge_formel:
            return  # Skip items without formula
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

    # Special case: GN Einschweißteil DA 63 mm should be included
    # whenever HVB = 63mm, regardless of Kugelhahn type
    # Dynamically find any Einschweißteil with DA 63 that matches HVB = 63mm
    # This works for current and future DA 63 Einschweißteil items
    if hvb_size == "63":
        import re
        # Find all Einschweißteil items and check if they're DA 63
        all_einschweiss = Kugelhahn.objects.filter(
            artikelbezeichnung__icontains="Einschweißteil"
        )
        for entry in all_einschweiss:
            # Extract DA size from description (e.g., "DA 63 mm" -> "63")
            da_match = re.search(r'DA\s+(\d{2,3})\s*mm', entry.artikelbezeichnung or "", re.IGNORECASE)
            if da_match and da_match.group(1) == "63":
                # Check ET-HVB compatibility (should be DA 63)
                if entry.et_hvb and check_compatibility(entry.et_hvb, hvb_size, probe_size, 'hvb'):
                    quantity = calculate_formula("=sondenanzahl", context)
                    if quantity and quantity > 0:
                        items.append({
                            "artikelnummer": format_artikelnummer(entry.artikelnummer),
                            "artikelbezeichnung": entry.artikelbezeichnung,
                            "menge": _decimal(quantity),
                            "source_table": "Kugelhahn",
                        })
                        break  # Only add one DA 63 Einschweißteil
    
    entries = Kugelhahn.objects.filter(kugelhahn=kugelhahn_type)
    for entry in entries:
        if not entry.artikelnummer:
            continue
        
        artikelbezeichnung = entry.artikelbezeichnung or ""
        is_einschweiss = "Einschweißteil" in artikelbezeichnung
        
        # Extract DA size from description (e.g., "DA 63 mm" -> "63")
        import re
        da_match = re.search(r'DA\s+(\d{2,3})\s*mm', artikelbezeichnung, re.IGNORECASE)
        article_da_size = None
        if da_match:
            article_da_size = da_match.group(1)
        
        # Smart detection for Einlegeteil items that need sondenanzahl * 2
        # Rule: "The quantity is number of probes times two (for HVB and probes)"
        # Detect items with "Einlegeteil" but not "ohne Einlegeteil"
        is_einlegeteil = "Einlegeteil" in artikelbezeichnung and "ohne Einlegeteil" not in artikelbezeichnung
        
        if is_einlegeteil:
            # IMPORTANT: Einlegeteil articles must still respect compatibility rules.
            # Enforce the same ET-HVB / ET-Sonden / KH-HVB checks as for other Kugelhahn items
            if entry.et_hvb and not check_compatibility(entry.et_hvb, hvb_size, probe_size, "hvb"):
                continue
            if entry.et_sonden and not check_compatibility(entry.et_sonden, hvb_size, probe_size, "sonden"):
                continue
            if entry.kh_hvb and not check_compatibility(entry.kh_hvb, hvb_size, probe_size, "hvb"):
                continue
            
            # Check if formula already contains *2 (like line 2001167)
            has_multiply_2 = entry.menge_formel and "*2" in entry.menge_formel
            
            # If formula already has *2, use it as-is
            if has_multiply_2:
                add_entry(entry)
            else:
                # Override to sondenanzahl * 2 (for HVB and probes)
                quantity = calculate_formula("=sondenanzahl*2", context)
                if quantity and quantity > 0:
                    items.append({
                        "artikelnummer": format_artikelnummer(entry.artikelnummer),
                        "artikelbezeichnung": entry.artikelbezeichnung,
                        "menge": _decimal(quantity),
                        "source_table": "Kugelhahn",
                    })
            continue  # Skip other checks for Einlegeteil items
        
        # Special handling for Einschweißteil items based on business rules
        # Note: CSV structure is fixed by client, so we work with existing fields
        if is_einschweiss:
            # 1. GN Einschweißteil DA 63 mm (2001179)
            #    - Used ONLY for HVB
            #    - Only when HVB = 63mm (ET-HVB = DA 63)
            #    - Quantity = sondenanzahl (override static 1.0)
            #    - Already handled above for all Kugelhahn types when HVB = 63mm
            if article_da_size == "63":
                # Skip if already added in special case above (when HVB = 63mm)
                if hvb_size == "63":
                    continue
                # Otherwise, check ET-HVB compatibility (should be DA 63)
                if entry.et_hvb and check_compatibility(entry.et_hvb, hvb_size, probe_size, 'hvb'):
                    # Override static quantity to sondenanzahl
                    quantity = calculate_formula("=sondenanzahl", context)
                    if quantity and quantity > 0:
                        items.append({
                            "artikelnummer": format_artikelnummer(entry.artikelnummer),
                            "artikelbezeichnung": entry.artikelbezeichnung,
                            "menge": _decimal(quantity),
                            "source_table": "Kugelhahn",
                        })
                continue  # Skip other checks for DA 63 Einschweißteil
            
            # 2. GN Einschweißteil DA 40 mm (2001177)
            #    - Used ONLY for Sonden (probes)
            #    - NEVER for HVB (no ET-HVB field)
            #    - Used when probe = DA 40 or 50mm (ET-Sonden = DA 40|DA 50)
            #    - Quantity = sondenanzahl (already in formula)
            if article_da_size == "40":
                # Check ET-Sonden compatibility (should be DA 40|DA 50)
                # Only include if ET-Sonden matches (never for HVB)
                if entry.et_sonden and check_compatibility(entry.et_sonden, hvb_size, probe_size, 'sonden'):
                    add_entry(entry)
                continue  # Skip other checks for DA 40 Einschweißteil
            
            # 3. GN Einschweißteil DA 32 mm (2001178)
            #    - Used for BOTH HVB and Sonden
            #    - HVB: Used for every HVB which is NOT 63mm (KH-HVB field indicates HVB use)
            #    - Sonden: Used if probes are DA 32mm
            #    - Quantity = sondenanzahl (override formula =2)
            #    - Exception: If Kugelhahn DA size is 40 (e.g., DN 32 / DA 40), we do NOT need Sonden version
            #      This is future-proof: any Kugelhahn with DA 40 will skip DA 32 Einschweißteil (Sonden)
            #    Note: CSV has one row with both ET-Sonden and KH-HVB fields
            if article_da_size == "32":
                # Check if used for HVB: KH-HVB field exists (indicates HVB use) and HVB is NOT 63mm
                # Requirement: "always used for every HVB which is not 63 mm"
                if entry.kh_hvb and entry.kh_hvb.strip() and hvb_size != "63":
                    # Override quantity to sondenanzahl
                    quantity = calculate_formula("=sondenanzahl", context)
                    if quantity and quantity > 0:
                        items.append({
                            "artikelnummer": format_artikelnummer(entry.artikelnummer),
                            "artikelbezeichnung": entry.artikelbezeichnung + " (HVB)",
                            "menge": _decimal(quantity),
                            "source_table": "Kugelhahn",
                        })
                
                # Check if used for Sonden: probe is DA 32mm
                # Requirement: "always used if somebody selected probes with DA 32 mm"
                # Exception: "If this ball valve is selected, we do not need 'Sonden' (probes) in DA 32 mm"
                # Future-proof: Skip Sonden version if Kugelhahn DA size is 40 (works for DN 32 / DA 40 and future DA 40 types)
                kugelhahn_da = _extract_da_from_kugelhahn_type(kugelhahn_type)
                if probe_size == "32" and kugelhahn_da != "40":
                    # Override quantity to sondenanzahl
                    quantity = calculate_formula("=sondenanzahl", context)
                    if quantity and quantity > 0:
                        items.append({
                            "artikelnummer": format_artikelnummer(entry.artikelnummer),
                            "artikelbezeichnung": entry.artikelbezeichnung + " (Sonden)",
                            "menge": _decimal(quantity),
                            "source_table": "Kugelhahn",
                        })
                continue  # Skip other checks for DA 32 Einschweißteil
        
        # Smart detection for Heizdorn-Reduktion items
        # Rule: "The quantity is the same as number of probes" (sondenanzahl)
        # Example: If DN 32 / DA 40 and probe = 50mm, include Heizdorn-Reduktion DA 50 / 40
        is_heizdorn = "Heizdorn" in artikelbezeichnung or "Heizdorn-Reduktion" in artikelbezeichnung
        
        if is_heizdorn:
            # Check ET-Sonden compatibility (should match probe size)
            if entry.et_sonden and check_compatibility(entry.et_sonden, hvb_size, probe_size, 'sonden'):
                # Override to sondenanzahl (ignore static value)
                quantity = calculate_formula("=sondenanzahl", context)
                if quantity and quantity > 0:
                    items.append({
                        "artikelnummer": format_artikelnummer(entry.artikelnummer),
                        "artikelbezeichnung": entry.artikelbezeichnung,
                        "menge": _decimal(quantity),
                        "source_table": "Kugelhahn",
                    })
            continue  # Skip other checks for Heizdorn-Reduktion items
        
        # For non-Einschweißteil items, filter by DA size mismatch first
        if article_da_size and article_da_size != da_value:
            print(f"DEBUG: Entry {entry.artikelnummer} filtered out - DA size mismatch: article is DA {article_da_size}, expected DA {da_value}")
            continue
        
        # For non-Einschweißteil items, apply standard compatibility checks
        if entry.et_hvb and not check_compatibility(entry.et_hvb, hvb_size, probe_size, 'hvb'):
            continue
        if entry.et_sonden and not check_compatibility(entry.et_sonden, hvb_size, probe_size, 'sonden'):
            continue
        if entry.kh_hvb and not check_compatibility(entry.kh_hvb, hvb_size, probe_size, 'hvb'):
            continue
        
        add_entry(entry)

    return items


def build_dfm_kugelhahn_components(config, context) -> List[Dict]:
    """Build D-Kugelhahn components (Kugelhahn-Typ selected from DFM dropdown) - separate from regular Kugelhahn"""
    items: List[Dict] = []
    
    # Get the DFM Kugelhahn type (selected from DFM dropdown)
    dfm_kugelhahn_type = config.dfm_kugelhahn_type
    if not dfm_kugelhahn_type:
        return items

    # Dynamically extract DA size from D-Kugelhahn type name
    da_value = _extract_da_from_kugelhahn_type(dfm_kugelhahn_type)
    if not da_value:
        return items

    per_probe = _decimal(config.sondenanzahl)
    hvb_size = str(config.hvb_size)
    probe_size = str(config.sonden_durchmesser)

    def add_entry(entry):
        # Only use menge_formel, ignore menge_statisch as per client requirement
        if not entry.menge_formel:
            return  # Skip items without formula
        quantity = calculate_formula(entry.menge_formel, context)
        if quantity is None or quantity <= 0:
            return
        items.append(
            {
                "artikelnummer": format_artikelnummer(entry.artikelnummer),
                "artikelbezeichnung": entry.artikelbezeichnung,
                "menge": _decimal(quantity),
                "source_table": "D-Kugelhahn",  # Different source to distinguish from regular Kugelhahn
            }
        )

    # Special case: GN Einschweißteil DA 63 mm should be included
    # whenever HVB = 63mm, regardless of D-Kugelhahn type
    # Dynamically find any Einschweißteil with DA 63 that matches HVB = 63mm
    # Only add if regular Kugelhahn is not set (to avoid duplicate)
    if hvb_size == "63" and not config.kugelhahn_type:
        import re
        # Find all Einschweißteil items and check if they're DA 63
        all_einschweiss = Kugelhahn.objects.filter(
            artikelbezeichnung__icontains="Einschweißteil"
        )
        for entry in all_einschweiss:
            # Extract DA size from description (e.g., "DA 63 mm" -> "63")
            da_match = re.search(r'DA\s+(\d{2,3})\s*mm', entry.artikelbezeichnung or "", re.IGNORECASE)
            if da_match and da_match.group(1) == "63":
                # Check ET-HVB compatibility (should be DA 63)
                if entry.et_hvb and check_compatibility(entry.et_hvb, hvb_size, probe_size, 'hvb'):
                    quantity = calculate_formula("=sondenanzahl", context)
                    if quantity and quantity > 0:
                        items.append({
                            "artikelnummer": format_artikelnummer(entry.artikelnummer),
                            "artikelbezeichnung": entry.artikelbezeichnung,
                            "menge": _decimal(quantity),
                            "source_table": "D-Kugelhahn",
                        })
                        break  # Only add one DA 63 Einschweißteil
    
    entries = Kugelhahn.objects.filter(kugelhahn=dfm_kugelhahn_type)
    print(f"DEBUG build_dfm_kugelhahn_components: Found {entries.count()} entries for dfm_kugelhahn_type='{dfm_kugelhahn_type}'")
    for entry in entries:
        if not entry.artikelnummer:
            continue
        
        artikelbezeichnung = entry.artikelbezeichnung or ""
        is_einschweiss = "Einschweißteil" in artikelbezeichnung
        
        # Extract DA size from article description
        import re
        da_match = re.search(r'DA\s+(\d{2,3})\s*mm', artikelbezeichnung, re.IGNORECASE)
        article_da_size = None
        if da_match:
            article_da_size = da_match.group(1)
        
        # Smart detection for Einlegeteil items that need sondenanzahl * 2
        # Rule: "The quantity is number of probes times two (for HVB and probes)"
        # Detect items with "Einlegeteil" but not "ohne Einlegeteil"
        is_einlegeteil = "Einlegeteil" in artikelbezeichnung and "ohne Einlegeteil" not in artikelbezeichnung
        
        if is_einlegeteil:
            # IMPORTANT: Einlegeteil articles in the D-Kugelhahn context must also respect
            # HVB compatibility (and KH-HVB if present), same as other D-Kugelhahn items.
            if entry.et_hvb and not check_compatibility(entry.et_hvb, hvb_size, probe_size, "hvb"):
                print(f"DEBUG: D-Kugelhahn Einlegeteil {entry.artikelnummer} filtered out by et_hvb compatibility")
                continue
            if entry.kh_hvb and not check_compatibility(entry.kh_hvb, hvb_size, probe_size, "hvb"):
                print(f"DEBUG: D-Kugelhahn Einlegeteil {entry.artikelnummer} filtered out by kh_hvb compatibility")
                continue
            
            # Check if formula already contains *2 (like line 2001167)
            has_multiply_2 = entry.menge_formel and "*2" in entry.menge_formel
            
            # If formula already has *2, use it as-is
            if has_multiply_2:
                add_entry(entry)
            else:
                # Override to sondenanzahl * 2 (for HVB and probes)
                quantity = calculate_formula("=sondenanzahl*2", context)
                if quantity and quantity > 0:
                    items.append({
                        "artikelnummer": format_artikelnummer(entry.artikelnummer),
                        "artikelbezeichnung": entry.artikelbezeichnung,
                        "menge": _decimal(quantity),
                        "source_table": "D-Kugelhahn",
                    })
            continue  # Skip other checks for Einlegeteil items
        
        # Special handling for Einschweißteil items based on business rules (same as regular Kugelhahn)
        if is_einschweiss:
            # 1. GN Einschweißteil DA 63 mm (2001179)
            #    - Used ONLY for HVB
            #    - Only when HVB = 63mm (ET-HVB = DA 63)
            #    - Quantity = sondenanzahl (override static 1.0)
            #    - Already handled above for all D-Kugelhahn types when HVB = 63mm
            if article_da_size == "63":
                # Skip if already added in special case above (when HVB = 63mm)
                if hvb_size == "63":
                    continue
                # Otherwise, check ET-HVB compatibility (should be DA 63)
                if entry.et_hvb and check_compatibility(entry.et_hvb, hvb_size, probe_size, 'hvb'):
                    # Override static quantity to sondenanzahl
                    quantity = calculate_formula("=sondenanzahl", context)
                    if quantity and quantity > 0:
                        items.append({
                            "artikelnummer": format_artikelnummer(entry.artikelnummer),
                            "artikelbezeichnung": entry.artikelbezeichnung,
                            "menge": _decimal(quantity),
                            "source_table": "D-Kugelhahn",
                        })
                continue  # Skip other checks for DA 63 Einschweißteil
            
            # 2. GN Einschweißteil DA 40 mm (2001177)
            #    - Used ONLY for Sonden (probes)
            #    - NEVER for HVB (no ET-HVB field)
            #    - Used when probe = DA 40 or 50mm (ET-Sonden = DA 40|DA 50)
            #    - Quantity = sondenanzahl (already in formula)
            if article_da_size == "40":
                # Check ET-Sonden compatibility (should be DA 40|DA 50)
                # Only include if ET-Sonden matches (never for HVB)
                if entry.et_sonden and check_compatibility(entry.et_sonden, hvb_size, probe_size, 'sonden'):
                    add_entry(entry)
                continue  # Skip other checks for DA 40 Einschweißteil
            
            # 3. GN Einschweißteil DA 32 mm (2001178)
            #    - Used for BOTH HVB and Sonden
            #    - HVB: Used for every HVB which is NOT 63mm (KH-HVB field indicates HVB use)
            #    - Sonden: Used if probes are DA 32mm
            #    - Quantity = sondenanzahl (override formula =2)
            #    - Exception: If D-Kugelhahn DA size is 40 (e.g., DN 32 / DA 40), we do NOT need Sonden version
            #      This is future-proof: any D-Kugelhahn with DA 40 will skip DA 32 Einschweißteil (Sonden)
            if article_da_size == "32":
                # Check if used for HVB: KH-HVB field exists (indicates HVB use) and HVB is NOT 63mm
                # Requirement: "always used for every HVB which is not 63 mm"
                if entry.kh_hvb and entry.kh_hvb.strip() and hvb_size != "63":
                    # Override quantity to sondenanzahl
                    quantity = calculate_formula("=sondenanzahl", context)
                    if quantity and quantity > 0:
                        items.append({
                            "artikelnummer": format_artikelnummer(entry.artikelnummer),
                            "artikelbezeichnung": entry.artikelbezeichnung + " (HVB)",
                            "menge": _decimal(quantity),
                            "source_table": "D-Kugelhahn",
                        })
                
                # Check if used for Sonden: probe is DA 32mm
                # Requirement: "always used if somebody selected probes with DA 32 mm"
                # Exception: "If this ball valve is selected, we do not need 'Sonden' (probes) in DA 32 mm"
                # Future-proof: Skip Sonden version if D-Kugelhahn DA size is 40 (works for DN 32 / DA 40 and future DA 40 types)
                dfm_kugelhahn_da = _extract_da_from_kugelhahn_type(dfm_kugelhahn_type)
                if probe_size == "32" and dfm_kugelhahn_da != "40":
                    # Override quantity to sondenanzahl
                    quantity = calculate_formula("=sondenanzahl", context)
                    if quantity and quantity > 0:
                        items.append({
                            "artikelnummer": format_artikelnummer(entry.artikelnummer),
                            "artikelbezeichnung": entry.artikelbezeichnung + " (Sonden)",
                            "menge": _decimal(quantity),
                            "source_table": "D-Kugelhahn",
                        })
                continue  # Skip other checks for DA 32 Einschweißteil
        
        # Smart detection for Heizdorn-Reduktion items
        # Rule: "The quantity is the same as number of probes" (sondenanzahl)
        # Example: If DN 32 / DA 40 and probe = 50mm, include Heizdorn-Reduktion DA 50 / 40
        is_heizdorn = "Heizdorn" in artikelbezeichnung or "Heizdorn-Reduktion" in artikelbezeichnung
        
        if is_heizdorn:
            # Check ET-Sonden compatibility (should match probe size)
            if entry.et_sonden and check_compatibility(entry.et_sonden, hvb_size, probe_size, 'sonden'):
                # Override to sondenanzahl (ignore static value)
                quantity = calculate_formula("=sondenanzahl", context)
                if quantity and quantity > 0:
                    items.append({
                        "artikelnummer": format_artikelnummer(entry.artikelnummer),
                        "artikelbezeichnung": entry.artikelbezeichnung,
                        "menge": _decimal(quantity),
                        "source_table": "D-Kugelhahn",
                    })
            continue  # Skip other checks for Heizdorn-Reduktion items
        
        # For non-Einschweißteil items, filter by DA size mismatch first
        if article_da_size and article_da_size != da_value:
            print(f"DEBUG: Entry {entry.artikelnummer} filtered out - DA size mismatch: article is DA {article_da_size}, expected DA {da_value}")
            continue
        
        # For D-Kugelhahn items, we're more lenient with compatibility checks
        # since they're selected independently from DFM category
        # Only check HVB compatibility strictly, sonden compatibility is optional
        if entry.et_hvb and not check_compatibility(entry.et_hvb, hvb_size, probe_size, 'hvb'):
            print(f"DEBUG: Entry {entry.artikelnummer} filtered out by et_hvb compatibility")
            continue
        # Skip sonden compatibility check for D-Kugelhahn - user explicitly selected this type
        # if entry.et_sonden and not check_compatibility(entry.et_sonden, hvb_size, probe_size, 'sonden'):
        #     print(f"DEBUG: Entry {entry.artikelnummer} filtered out by et_sonden compatibility")
        #     continue
        if entry.kh_hvb and not check_compatibility(entry.kh_hvb, hvb_size, probe_size, 'hvb'):
            print(f"DEBUG: Entry {entry.artikelnummer} filtered out by kh_hvb compatibility")
            continue
        print(f"DEBUG: Adding D-Kugelhahn entry: {entry.artikelnummer} - {entry.artikelbezeichnung}")
        add_entry(entry)

    print(f"DEBUG build_dfm_kugelhahn_components: Returning {len(items)} items")
    return items


def build_hvb_stuetze_components(config, custom_quantities: dict = None) -> List[Dict]:
    """Build HVB Stütze (support) components - Oben and Unter articles for each HVB diameter
    CRITICAL: These "GN X - ZUB - Verteiler - Stütze" articles are ONLY for GN X chambers
    (GN X1, GN X2, GN X3, GN X4). They must NOT appear for regular GN chambers (GN 1, GN 2, etc.)
    
    Args:
        config: BOMConfiguration instance
        custom_quantities: Dictionary mapping artikelnummer to custom quantity (from Step 2)
    """
    items: List[Dict] = []
    
    if custom_quantities is None:
        custom_quantities = {}
    
    # CRITICAL FILTER: Only include for GN X chambers (chambers with "X" in the name)
    schachttyp = str(config.schachttyp or "").strip()
    if not schachttyp or "X" not in schachttyp.upper():
        # Not a GN X chamber - return empty list (no HVB Stütze for regular GN chambers)
        return items
    
    hvb_size = str(config.hvb_size).strip()
    
    if not hvb_size:
        return items
    
    # Remove 'mm' suffix if present
    if hvb_size.lower().endswith('mm'):
        hvb_size = hvb_size[:-2].strip()
    
    # Get both Oben and Unter articles for this HVB diameter
    # Only for GN X chambers (already filtered above)
    stuetze_articles = HVBStuetze.objects.filter(hvb_durchmesser=hvb_size)
    
    for stuetze in stuetze_articles:
        artikelnummer = format_artikelnummer(stuetze.artikelnummer)
        artikelnummer_key = str(stuetze.artikelnummer).replace('.0', '').strip()
        
        # Use custom quantity if provided, otherwise default to 1
        quantity = Decimal("1")
        if artikelnummer_key in custom_quantities:
            try:
                quantity = Decimal(str(custom_quantities[artikelnummer_key]))
                if quantity < 0:
                    quantity = Decimal("1")
            except (ValueError, TypeError):
                quantity = Decimal("1")
        
        items.append(
            {
                "artikelnummer": artikelnummer,
                "artikelbezeichnung": stuetze.artikelbezeichnung,
                "menge": quantity,
                "source_table": "HVB Stütze",
                "is_finalized": True,  # Mark as finalized - based on fixed HVB-Größe selection
            }
        )
    
    return items

