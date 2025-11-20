import json
import re
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from .models import (
    Schacht, HVB, Sondengroesse, Sondenabstand, Kugelhahn, DFM,
    BOMConfiguration, BOMItem, GNXChamberArticle, GNXChamberConfiguration
)


def index(request):
    """Main configurator page"""
    context = {
        'schacht_types': Schacht.objects.all().order_by('schachttyp'),
        'hvb_sizes': HVB.objects.all().order_by('hauptverteilerbalken'),
        'recent_configurations': BOMConfiguration.objects.all().order_by('-created_at')[:5]
    }
    return render(request, 'configurator/index.html', context)


def configurator(request):
    """BOM Configurator main interface"""
    from django.db.models import Case, When, IntegerField
    
    # Custom order for Schachttyp
    schacht_order = Case(
        When(schachttyp='Verteiler', then=1),
        When(schachttyp='GN X1', then=2),
        When(schachttyp='GN X2', then=3),
        When(schachttyp='GN X3', then=4),
        When(schachttyp='GN X4', then=5),
        When(schachttyp='GN 2', then=6),
        When(schachttyp='GN 1', then=7),
        When(schachttyp='GN R Medium', then=8),
        When(schachttyp='GN R Kompakt', then=9),
        When(schachttyp='GN R Mini', then=10),
        When(schachttyp='GN R Nano', then=11),
        default=99,
        output_field=IntegerField()
    )
    
    # Sort HVB sizes numerically (convert to int for proper sorting)
    hvb_sizes = sorted(
        HVB.objects.all(),
        key=lambda x: int(x.hauptverteilerbalken) if x.hauptverteilerbalken.isdigit() else 9999
    )
    
    # Get DFM types and separate Brass/Plastic categories
    # Exclude category headers that shouldn't be selectable
    exclude_categories = ['Brass Flowmeters', 'Plastic Flowmeters']
    all_dfm_types = DFM.objects.exclude(
        durchflussarmatur__in=exclude_categories
    ).values('durchflussarmatur').distinct().order_by('durchflussarmatur')
    
    dfm_types = []
    brass_flowmeters = []
    plastic_flowmeters = []
    
    for dfm in all_dfm_types:
        name = dfm['durchflussarmatur']
        # Categorize based on known patterns
        if (name.startswith('HC VTR') or 
            name.startswith('IMI STAD') or 
            name.startswith('IMI TA') or 
            name.startswith('K-DFM')):
            brass_flowmeters.append(name)
        elif name.startswith('Plastic') and name != 'Plastic Flowmeters':
            plastic_flowmeters.append(name)
        else:
            dfm_types.append(name)
    
    context = {
        'schacht_types': Schacht.objects.all().order_by(schacht_order),
        'hvb_sizes': hvb_sizes,
        'sondenabstaende': Sondenabstand.objects.all().order_by('sondenabstand'),
        'kugelhahn_types': Kugelhahn.objects.values('kugelhahn').distinct().order_by('kugelhahn'),
        'dfm_types': dfm_types,
        'brass_flowmeters': sorted(brass_flowmeters),
        'plastic_flowmeters': sorted(plastic_flowmeters),
    }
    return render(request, 'configurator/configurator.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def get_sonden_options(request):
    """Get probe options based on selected shaft type and HVB"""
    try:
        data = json.loads(request.body)
        raw_schachttyp = data.get('schachttyp', '') or ''
        raw_hvb_size = data.get('hvb_size', '') or ''

        # Normalize inputs defensively (handles autofill and formatting differences)
        schachttyp = " ".join(str(raw_schachttyp).strip().split())  # collapse inner whitespace
        hvb_size = str(raw_hvb_size).strip()
        # Remove 'mm' suffix if present, but keep the number
        if hvb_size.lower().endswith('mm'):
            hvb_size = hvb_size[:-2].strip()
        
        # Debug logging
        print(f"DEBUG: Received request - schachttyp: '{schachttyp}', hvb_size: '{hvb_size}'")
        print(f"DEBUG: schachttyp type: {type(schachttyp)}, hvb_size type: {type(hvb_size)}")
        print(f"DEBUG: schachttyp repr: {repr(schachttyp)}, hvb_size repr: {repr(hvb_size)}")
        
        # Check if values are None or empty
        if not schachttyp or not hvb_size:
            print(f"DEBUG: Missing values - schachttyp: '{schachttyp}', hvb_size: '{hvb_size}'")
            return JsonResponse({
                'sonden_options': [],
                'error': 'Missing schachttyp or hvb_size',
                'received': {'schachttyp': schachttyp, 'hvb_size': hvb_size}
            })
        
        # First, try exact match (schachttyp + HVB) - this is the original behavior
        sonden_options = Sondengroesse.objects.filter(
            schachttyp__iexact=schachttyp,
            hvb__iexact=hvb_size
        )
        
        print(f"DEBUG: Query filter - schachttyp='{schachttyp}', hvb='{hvb_size}'")
        print(f"DEBUG: Found {sonden_options.count()} probes with exact match")
        
        # If we have exact matches, also check for additional diameters available for this schachttyp
        # This ensures all available diameters are shown even if not all HVB combinations exist
        if sonden_options.count() > 0:
            # Get all unique diameters for this schachttyp
            all_diameters_for_schachttyp = list(Sondengroesse.objects.filter(
                schachttyp__iexact=schachttyp
            ).values_list('durchmesser_sonde', flat=True).distinct())
            
            # Get diameters we already have from exact match
            existing_diameters = set(sonden_options.values_list('durchmesser_sonde', flat=True).distinct())
            all_diameters = set(all_diameters_for_schachttyp)
            
            # Find missing diameters
            missing_diameters = all_diameters - existing_diameters
            
            if missing_diameters:
                print(f"DEBUG: Found {len(existing_diameters)} diameters in exact match, but {len(all_diameters)} available for schachttyp")
                print(f"DEBUG: Missing diameters: {missing_diameters}")
                
                # Get IDs of existing probes
                existing_ids = list(sonden_options.values_list('id', flat=True))
                
                # For each missing diameter, get best available entry
                for missing_diam in missing_diameters:
                    # Try to find same HVB first
                    missing_probe = Sondengroesse.objects.filter(
                        schachttyp__iexact=schachttyp,
                        hvb__iexact=hvb_size,
                        durchmesser_sonde=missing_diam
                    ).first()
                    
                    # If not found, get any entry for this schachttyp and diameter
                    if not missing_probe:
                        missing_probe = Sondengroesse.objects.filter(
                            schachttyp__iexact=schachttyp,
                            durchmesser_sonde=missing_diam
                        ).first()
                    
                    if missing_probe:
                        existing_ids.append(missing_probe.id)
                        print(f"DEBUG: Added missing diameter {missing_diam}mm from HVB {missing_probe.hvb}")
                
                # Get all probes by IDs
                sonden_options = Sondengroesse.objects.filter(id__in=existing_ids)
        
        print(f"DEBUG: Total probes found: {sonden_options.count()}")
        
        # If still no results, show debug info
        if sonden_options.count() == 0:
            print(f"DEBUG: No probes found for schachttyp '{schachttyp}'")
            # Show what schachttyp values exist
            all_schacht = Sondengroesse.objects.values_list('schachttyp', flat=True).distinct()
            print(f"DEBUG: Available schachttyp values: {list(all_schacht)}")
            
            # Show what hvb values exist
            all_hvb = Sondengroesse.objects.values_list('hvb', flat=True).distinct()
            print(f"DEBUG: Available hvb values: {list(all_hvb)}")
        
        # Get the values and sort numerically by diameter
        options_list = sonden_options.values(
            'durchmesser_sonde', 'sondenanzahl_min', 'sondenanzahl_max',
            'artikelnummer', 'artikelbezeichnung'
        ).distinct()
        
        # Convert to list and sort numerically by durchmesser_sonde
        options_list = list(options_list)
        options_list = sorted(
            options_list,
            key=lambda x: int(x['durchmesser_sonde']) if x['durchmesser_sonde'].isdigit() else 9999
        )
        print(f"DEBUG: Returning {len(options_list)} options")
        
        response_payload = {
            'sonden_options': options_list,
            'debug': {
                'received': {'schachttyp': schachttyp, 'hvb_size': hvb_size},
                'count': len(options_list)
            }
        }
        return JsonResponse(response_payload)
    
    except Exception as e:
        print(f"DEBUG: Exception in get_sonden_options: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'sonden_options': [],
            'error': str(e)
        })


