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
    context = {
        'schacht_types': Schacht.objects.all().order_by('schachttyp'),
        'hvb_sizes': HVB.objects.all().order_by('hauptverteilerbalken'),
        'sondenabstaende': Sondenabstand.objects.all().order_by('sondenabstand'),
        'kugelhahn_types': Kugelhahn.objects.values('kugelhahn').distinct().order_by('kugelhahn'),
        'dfm_types': DFM.objects.values('durchflussarmatur').distinct().order_by('durchflussarmatur'),
    }
    return render(request, 'configurator/configurator.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def get_sonden_options(request):
    """Get probe options based on selected shaft type and HVB"""
    data = json.loads(request.body)
    schachttyp = data.get('schachttyp')
    hvb_size = data.get('hvb_size')
    
    sonden_options = Sondengroesse.objects.filter(
        schachttyp=schachttyp,
        hvb=hvb_size
    ).values(
        'durchmesser_sonde', 'sondenanzahl_min', 'sondenanzahl_max',
        'artikelnummer', 'artikelbezeichnung'
    ).distinct()
    
    return JsonResponse({
        'sonden_options': list(sonden_options)
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


def calculate_formula(formula, context):
    """Safely calculate formula with given context"""
    if not formula or formula.strip() == '':
        return None
    
    try:
        # Remove Excel = prefix if present
        safe_formula = formula.strip()
        if safe_formula.startswith('='):
            safe_formula = safe_formula[1:]
        
        # Replace variables in formula
        for key, value in context.items():
            safe_formula = safe_formula.replace(key, str(value))
        
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
            if hvb.menge_formel:
                calculated = calculate_formula(hvb.menge_formel, calc_context)
                if calculated is not None:
                    # Convert millimeters to meters for HVB length
                    quantity = calculated / 1000  # Convert mm to meters
            
            bom_item = BOMItem.objects.create(
                configuration=config,
                artikelnummer=hvb.artikelnummer,
                artikelbezeichnung=f"{hvb.artikelbezeichnung} ({quantity:.3f}m)" if hvb.menge_formel else hvb.artikelbezeichnung,
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
                
                total_qty = vorlauf_qty + ruecklauf_qty
                
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