def calculate_hvb_length(config):
    # Calculate HVB length using proper formulas
    try:
        sondenanzahl = Decimal(config.sondenanzahl)
        distance = Decimal(config.sondenabstand)
        zuschlag_links = Decimal(config.zuschlag_links or 100)
        zuschlag_rechts = Decimal(config.zuschlag_rechts or 100)
    except Exception:
        return None

    if sondenanzahl <= 1 or distance <= 0:
        return None

    # Use U-form for chambers with multiple probes, I-form for manifolds
    if config.schachttyp == 'Verteiler' or config.bauform == 'I':
        # I-form formula: (sondenanzahl - 1) * sondenabstand + zuschläge
        base = (sondenanzahl - 1) * distance
    else:
        # U-form formula for chambers: (sondenanzahl - 1) * sondenabstand + zuschläge
        # Note: Both formulas are the same for the base calculation
        base = (sondenanzahl - 1) * distance

    total_mm = base + zuschlag_links + zuschlag_rechts
    if total_mm <= 0:
        return None
    return total_mm / Decimal('1000')
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
    Schacht, HVB, Sondengroesse, Sondenabstand, SondenDurchmesser, Kugelhahn, DFM,
    BOMConfiguration, BOMItem, GNXChamberArticle, GNXChamberConfiguration,
    Schachtgrenze
)
from .services import bom_rules
from .utils import parse_allowed_hvb_sizes
from .utils import format_artikelnummer, calculate_formula, check_compatibility


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
    
    # Get DFM types - no longer needed in template since we'll load via AJAX
    # Just get basic data for context if needed elsewhere
    dfm_types = []
    brass_flowmeters = []
    plastic_flowmeters = []
    
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
def get_sonden_durchmesser_options(request):
    """Get Sonden Durchmesser options based on selected schachttyp"""
    try:
        data = json.loads(request.body)
        schachttyp = data.get('schachttyp', '').strip()
        
        if not schachttyp:
            return JsonResponse({
                'sonden_durchmesser_options': [],
                'error': 'Missing schachttyp'
            })
        
        # Check if any data exists in SondenDurchmesser table
        total_count = SondenDurchmesser.objects.count()
        if total_count == 0:
            return JsonResponse({
                'sonden_durchmesser_options': [],
                'error': 'CSV data not imported. Please run: python manage.py import_csv_data --force'
            }, status=500)
        
        # Get probe diameters for this schacht type from SondenDurchmesser model
        # Use case-insensitive matching and handle potential whitespace differences
        schachttyp_clean = schachttyp.strip()
        
        # Debug: Log what we're searching for
        print(f"DEBUG: Searching for schachttyp: '{schachttyp_clean}'")
        
        # First try exact match (case-insensitive)
        durchmesser_list = list(SondenDurchmesser.objects.filter(
            schachttyp__iexact=schachttyp_clean
        ).values_list('durchmesser', flat=True).distinct())
        
        print(f"DEBUG: Found {len(durchmesser_list)} diameters with exact match")
        
        # If no exact match, try fuzzy matching
        if not durchmesser_list:
            # Get all schacht types from database
            all_schacht_types = SondenDurchmesser.objects.values_list('schachttyp', flat=True).distinct()
            print(f"DEBUG: Available schacht types in DB: {list(all_schacht_types)}")
            
            # Try to find by matching (normalize both sides)
            search_normalized = schachttyp_clean.lower().replace(' ', '')
            for st in all_schacht_types:
                st_normalized = st.strip().lower().replace(' ', '')
                if st_normalized == search_normalized:
                    print(f"DEBUG: Found fuzzy match: '{st}' matches '{schachttyp_clean}'")
                    durchmesser_list = list(SondenDurchmesser.objects.filter(
                        schachttyp=st
                    ).values_list('durchmesser', flat=True).distinct())
                    break
        
        print(f"DEBUG: Final result: {len(durchmesser_list)} diameters - {list(durchmesser_list)}")
        
        # Sort numerically
        durchmesser_list = sorted(
            durchmesser_list,
            key=lambda x: int(x) if x.isdigit() else 9999
        )
        
        # Format as options
        options = [{'durchmesser': d, 'label': f'{d}mm'} for d in durchmesser_list]
        
        return JsonResponse({
            'sonden_durchmesser_options': options,
            'schachttyp': schachttyp
        })
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Sonden Durchmesser Options Error: {str(e)}")
        print(f"Traceback: {error_trace}")
        return JsonResponse({
            'sonden_durchmesser_options': [],
            'error': str(e)
        }, status=500)


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
        
        # Try strict case-insensitive match first
        sonden_options = Sondengroesse.objects.filter(
            schachttyp__iexact=schachttyp,
            hvb__iexact=hvb_size
        )
        
        print(f"DEBUG: Query filter - schachttyp='{schachttyp}', hvb='{hvb_size}'")
        print(f"DEBUG: Found {sonden_options.count()} probes with exact match")
        
        # If no exact match, try to find similar matches for debugging
        if sonden_options.count() == 0:
            print(f"DEBUG: No exact match found. Searching for similar...")
            
            # Try fuzzy HVB matching and trimmed values
            if sonden_options.count() == 0:
                sonden_options = Sondengroesse.objects.filter(
                    schachttyp__iexact=schachttyp.strip(),
                    hvb__icontains=hvb_size.strip()
                )
                print(f"DEBUG: Fuzzy/trimmed match found: {sonden_options.count()}")

            # Safe fallback: if still nothing, try by schachttyp only
            fallback_used = False
            if sonden_options.count() == 0:
                fallback_used = True
                sonden_options = Sondengroesse.objects.filter(
                    schachttyp__iexact=schachttyp.strip()
                )
                print(f"DEBUG: Fallback by schachttyp only: {sonden_options.count()}")
            
            # Show what schachttyp values exist
            all_schacht = Sondengroesse.objects.values_list('schachttyp', flat=True).distinct()
            print(f"DEBUG: Available schachttyp values: {list(all_schacht)}")
            
            # Show what hvb values exist
            all_hvb = Sondengroesse.objects.values_list('hvb', flat=True).distinct()
            print(f"DEBUG: Available hvb values: {list(all_hvb)}")
            
            # Show first few probes
            sample_probes = Sondengroesse.objects.all()[:5]
            for probe in sample_probes:
                print(f"DEBUG: Sample probe - schachttyp: '{probe.schachttyp}' (repr: {repr(probe.schachttyp)}), hvb: '{probe.hvb}' (repr: {repr(probe.hvb)})")
        
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
        if 'fallback_used' in locals() and fallback_used:
            response_payload['debug']['fallback'] = 'schachttyp_only'
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
def get_allowed_hvb_sizes(request):
    """Get allowed HVB sizes for a selected Schachttyp based on Schachtgrenze"""
    try:
        data = json.loads(request.body)
        schachttyp = data.get('schachttyp', '').strip()
        
        if not schachttyp:
            return JsonResponse({'allowed_sizes': [], 'error': 'Schachttyp is required'})
        
        # Get Schachtgrenze for this Schachttyp
        try:
            schachtgrenze = Schachtgrenze.objects.get(schachttyp=schachttyp)
            erlaubte_hvb = schachtgrenze.erlaubte_hvb or ''
        except Schachtgrenze.DoesNotExist:
            # If no restriction found, allow all HVB sizes
            return JsonResponse({'allowed_sizes': [], 'all_allowed': True})
        
        # Parse allowed HVB sizes from erlaubte_hvb field
        allowed_sizes = parse_allowed_hvb_sizes(erlaubte_hvb)
        
        return JsonResponse({
            'allowed_sizes': allowed_sizes,
            'all_allowed': len(allowed_sizes) == 0  # If empty, all are allowed
        })
    except Exception as e:
        return JsonResponse({'allowed_sizes': [], 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def get_schachtgrenze_info(request):
    """Get max sondenanzahl from Schachtgrenze based on Schachttyp"""
    try:
        data = json.loads(request.body)
        schachttyp = data.get('schachttyp', '').strip()
        
        if not schachttyp:
            return JsonResponse({'max_sondenanzahl': None, 'error': 'Schachttyp is required'})
        
        # Get Schachtgrenze for this Schachttyp
        try:
            schachtgrenze = Schachtgrenze.objects.get(schachttyp=schachttyp)
            max_sondenanzahl = schachtgrenze.max_sondenanzahl
            return JsonResponse({
                'max_sondenanzahl': max_sondenanzahl,
                'min_sondenanzahl': 2  # Always 2 as per requirement
            })
        except Schachtgrenze.DoesNotExist:
            # If no restriction found, return None (no limit)
            return JsonResponse({
                'max_sondenanzahl': None,
                'min_sondenanzahl': 2,
                'error': 'No Schachtgrenze found for this Schachttyp'
            })
    except Exception as e:
        return JsonResponse({'max_sondenanzahl': None, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def get_dfm_options(request):
    """Get DFM options based on category"""
    from configurator.utils import sort_by_numeric_range
    
    data = json.loads(request.body)
    category = data.get('category', '')
    
    if not category:
        return JsonResponse({'dfm_options': []})
    
    # Exclude category headers that shouldn't be selectable
    exclude_categories = ['Brass Flowmeters', 'Plastic Flowmeters']
    all_dfm_types = DFM.objects.exclude(
        durchflussarmatur__in=exclude_categories
    ).values('durchflussarmatur').distinct().order_by('durchflussarmatur')
    
    dfm_options = []
    
    # "Kugelhahn-Typ" is always available as an option regardless of category
    # Note: This will be added in the frontend, but we keep the backend clean
    
    for dfm in all_dfm_types:
        name = dfm['durchflussarmatur']
        
        if category == 'plastic':
            # Plastic flow meters: K-DFM series
            if name.startswith('K-DFM'):
                dfm_options.append(name)
        elif category == 'brass':
            # Brass flow meters: HC VTR, IMI STAD, IMI TA series
            if (name.startswith('HC VTR') or 
                name.startswith('IMI STAD') or 
                name.startswith('IMI TA')):
                dfm_options.append(name)
    
    # Sort by numeric range (e.g., "2-12", "5-42", "8-28", "35-70")
    dfm_options = sort_by_numeric_range(dfm_options)
    
    return JsonResponse({
        'dfm_options': dfm_options
    })


@csrf_exempt
@require_http_methods(["POST"])
def check_existing_configuration(request):
    """Check if configuration already exists - matches exact requirements from client"""
    data = json.loads(request.body)
    
    # Extract configuration parameters
    schachttyp = data.get('schachttyp')
    hvb_size = data.get('hvb_size')
    sonden_durchmesser = data.get('sonden_durchmesser')
    sondenanzahl = data.get('sondenanzahl')
    sondenabstand = data.get('sondenabstand')
    anschlussart = data.get('anschlussart')
    kugelhahn_type = data.get('kugelhahn_type', '') or ''
    dfm_type = data.get('dfm_type', '') or ''
    dfm_category = data.get('dfm_category', '') or ''
    dfm_kugelhahn_type = data.get('dfm_kugelhahn_type', '') or ''
    bauform = data.get('bauform', 'I') or 'I'
    
    # Normalize empty strings to None for optional fields
    kugelhahn_type = kugelhahn_type if kugelhahn_type else None
    dfm_type = dfm_type if dfm_type else None
    dfm_category = dfm_category if dfm_category else None
    dfm_kugelhahn_type = dfm_kugelhahn_type if dfm_kugelhahn_type else None
    
    # STEP 1: Check if exact configuration exists (all parameters match)
    # This includes optional fields - if they're None, match None; if they have values, match values
    query = BOMConfiguration.objects.filter(
        schachttyp=schachttyp,
        hvb_size=hvb_size,
        sonden_durchmesser=sonden_durchmesser,
        sondenanzahl=sondenanzahl,
        sondenabstand=sondenabstand,
        anschlussart=anschlussart,
        bauform=bauform
    )
    
    # Handle optional fields - match None if not provided, or match value if provided
    if kugelhahn_type is None:
        query = query.filter(kugelhahn_type__isnull=True)
    else:
        query = query.filter(kugelhahn_type=kugelhahn_type)
    
    if dfm_type is None:
        query = query.filter(dfm_type__isnull=True)
    else:
        query = query.filter(dfm_type=dfm_type)
    
    if dfm_category is None:
        query = query.filter(dfm_category__isnull=True)
    else:
        query = query.filter(dfm_category=dfm_category)
    
    if dfm_kugelhahn_type is None:
        query = query.filter(dfm_kugelhahn_type__isnull=True)
    else:
        query = query.filter(dfm_kugelhahn_type=dfm_kugelhahn_type)
    
    existing_config = query.first()
    
    if existing_config and existing_config.full_article_number:
        # Exact configuration exists with article number
        return JsonResponse({
            'exists': True,
            'type': 'full_configuration',
            'article_number': existing_config.full_article_number,
            'configuration_id': existing_config.id,
            'message': f'Diese Konfiguration existiert bereits mit Artikelnummer: {existing_config.full_article_number}'
        })
    
    # STEP 2: Check if mother article exists (base configuration match)
    # Mother article is defined by: schachttyp, hvb_size, sonden_durchmesser
    # Find any configuration with these base parameters that has a mother_article_number
    mother_config = BOMConfiguration.objects.filter(
        schachttyp=schachttyp,
        hvb_size=hvb_size,
        sonden_durchmesser=sonden_durchmesser,
        mother_article_number__isnull=False
    ).exclude(mother_article_number='').first()
    
    if mother_config and mother_config.mother_article_number:
        # Check if this exact configuration already has a child article
        # (i.e., does this exact config exist as a child of this mother?)
        existing_child = BOMConfiguration.objects.filter(
            schachttyp=schachttyp,
            hvb_size=hvb_size,
            sonden_durchmesser=sonden_durchmesser,
            sondenanzahl=sondenanzahl,
            sondenabstand=sondenabstand,
            anschlussart=anschlussart,
            bauform=bauform,
            kugelhahn_type=kugelhahn_type,
            dfm_type=dfm_type,
            dfm_category=dfm_category,
            dfm_kugelhahn_type=dfm_kugelhahn_type,
            mother_article_number=mother_config.mother_article_number
        ).exclude(child_article_number__isnull=True).exclude(child_article_number='').first()
        
        if existing_child and existing_child.child_article_number:
            # This exact configuration already exists as a child
            full_article = f"{mother_config.mother_article_number}-{existing_child.child_article_number.split('-')[-1]}"
            return JsonResponse({
                'exists': True,
                'type': 'full_configuration',
                'article_number': full_article,
                'configuration_id': existing_child.id,
                'message': f'Diese Konfiguration existiert bereits mit Artikelnummer: {full_article}'
            })
        
        # Mother article exists, but this exact configuration doesn't have a child article yet
        # Find the highest child number and suggest the next one
        existing_children = BOMConfiguration.objects.filter(
            mother_article_number=mother_config.mother_article_number
        ).exclude(child_article_number__isnull=True).exclude(child_article_number='')
        
        # Extract child numbers and find the highest
        max_child_num = 0
        for child in existing_children:
            child_num_str = child.child_article_number.split('-')[-1] if '-' in child.child_article_number else child.child_article_number
            try:
                child_num = int(child_num_str)
                max_child_num = max(max_child_num, child_num)
            except ValueError:
                pass
        
        next_child_number = f"{mother_config.mother_article_number}-{max_child_num + 1:03d}"
        
        return JsonResponse({
            'exists': True,
            'type': 'mother_article',
            'mother_article_number': mother_config.mother_article_number,
            'suggested_child_number': next_child_number,
            'message': f'Mutterartikel "{mother_config.mother_article_number}" existiert bereits, aber es gibt keine Kindartikelnummer zu dieser Konfiguration.'
        })
    
    # STEP 3: No match found - new configuration
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


@csrf_exempt
@require_http_methods(["POST"])
def generate_bom(request):
    """Generate BOM based on configuration"""
    data = json.loads(request.body)
    
    try:
        # Validate required fields (check for None, not falsy values, since 0 is valid)
        required_fields = ['schachttyp', 'hvb_size', 'sonden_durchmesser', 'sondenanzahl', 'sondenabstand', 'anschlussart']
        missing_fields = [field for field in required_fields if data.get(field) is None or data.get(field) == '']
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Fehlende Pflichtfelder: {", ".join(missing_fields)}',
                'message': f'Bitte füllen Sie alle Pflichtfelder aus: {", ".join(missing_fields)}'
            })
        
        # Safely convert to int with defaults
        sondenanzahl = data.get('sondenanzahl', 0)
        sondenabstand = data.get('sondenabstand', 0)
        zuschlag_links = data.get('zuschlag_links', 100)
        zuschlag_rechts = data.get('zuschlag_rechts', 100)
        
        try:
            sondenanzahl = int(sondenanzahl) if sondenanzahl else 0
            sondenabstand = int(sondenabstand) if sondenabstand else 0
            zuschlag_links = int(zuschlag_links) if zuschlag_links else 100
            zuschlag_rechts = int(zuschlag_rechts) if zuschlag_rechts else 100
        except (ValueError, TypeError) as e:
            return JsonResponse({
                'success': False,
                'error': f'Ungültige Zahlenwerte: {str(e)}',
                'message': 'Bitte überprüfen Sie die eingegebenen Zahlenwerte.'
            })
        
        # Handle article number logic
        mother_article_number = data.get('mother_article_number', '') or ''
        child_article_number = data.get('child_article_number', '') or ''
        full_article_number = data.get('full_article_number', '') or ''
        
        # If child_article_number is provided in format "1000089-002", extract mother and child
        if child_article_number and '-' in child_article_number:
            parts = child_article_number.split('-', 1)
            if not mother_article_number:
                mother_article_number = parts[0]
            if len(parts) > 1:
                child_article_number = parts[1]
            if not full_article_number:
                full_article_number = child_article_number  # Use the full format provided
        
        # If full_article_number is provided in format "1000089-002", extract mother and child
        if full_article_number and '-' in full_article_number and not mother_article_number:
            parts = full_article_number.split('-', 1)
            mother_article_number = parts[0]
            if len(parts) > 1:
                child_article_number = parts[1]
        
        # If we have mother and child, construct full_article_number
        if mother_article_number and child_article_number and not full_article_number:
            full_article_number = f"{mother_article_number}-{child_article_number}"
        
        # Create BOM configuration
        config = BOMConfiguration.objects.create(
            name=data.get('configuration_name', 'Neue Konfiguration'),
            schachttyp=data.get('schachttyp'),
            hvb_size=data.get('hvb_size'),
            sonden_durchmesser=data.get('sonden_durchmesser'),
            sondenanzahl=sondenanzahl,
            sondenabstand=sondenabstand,
            anschlussart=data.get('anschlussart'),
            kugelhahn_type=data.get('kugelhahn_type', '') or None,
            dfm_type=data.get('dfm_type', '') or None,
            dfm_category=data.get('dfm_category', '') or None,
            dfm_kugelhahn_type=data.get('dfm_kugelhahn_type', '') or None,
            bauform=data.get('bauform', 'I') or 'I',
            mother_article_number=mother_article_number or None,
            child_article_number=child_article_number or None,
            full_article_number=full_article_number or None,
            zuschlag_links=zuschlag_links,
            zuschlag_rechts=zuschlag_rechts
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
                artikelnummer=format_artikelnummer(schacht.artikelnummer),
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
            length = calculate_hvb_length(config)
            if length is not None:
                quantity = length
                calculated = length * Decimal('1000')
            elif hvb.menge_formel:
                calculated_value = calculate_formula(hvb.menge_formel, calc_context)
                if calculated_value is not None:
                    quantity = calculated_value / Decimal('1000')
                    calculated = calculated_value
            
            # Format description with length in meters
            if hvb.menge_formel and calculated is not None:
                artikelbezeichnung = f"{hvb.artikelbezeichnung} ({calculated:.0f}mm / {quantity:.3f}m)"
            else:
                artikelbezeichnung = hvb.artikelbezeichnung
            
            bom_item = BOMItem.objects.create(
                configuration=config,
                artikelnummer=format_artikelnummer(hvb.artikelnummer),
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
                print(f"DEBUG Sonden: Vorlauf={vorlauf_qty}, Ruecklauf={ruecklauf_qty}, Sondenanzahl={config.sondenanzahl}, Total={total_qty}")
                
                if total_qty > 0:
                    bom_item = BOMItem.objects.create(
                        configuration=config,
                        artikelnummer=format_artikelnummer(sonde.artikelnummer),
                        artikelbezeichnung=sonde.artikelbezeichnung,
                        menge=total_qty,
                        source_table='Sondengroesse'
                    )
                    print(f"DEBUG BOMItem created: Menge={bom_item.menge}, Type={type(bom_item.menge)}, String={str(bom_item.menge)}")
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
                    artikelnummer=format_artikelnummer(gnx_article.artikelnummer),
                    artikelbezeichnung=gnx_article.artikelbezeichnung,
                    menge=custom_quantity,
                    source_table='GNXChamberArticle'
                )
                bom_items.append(bom_item)
        
        # Use rule-based builders for all configurations
        additional_components = []
        additional_components.extend(bom_rules.build_hvb_stuetze_components(config))
        additional_components.extend(bom_rules.build_kugelhahn_components(config, calc_context))
        additional_components.extend(bom_rules.build_dfm_kugelhahn_components(config, calc_context))
        additional_components.extend(bom_rules.build_plastic_dfm_components(config, calc_context))
        additional_components.extend(bom_rules.build_sondenverschlusskappen(config, calc_context))
        additional_components.extend(bom_rules.build_stumpfschweiss_endkappen(config))
        additional_components.extend(bom_rules.build_entlueftung_components(config, calc_context))
        additional_components.extend(bom_rules.build_manifold_components(config))

        component_map = {}
        for component in additional_components:
            # Use both artikelnummer and source_table as key to keep different sources separate
            # This ensures "Kugelhahn" and "D-Kugelhahn" items are distinguished even if same article
            source = component.get('source_table', component.get('source', 'Unknown'))
            key = f"{component['artikelnummer']}::{source}"
            
            if key in component_map:
                component_map[key]['menge'] += component['menge']
            else:
                component_map[key] = {
                    'artikelnummer': component['artikelnummer'],
                    'artikelbezeichnung': component['artikelbezeichnung'],
                    'menge': component['menge'],
                    'source_table': source
                }

        for component in component_map.values():
            bom_item = BOMItem.objects.create(
                configuration=config,
                artikelnummer=format_artikelnummer(component['artikelnummer']),
                artikelbezeichnung=component['artikelbezeichnung'],
                menge=component['menge'],
                source_table=component['source_table']
            )
            bom_items.append(bom_item)
        
        # Prepare response data
        bom_data = []
        for item in bom_items:
            # Convert Decimal to float for JSON serialization to avoid any scaling issues
            menge_value = float(item.menge)
            print(f"DEBUG JSON: Article {item.artikelnummer}, Menge in DB: {item.menge}, Float: {menge_value}, Source: {item.source_table}")
            bom_data.append({
                'artikelnummer': item.artikelnummer,
                'artikelbezeichnung': item.artikelbezeichnung,
                'menge': menge_value,  # Use float instead of string to ensure correct serialization
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"BOM Generation Error: {str(e)}")
        print(f"Traceback: {error_trace}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': f'Fehler beim Generieren der BOM: {str(e)}',
            'traceback': error_trace
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