@csrf_exempt
@require_http_methods(["POST"])
def get_sondenabstand_options(request):
    """Get probe distance options"""
    data = json.loads(request.body)
    anschlussart = data.get('anschlussart', 'einseitig')
    
    abstand_options = Sondenabstand.objects.filter(
        anschlussart=anschlussart
    ).values(
        'sondenabstand', 'zuschlag_links', 'zuschlag_rechts', 'hinweis'
    ).order_by('sondenabstand')
    
    return JsonResponse({
        'abstand_options': list(abstand_options)
    })


@csrf_exempt
@require_http_methods(["POST"])
def check_existing_configuration(request):
    """Check if configuration already exists"""
    data = json.loads(request.body)
    
    # Extract configuration parameters
    schachttyp = data.get('schachttyp')
    hvb_size = data.get('hvb_size')
    sonden_durchmesser = data.get('sonden_durchmesser')
    sondenanzahl = data.get('sondenanzahl')
    sondenabstand = data.get('sondenabstand')
    anschlussart = data.get('anschlussart')
    
    # Check for exact configuration match
    existing_config = BOMConfiguration.objects.filter(
        schachttyp=schachttyp,
        hvb_size=hvb_size,
        sonden_durchmesser=sonden_durchmesser,
        sondenanzahl=sondenanzahl,
        sondenabstand=sondenabstand,
        anschlussart=anschlussart
    ).first()
    
    if existing_config:
        return JsonResponse({
            'exists': True,
            'type': 'full_configuration',
            'article_number': existing_config.full_article_number,
            'configuration_id': existing_config.id,
            'message': f'Diese Konfiguration existiert bereits mit Artikelnummer: {existing_config.full_article_number}'
        })
    
    # Check for mother article (same base config, different details)
    mother_config = BOMConfiguration.objects.filter(
        schachttyp=schachttyp,
        hvb_size=hvb_size,
        sonden_durchmesser=sonden_durchmesser
    ).first()
    
    if mother_config and mother_config.mother_article_number:
        # Generate next child number
        existing_children = BOMConfiguration.objects.filter(
            mother_article_number=mother_config.mother_article_number
        ).count()
        next_child_number = f"{mother_config.mother_article_number}-{existing_children + 1:03d}"
        
        return JsonResponse({
            'exists': True,
            'type': 'mother_article',
            'mother_article_number': mother_config.mother_article_number,
            'suggested_child_number': next_child_number,
            'message': f'Mutterartikel existiert: {mother_config.mother_article_number}. Vorgeschlagene Kindnummer: {next_child_number}'
        })
    
    return JsonResponse({
        'exists': False,
        'type': 'new_configuration',
        'message': 'Neue Konfiguration - Artikelnummer muss erstellt werden'
    })


