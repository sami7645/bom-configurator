from decimal import Decimal, InvalidOperation
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
    SondenDurchmesserPipe,
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
    """Sondenverschlusskappe (probe closure caps) - for probe pipe ends only.
    
    Business rules:
    - Probes: sondenanzahl * 2 pieces, selected by probe diameter (sonden_durchmesser)
    - Note: HVB closure caps are handled separately by build_stumpfschweiss_endkappen
    """
    items: List[Dict] = []
    
    sondenanzahl = context.get('sondenanzahl', 0) if context else 0
    if not sondenanzahl:
        sondenanzahl = config.sondenanzahl or 0
    
    # ============================================
    # Probe Sondenverschlusskappe (sondenanzahl * 2 pieces)
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
                    "artikelbezeichnung": probe_cap.artikelbezeichnung,
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
        
        # ET-Sonden compatibility check (probe diameter)
        # For most parts (e.g. Übergangsstutzen, Heizdorn-Reduktion, brass fittings),
        # ET-Sonden is a hard compatibility constraint and must match the selected
        # probe diameter.
        #
        # For GN Einschweißteil articles with explicit HVB compatibility (ET-HVB),
        # the DA value in ET-Sonden describes the branch size (e.g. DA 32) rather
        # than the probe diameter, so we rely on HVB compatibility instead and do
        # NOT filter by probe diameter here.
        enforce_sonden_compat = bool(entry.et_sonden)
        beschreibung = (entry.artikelbezeichnung or "").lower()
        if "einschweißteil" in beschreibung and entry.et_hvb:
            enforce_sonden_compat = False
        
        if enforce_sonden_compat and not check_compatibility(entry.et_sonden, config.hvb_size, config.sonden_durchmesser, 'sonden'):
            continue
        
        # DFM-HVB compatibility check (HVB size for brass flowmeters)
        # For brass flowmeters, dfm_hvb contains HVB sizes that are compatible
        # If dfm_hvb is empty but et_hvb contains HVB sizes (like "DA 63|DA 75|..."), use et_hvb for HVB check
        hvb_checked = False
        if entry.dfm_hvb:
            if not check_compatibility(entry.dfm_hvb, config.hvb_size, config.sonden_durchmesser, 'hvb'):
                continue
            hvb_checked = True
        elif entry.et_hvb:
            # For brass flowmeters, et_hvb may contain HVB compatibility list (e.g., "DA 63|DA 75|...")
            # Check if et_hvb contains pipe sizes (DA values) - if so, use it for HVB compatibility
            if 'DA' in entry.et_hvb and '|' in entry.et_hvb:
                # This looks like an HVB compatibility list, check it
                if not check_compatibility(entry.et_hvb, config.hvb_size, config.sonden_durchmesser, 'hvb'):
                    continue
                hvb_checked = True
        
        # ET-HVB compatibility check (for Entlüftung components) - only if not already checked above
        # Skip this check if we already used et_hvb for HVB compatibility above
        if not hvb_checked and entry.et_hvb and not ('DA' in entry.et_hvb and '|' in entry.et_hvb):
            if not check_compatibility(entry.et_hvb, config.hvb_size, config.sonden_durchmesser, 'hvb'):
                continue

        # Calculate quantity: use formula if available, otherwise static value
        quantity = None
        if entry.menge_formel:
            # Prioritize Menge Formel if it exists
            quantity = calculate_formula(entry.menge_formel, context)
        elif entry.menge_statisch:
            # If Menge Formel is empty, check Menge Statisch
            # Menge Statisch might be a decimal value or a formula string
            if isinstance(entry.menge_statisch, Decimal):
                # It's a static decimal value
                quantity = entry.menge_statisch
            else:
                # It might be a formula string (e.g., "=sondenanzahl (for all HVB diameteres)")
                menge_statisch_str = str(entry.menge_statisch).strip()
                if menge_statisch_str.startswith('=') or any(keyword in menge_statisch_str.lower() for keyword in ['sondenanzahl', 'sondenabstand', 'zuschlag']):
                    # It's a formula, try to calculate it
                    quantity = calculate_formula(menge_statisch_str, context)
                else:
                    # Try to parse as decimal
                    try:
                        quantity = Decimal(str(entry.menge_statisch).replace(',', '.'))
                    except (ValueError, InvalidOperation):
                        quantity = None
        
        # If still no quantity, check if same article exists in Kugelhahn with a formula
        if quantity is None:
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
    """
    Build Kugelhahn components **directly** from CSV rules.

    Philosophy:
    - Trust the CSV completely (Kugelhaehne.csv):
      - Menge Formel / Menge Statisch define the quantity.
      - ET-HVB, ET-Sonden, KH-HVB define compatibility.
    - Avoid hard-coded "special cases" for specific article numbers.
    - Only add light, generic logic:
      - Match DA size of non-Einschweißteil articles to the selected Kugelhahn DA.
    """
    items: List[Dict] = []

    # If no Kugelhahn selected but DFM is plastic, use DN 25 / DA 32 rules
    kugelhahn_type = config.kugelhahn_type
    if not kugelhahn_type and config.dfm_type and config.dfm_type.startswith('K-DFM'):
        kugelhahn_type = "DN 25 / DA 32"  # Default for plastic DFM

    if not kugelhahn_type:
        return items

    # Dynamically extract DA size from Kugelhahn type name (for non-Einschweißteil rows)
    da_value = _extract_da_from_kugelhahn_type(kugelhahn_type)

    hvb_size = str(config.hvb_size)
    probe_size = str(config.sonden_durchmesser)

    entries = Kugelhahn.objects.filter(kugelhahn=kugelhahn_type)
    for entry in entries:
        if not entry.artikelnummer:
            continue

        artikelbezeichnung = entry.artikelbezeichnung or ""
        is_einschweiss = "Einschweißteil" in artikelbezeichnung

        # Extract DA size from description (e.g., "DA 63 mm" -> "63")
        import re
        da_match = re.search(r"DA\s+(\d{2,3})\s*mm", artikelbezeichnung, re.IGNORECASE)
        article_da_size = da_match.group(1) if da_match else None

        # Generic DA filter ONLY for non-Einschweißteil items:
        # data already encodes which DA belongs to which Kugelhahn.
        if not is_einschweiss and da_value and article_da_size and article_da_size != da_value:
            continue

        # Generic compatibility checks based on CSV columns
        if entry.et_hvb and not check_compatibility(entry.et_hvb, hvb_size, probe_size, 'hvb'):
            continue
        if entry.et_sonden and not check_compatibility(entry.et_sonden, hvb_size, probe_size, 'sonden'):
            continue
        if entry.kh_hvb and not check_compatibility(entry.kh_hvb, hvb_size, probe_size, 'hvb'):
            continue

        # Quantity: prefer Formel, fall back to statisch
        quantity = None
        if entry.menge_formel:
            quantity = calculate_formula(entry.menge_formel, context)
        elif entry.menge_statisch is not None:
            quantity = entry.menge_statisch

        if quantity is None or quantity <= 0:
            continue

        items.append(
            {
                "artikelnummer": format_artikelnummer(entry.artikelnummer),
                "artikelbezeichnung": artikelbezeichnung,
                "menge": _decimal(quantity),
                "source_table": "Kugelhahn",
            }
        )

    return items