@csrf_exempt
@require_http_methods(["POST"])
def get_gnx_chamber_articles(request):
    """Get GN X chamber articles based on HVB size"""
    data = json.loads(request.body)
    hvb_size = int(data.get('hvb_size', 0))
    
    articles = GNXChamberArticle.objects.filter(
        hvb_size_min__lte=hvb_size,
        hvb_size_max__gte=hvb_size
    ).values('id', 'artikelnummer', 'artikelbezeichnung', 'is_automatic')
    
    return JsonResponse({
        'articles': list(articles)
    })


def check_compatibility(compatibility_field, hvb_size, sonden_durchmesser, check_type='either'):
    """
    Check if an item is compatible with the selected HVB size and sonden diameter.
    Compatibility field format: "DA 63|DA 75|DA 90" or "DA 32|DA 40"
    
    Args:
        compatibility_field: The compatibility string from CSV
        hvb_size: Selected HVB size (e.g., "63")
        sonden_durchmesser: Selected sonden diameter (e.g., "32")
        check_type: 'either' (default) or 'hvb' or 'sonden'
    """
    if not compatibility_field or not compatibility_field.strip():
        return True  # No compatibility restriction means it's compatible
    
    # Format HVB size as "DA XX" (e.g., "63" -> "DA 63")
    hvb_formatted = f"DA {hvb_size}"
    
    # Format sonden diameter as "DA XX" (e.g., "32" -> "DA 32")
    sonden_formatted = f"DA {sonden_durchmesser}"
    
    # Parse compatible values
    compatible_values = [v.strip() for v in compatibility_field.split('|')]
    
    # Check based on type
    if check_type == 'hvb':
        return hvb_formatted in compatible_values
    elif check_type == 'sonden':
        return sonden_formatted in compatible_values
    else:  # 'either' - default
        return hvb_formatted in compatible_values or sonden_formatted in compatible_values


def calculate_formula(formula, context):
    """Safely calculate formula with given context"""
    if not formula or formula.strip() == '':
        return None
    
    try:
        # Remove Excel = prefix if present
        safe_formula = formula.strip()
        if safe_formula.startswith('='):
            safe_formula = safe_formula[1:]
        
        # Replace variables in formula - sort by length (longest first) to avoid partial replacements
        # e.g., replace 'sondenanzahl_min' before 'sondenanzahl'
        sorted_keys = sorted(context.keys(), key=len, reverse=True)
        for key in sorted_keys:
            value = context[key]
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(key) + r'\b'
            safe_formula = re.sub(pattern, str(value), safe_formula)
        
        # Only allow basic mathematical operations
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in safe_formula):
            return None
        
        # Evaluate the formula
        result = eval(safe_formula)
        return Decimal(str(result))
    except Exception as e:
        print(f"Formula calculation error: {e}")
        return None


@csrf_exempt
@require_http_methods(["POST"])
def generate_bom(request):
    """Generate BOM based on configuration"""
    data = json.loads(request.body)
    
    try:
        # Create BOM configuration
        config = BOMConfiguration.objects.create(
            name=data.get('configuration_name', 'Neue Konfiguration'),
            schachttyp=data.get('schachttyp'),
            hvb_size=data.get('hvb_size'),
            sonden_durchmesser=data.get('sonden_durchmesser'),
            sondenanzahl=int(data.get('sondenanzahl', 0)),
            sondenabstand=int(data.get('sondenabstand', 0)),
            anschlussart=data.get('anschlussart'),
            kugelhahn_type=data.get('kugelhahn_type', ''),
            dfm_type=data.get('dfm_type', ''),
            mother_article_number=data.get('mother_article_number', ''),
            child_article_number=data.get('child_article_number', ''),
            full_article_number=data.get('full_article_number', ''),
            zuschlag_links=int(data.get('zuschlag_links', 100)),
            zuschlag_rechts=int(data.get('zuschlag_rechts', 100))
        )
        
        # Calculate context for formulas
        calc_context = config.calculate_quantities()
        
        bom_items = []
        
        # Add Schacht item
        schacht = Schacht.objects.filter(schachttyp=config.schachttyp).first()
        if schacht and schacht.artikelnummer:
            quantity = schacht.menge_statisch or Decimal('1')
            if schacht.menge_formel:
                calculated = calculate_formula(schacht.menge_formel, calc_context)
                if calculated is not None:
                    quantity = calculated
            
            bom_item = BOMItem.objects.create(
                configuration=config,
                artikelnummer=schacht.artikelnummer,
                artikelbezeichnung=schacht.artikelbezeichnung,
                menge=quantity,
                source_table='Schacht'
            )
            bom_items.append(bom_item)
        
        # Add HVB item
        hvb = HVB.objects.filter(hauptverteilerbalken=config.hvb_size).first()
        if hvb:
            quantity = hvb.menge_statisch or Decimal('1')
            calculated = None
            if hvb.menge_formel:
                calculated = calculate_formula(hvb.menge_formel, calc_context)
                if calculated is not None:
                    # Formula calculates in mm, convert to meters for quantity
                    quantity = calculated / Decimal('1000')  # Convert mm to meters
            
            # Format description with length in meters
            if hvb.menge_formel and calculated is not None:
                artikelbezeichnung = f"{hvb.artikelbezeichnung} ({calculated:.0f}mm / {quantity:.3f}m)"
            else:
                artikelbezeichnung = hvb.artikelbezeichnung
            
            bom_item = BOMItem.objects.create(
                configuration=config,
                artikelnummer=hvb.artikelnummer,
                artikelbezeichnung=artikelbezeichnung,
                menge=quantity,
                calculated_quantity=calculated if hvb.menge_formel else None,
                source_table='HVB'
            )
            bom_items.append(bom_item)
        
        # Add Sonden items
        sonden = Sondengroesse.objects.filter(
            durchmesser_sonde=config.sonden_durchmesser,
            schachttyp=config.schachttyp,
            hvb=config.hvb_size
        )
        
        for sonde in sonden:
            if sonde.artikelnummer:
                # Calculate quantities based on Vorlauf/Rücklauf
                # These are per-sonde lengths, so multiply by sondenanzahl
                vorlauf_qty = sonde.vorlauf_laenge or Decimal('0')
                ruecklauf_qty = sonde.ruecklauf_laenge or Decimal('0')
                
                if sonde.vorlauf_formel:
                    calculated = calculate_formula(sonde.vorlauf_formel, calc_context)
                    if calculated is not None:
                        vorlauf_qty = calculated
                
                if sonde.ruecklauf_formel:
                    calculated = calculate_formula(sonde.ruecklauf_formel, calc_context)
                    if calculated is not None:
                        ruecklauf_qty = calculated
                
                # Multiply by sondenanzahl to get total length for all sonden
                total_qty = (vorlauf_qty + ruecklauf_qty) * Decimal(str(config.sondenanzahl))
                
                if total_qty > 0:
                    bom_item = BOMItem.objects.create(
                        configuration=config,
                        artikelnummer=sonde.artikelnummer,
                        artikelbezeichnung=sonde.artikelbezeichnung,
                        menge=total_qty,
                        source_table='Sondengroesse'
                    )
                    bom_items.append(bom_item)
        
        # Add Kugelhahn items if selected
        if config.kugelhahn_type:
            kugelhaehne = Kugelhahn.objects.filter(kugelhahn=config.kugelhahn_type)
            for kugelhahn in kugelhaehne:
                if kugelhahn.artikelnummer:
                    # Check compatibility
                    is_compatible = True
                    
                    # Check ET-HVB compatibility (if specified) - must match HVB
                    if kugelhahn.et_hvb:
                        is_compatible = check_compatibility(
                            kugelhahn.et_hvb, 
                            config.hvb_size, 
                            config.sonden_durchmesser,
                            check_type='hvb'
                        )
                    
                    # Check ET-Sonden compatibility (if specified) - must match sonden
                    if is_compatible and kugelhahn.et_sonden:
                        is_compatible = check_compatibility(
                            kugelhahn.et_sonden, 
                            config.hvb_size, 
                            config.sonden_durchmesser,
                            check_type='sonden'
                        )
                    
                    # Check KH-HVB compatibility (if specified) - must match HVB
                    if is_compatible and kugelhahn.kh_hvb:
                        is_compatible = check_compatibility(
                            kugelhahn.kh_hvb, 
                            config.hvb_size, 
                            config.sonden_durchmesser,
                            check_type='hvb'
                        )
                    
                    # Only add if compatible
                    if is_compatible:
                        quantity = kugelhahn.menge_statisch or Decimal('1')
                        if kugelhahn.menge_formel:
                            calculated = calculate_formula(kugelhahn.menge_formel, calc_context)
                            if calculated is not None:
                                quantity = calculated
                        
                        bom_item = BOMItem.objects.create(
                            configuration=config,
                            artikelnummer=kugelhahn.artikelnummer,
                            artikelbezeichnung=kugelhahn.artikelbezeichnung,
                            menge=quantity,
                            source_table='Kugelhahn'
                        )
                        bom_items.append(bom_item)
        
        # Add DFM items if selected
        if config.dfm_type:
            dfms = DFM.objects.filter(durchflussarmatur=config.dfm_type)
            for dfm in dfms:
                if dfm.artikelnummer:
                    # Check compatibility
                    is_compatible = True
                    
                    # Check ET-HVB compatibility (if specified) - must match HVB
                    if dfm.et_hvb:
                        is_compatible = check_compatibility(
                            dfm.et_hvb, 
                            config.hvb_size, 
                            config.sonden_durchmesser,
                            check_type='hvb'
                        )
                    
                    # Check ET-Sonden compatibility (if specified) - must match sonden
                    if is_compatible and dfm.et_sonden:
                        is_compatible = check_compatibility(
                            dfm.et_sonden, 
                            config.hvb_size, 
                            config.sonden_durchmesser,
                            check_type='sonden'
                        )
                    
                    # Check DFM-HVB compatibility (if specified) - must match HVB
                    if is_compatible and dfm.dfm_hvb:
                        is_compatible = check_compatibility(
                            dfm.dfm_hvb, 
                            config.hvb_size, 
                            config.sonden_durchmesser,
                            check_type='hvb'
                        )
                    
                    # Only add if compatible
                    if is_compatible:
                        quantity = dfm.menge_statisch or Decimal('1')
                        if dfm.menge_formel:
                            calculated = calculate_formula(dfm.menge_formel, calc_context)
                            if calculated is not None:
                                quantity = calculated
                        
                        bom_item = BOMItem.objects.create(
                            configuration=config,
                            artikelnummer=dfm.artikelnummer,
                            artikelbezeichnung=dfm.artikelbezeichnung,
                            menge=quantity,
                            source_table='DFM'
                        )
                        bom_items.append(bom_item)
        
        # Handle GN X chamber articles if applicable
        if config.schachttyp in ['GN X1', 'GN X2', 'GN X3', 'GN X4']:
            gnx_articles_data = data.get('gnx_articles', [])
            for article_data in gnx_articles_data:
                article_id = article_data.get('id')
                custom_quantity = Decimal(str(article_data.get('quantity', 1)))
                
                gnx_article = GNXChamberArticle.objects.get(id=article_id)
                
                # Create GN X chamber configuration
                GNXChamberConfiguration.objects.create(
                    bom_configuration=config,
                    gnx_article=gnx_article,
                    custom_quantity=custom_quantity
                )
                
                # Add to BOM items
                bom_item = BOMItem.objects.create(
                    configuration=config,
                    artikelnummer=gnx_article.artikelnummer,
                    artikelbezeichnung=gnx_article.artikelbezeichnung,
                    menge=custom_quantity,
                    source_table='GNXChamberArticle'
                )
                bom_items.append(bom_item)
        
        # Prepare response data
        bom_data = []
        for item in bom_items:
            bom_data.append({
                'artikelnummer': item.artikelnummer,
                'artikelbezeichnung': item.artikelbezeichnung,
                'menge': str(item.menge),
                'source': item.source_table
            })
        
        return JsonResponse({
            'success': True,
            'configuration_id': config.id,
            'bom_items': bom_data,
            'article_number': config.full_article_number or config.generate_article_number(),
            'message': 'BOM erfolgreich generiert'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Fehler beim Generieren der BOM'
        })