def build_dfm_kugelhahn_components(config, context) -> List[Dict]:
    """Build D-Kugelhahn components (Kugelhahn-Typ selected from DFM dropdown)
    purely based on CSV rules (Kugelhaehne.csv).

    We mirror the logic from build_kugelhahn_components but label the
    source_table as \"D-Kugelhahn\".
    """
    items: List[Dict] = []

    dfm_kugelhahn_type = config.dfm_kugelhahn_type
    if not dfm_kugelhahn_type:
        return items

    da_value = _extract_da_from_kugelhahn_type(dfm_kugelhahn_type)
    hvb_size = str(config.hvb_size)
    probe_size = str(config.sonden_durchmesser)

    entries = Kugelhahn.objects.filter(kugelhahn=dfm_kugelhahn_type)
    for entry in entries:
        if not entry.artikelnummer:
            continue

        artikelbezeichnung = entry.artikelbezeichnung or ""
        is_einschweiss = "Einschweißteil" in artikelbezeichnung

        import re
        da_match = re.search(r"DA\s+(\d{2,3})\s*mm", artikelbezeichnung, re.IGNORECASE)
        article_da_size = da_match.group(1) if da_match else None

        # Generic DA filter ONLY for non-Einschweißteil items
        if not is_einschweiss and da_value and article_da_size and article_da_size != da_value:
            continue

        # Respect CSV compatibility fields
        if entry.et_hvb and not check_compatibility(entry.et_hvb, hvb_size, probe_size, "hvb"):
            continue
        if entry.et_sonden and not check_compatibility(entry.et_sonden, hvb_size, probe_size, "sonden"):
            continue
        if entry.kh_hvb and not check_compatibility(entry.kh_hvb, hvb_size, probe_size, "hvb"):
            continue

        quantity = None
        if entry.menge_formel:
            quantity = calculate_formula(entry.menge_formel, context)
        elif entry.menge_statisch is not None:
            quantity = entry.menge_statisch

        if quantity is None or quantity <= 0:
            continue

        items.append(
            {
                "artikelnummer": format_artikelnummer(entry.artikelnummer),
                "artikelbezeichnung": artikelbezeichnung,
                "menge": _decimal(quantity),
                "source_table": "D-Kugelhahn",
            }
        )

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