def view_configuration(request, config_id):
    """View a specific BOM configuration"""
    config = get_object_or_404(BOMConfiguration, id=config_id)
    bom_items = config.items.all().order_by('artikelnummer')
    gnx_configurations = config.gnxchamberconfiguration_set.all()
    
    context = {
        'configuration': config,
        'bom_items': bom_items,
        'gnx_configurations': gnx_configurations,
    }
    return render(request, 'configurator/view_configuration.html', context)


def configuration_list(request):
    """List all BOM configurations"""
    configurations = BOMConfiguration.objects.all().order_by('-created_at')
    
    context = {
        'configurations': configurations,
    }
    return render(request, 'configurator/configuration_list.html', context)


def delete_configuration(request, config_id):
    """Delete a BOM configuration"""
    config = get_object_or_404(BOMConfiguration, id=config_id)
    
    if request.method == 'POST':
        config.delete()
        messages.success(request, f'Konfiguration "{config.name}" wurde erfolgreich gelöscht.')
        return redirect('configuration_list')
    
    context = {
        'configuration': config,
    }
    return render(request, 'configurator/delete_configuration.html', context)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def update_probes_endpoint(request):
    """Manual endpoint to update probe combinations"""
    try:
        # Import here to avoid circular imports
        from configurator.models import Sondengroesse, Schacht, HVB
        from decimal import Decimal
        
        # Comprehensive probe data for all combinations
        additional_probes = [
            # GN X1 combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN X1', 'hvb_size': '63', 'sondenanzahl_min': 5, 'sondenanzahl_max': 20, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X1', 'hvb_size': '75', 'sondenanzahl_min': 5, 'sondenanzahl_max': 25, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '50', 'artikelnummer': '2000490', 'artikelbezeichnung': 'Rohr - PE 100-RC - 50', 'schachttyp': 'GN X1', 'hvb_size': '90', 'sondenanzahl_min': 5, 'sondenanzahl_max': 30, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            
            # GN X3 combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN X3', 'hvb_size': '110', 'sondenanzahl_min': 10, 'sondenanzahl_max': 50, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X3', 'hvb_size': '125', 'sondenanzahl_min': 10, 'sondenanzahl_max': 60, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '50', 'artikelnummer': '2000490', 'artikelbezeichnung': 'Rohr - PE 100-RC - 50', 'schachttyp': 'GN X3', 'hvb_size': '140', 'sondenanzahl_min': 10, 'sondenanzahl_max': 70, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            
            # GN X4 combinations
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN X4', 'hvb_size': '160', 'sondenanzahl_min': 15, 'sondenanzahl_max': 80, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '50', 'artikelnummer': '2000490', 'artikelbezeichnung': 'Rohr - PE 100-RC - 50', 'schachttyp': 'GN X4', 'hvb_size': '180', 'sondenanzahl_min': 15, 'sondenanzahl_max': 100, 'vorlauf_laenge': Decimal('0.280'), 'ruecklauf_laenge': Decimal('0.365')},
            
            # GN 2 combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN 2', 'hvb_size': '63', 'sondenanzahl_min': 5, 'sondenanzahl_max': 15, 'vorlauf_laenge': Decimal('0.265'), 'ruecklauf_laenge': Decimal('0.365')},
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN 2', 'hvb_size': '75', 'sondenanzahl_min': 5, 'sondenanzahl_max': 20, 'vorlauf_laenge': Decimal('0.265'), 'ruecklauf_laenge': Decimal('0.365')},
            
            # GN R Medium combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN R Medium', 'hvb_size': '63', 'sondenanzahl_min': 3, 'sondenanzahl_max': 8, 'vorlauf_laenge': Decimal('0.200'), 'ruecklauf_laenge': Decimal('0.300')},
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN R Medium', 'hvb_size': '75', 'sondenanzahl_min': 3, 'sondenanzahl_max': 10, 'vorlauf_laenge': Decimal('0.200'), 'ruecklauf_laenge': Decimal('0.300')},
            
            # GN R Mini combinations
            {'durchmesser_sonde': '32', 'artikelnummer': '2000488', 'artikelbezeichnung': 'Rohr - PE 100-RC - 32', 'schachttyp': 'GN R Mini', 'hvb_size': '63', 'sondenanzahl_min': 2, 'sondenanzahl_max': 5, 'vorlauf_laenge': Decimal('0.150'), 'ruecklauf_laenge': Decimal('0.250')},
            
            # More GN 1 combinations
            {'durchmesser_sonde': '40', 'artikelnummer': '2000489', 'artikelbezeichnung': 'Rohr - PE 100-RC - 40', 'schachttyp': 'GN 1', 'hvb_size': '75', 'sondenanzahl_min': 8, 'sondenanzahl_max': 15, 'vorlauf_laenge': Decimal('0.265'), 'ruecklauf_laenge': Decimal('0.365')},
        ]

        count = 0
        errors = []
        
        for probe_data in additional_probes:
            try:
                # Get the actual model objects
                schacht = Schacht.objects.filter(schachttyp=probe_data['schachttyp']).first()
                hvb = HVB.objects.filter(hauptverteilerbalken=probe_data['hvb_size']).first()
                
                if not schacht:
                    errors.append(f"Schachttyp '{probe_data['schachttyp']}' not found")
                    continue
                    
                if not hvb:
                    errors.append(f"HVB size '{probe_data['hvb_size']}' not found")
                    continue
                
                # Check if combination already exists
                existing = Sondengroesse.objects.filter(
                    durchmesser_sonde=probe_data['durchmesser_sonde'],
                    schachttyp=schacht,
                    hvb_size=hvb
                ).first()
                
                if not existing:
                    Sondengroesse.objects.create(
                        durchmesser_sonde=probe_data['durchmesser_sonde'],
                        artikelnummer=probe_data['artikelnummer'],
                        artikelbezeichnung=probe_data['artikelbezeichnung'],
                        schachttyp=schacht,
                        hvb_size=hvb,
                        bauform='',  # Default empty
                        sondenanzahl_min=probe_data['sondenanzahl_min'],
                        sondenanzahl_max=probe_data['sondenanzahl_max'],
                        vorlauf_laenge=probe_data['vorlauf_laenge'],
                        ruecklauf_laenge=probe_data['ruecklauf_laenge'],
                        vorlauf_formel='',  # Default empty
                        ruecklauf_formel='',  # Default empty
                        hinweis=''  # Default empty
                    )
                    count += 1
                    
            except Exception as e:
                errors.append(f"Error with {probe_data['schachttyp']} + {probe_data['hvb_size']}mm: {str(e)}")

        total_probes = Sondengroesse.objects.count()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully added {count} new probe combinations!',
            'total_probes': total_probes,
            'added_probes': count,
            'errors': errors if errors else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Failed to update probe combinations'
        })


@csrf_exempt
@require_http_methods(["GET"])
def debug_probes_endpoint(request):
    """Debug endpoint to check probe data in database"""
    try:
        from configurator.models import Sondengroesse, Schacht, HVB
        
        # Get counts
        total_probes = Sondengroesse.objects.count()
        total_schacht = Schacht.objects.count()
        total_hvb = HVB.objects.count()
        
        # Get sample data
        sample_probes = list(Sondengroesse.objects.all()[:10].values(
            'durchmesser_sonde', 'schachttyp__schachttyp', 'hvb_size__hauptverteilerbalken',
            'artikelnummer', 'artikelbezeichnung'
        ))
        
        sample_schacht = list(Schacht.objects.all()[:5].values('schachttyp'))
        sample_hvb = list(HVB.objects.all()[:5].values('hauptverteilerbalken'))
        
        # Test specific combinations
        test_combinations = []
        for schacht in ['GN X1', 'GN X3', 'GN 2']:
            for hvb_size in ['63', '75', '90']:
                probes = Sondengroesse.objects.filter(
                    schachttyp__schachttyp=schacht,
                    hvb_size__hauptverteilerbalken=hvb_size
                ).values('durchmesser_sonde')
                
                test_combinations.append({
                    'schacht': schacht,
                    'hvb': hvb_size,
                    'probe_count': probes.count(),
                    'probes': list(probes)
                })
        
        return JsonResponse({
            'success': True,
            'database_counts': {
                'total_probes': total_probes,
                'total_schacht': total_schacht,
                'total_hvb': total_hvb
            },
            'sample_data': {
                'probes': sample_probes,
                'schacht': sample_schacht,
                'hvb': sample_hvb
            },
            'test_combinations': test_combinations
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Failed to debug probe data'
        })


@csrf_exempt
@require_http_methods(["POST", "GET"])
def test_endpoint(request):
    """Simple test endpoint to verify AJAX is working"""
    return JsonResponse({
        'status': 'success',
        'message': 'Test endpoint is working!',
        'method': request.method
    })