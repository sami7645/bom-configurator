from django.contrib import admin
from .models import (
    CSVDataSource, Schacht, HVB, Sondengroesse, Sondenabstand,
    Kugelhahn, DFM, Entlueftung, Sondenverschlusskappe,
    StumpfschweissEndkappe, WPVerschlusskappe, WPA, Verrohrung,
    Schachtgrenze, Schachtkompatibilitaet, BOMConfiguration,
    BOMItem, GNXChamberArticle, GNXChamberConfiguration
)


@admin.register(CSVDataSource)
class CSVDataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'file_path', 'last_modified', 'is_active']
    list_filter = ['is_active', 'last_modified']
    search_fields = ['name', 'file_path']


@admin.register(Schacht)
class SchachtAdmin(admin.ModelAdmin):
    list_display = ['schachttyp', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['schachttyp', 'artikelnummer', 'artikelbezeichnung']
    list_filter = ['schachttyp']


@admin.register(HVB)
class HVBAdmin(admin.ModelAdmin):
    list_display = ['hauptverteilerbalken', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['hauptverteilerbalken', 'artikelnummer', 'artikelbezeichnung']
    list_filter = ['hauptverteilerbalken']


@admin.register(Sondengroesse)
class SondengroesseAdmin(admin.ModelAdmin):
    list_display = ['durchmesser_sonde', 'schachttyp', 'hvb', 'artikelnummer', 'sondenanzahl_min', 'sondenanzahl_max']
    search_fields = ['durchmesser_sonde', 'schachttyp', 'hvb', 'artikelnummer']
    list_filter = ['durchmesser_sonde', 'schachttyp', 'hvb', 'bauform']


@admin.register(Sondenabstand)
class SondenabstandAdmin(admin.ModelAdmin):
    list_display = ['sondenabstand', 'anschlussart', 'zuschlag_links', 'zuschlag_rechts']
    search_fields = ['sondenabstand', 'anschlussart']
    list_filter = ['anschlussart']


@admin.register(Kugelhahn)
class KugelhahnAdmin(admin.ModelAdmin):
    list_display = ['kugelhahn', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['kugelhahn', 'artikelnummer', 'artikelbezeichnung']
    list_filter = ['kugelhahn']


@admin.register(DFM)
class DFMAdmin(admin.ModelAdmin):
    list_display = ['durchflussarmatur', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['durchflussarmatur', 'artikelnummer', 'artikelbezeichnung']
    list_filter = ['durchflussarmatur']


@admin.register(Entlueftung)
class EntlueftungAdmin(admin.ModelAdmin):
    list_display = ['name', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['name', 'artikelnummer', 'artikelbezeichnung']


@admin.register(Sondenverschlusskappe)
class SondenverschlusskapeAdmin(admin.ModelAdmin):
    list_display = ['name', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['name', 'artikelnummer', 'artikelbezeichnung']


@admin.register(StumpfschweissEndkappe)
class StumpfschweissEndkappeAdmin(admin.ModelAdmin):
    list_display = ['name', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['name', 'artikelnummer', 'artikelbezeichnung']


@admin.register(WPVerschlusskappe)
class WPVerschlusskappeAdmin(admin.ModelAdmin):
    list_display = ['name', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['name', 'artikelnummer', 'artikelbezeichnung']


@admin.register(WPA)
class WPAAdmin(admin.ModelAdmin):
    list_display = ['name', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['name', 'artikelnummer', 'artikelbezeichnung']


@admin.register(Verrohrung)
class VerrohrungAdmin(admin.ModelAdmin):
    list_display = ['verrohrung', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['verrohrung', 'artikelnummer', 'artikelbezeichnung']


@admin.register(Schachtgrenze)
class SchachtgrenzeAdmin(admin.ModelAdmin):
    list_display = ['name', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['name', 'artikelnummer', 'artikelbezeichnung']


@admin.register(Schachtkompatibilitaet)
class SchachtkompatibilitaetAdmin(admin.ModelAdmin):
    list_display = ['name', 'artikelnummer', 'artikelbezeichnung', 'menge_statisch']
    search_fields = ['name', 'artikelnummer', 'artikelbezeichnung']


class BOMItemInline(admin.TabularInline):
    model = BOMItem
    extra = 0
    readonly_fields = ['calculated_quantity']


class GNXChamberConfigurationInline(admin.TabularInline):
    model = GNXChamberConfiguration
    extra = 0


@admin.register(BOMConfiguration)
class BOMConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'schachttyp', 'hvb_size', 'sonden_durchmesser', 'sondenanzahl', 'created_at']
    search_fields = ['name', 'schachttyp', 'hvb_size', 'mother_article_number', 'full_article_number']
    list_filter = ['schachttyp', 'hvb_size', 'sonden_durchmesser', 'anschlussart', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [BOMItemInline, GNXChamberConfigurationInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'created_at', 'updated_at')
        }),
        ('Configuration Parameters', {
            'fields': (
                'schachttyp', 'hvb_size', 'sonden_durchmesser', 'sondenanzahl',
                'sondenabstand', 'anschlussart', 'kugelhahn_type', 'dfm_type'
            )
        }),
        ('Article Number Management', {
            'fields': (
                'mother_article_number', 'child_article_number', 'full_article_number',
                'is_existing_configuration', 'is_existing_mother_article'
            )
        }),
        ('Additional Parameters', {
            'fields': ('zuschlag_links', 'zuschlag_rechts')
        }),
    )


@admin.register(BOMItem)
class BOMItemAdmin(admin.ModelAdmin):
    list_display = ['configuration', 'artikelnummer', 'artikelbezeichnung', 'menge', 'source_table']
    search_fields = ['artikelnummer', 'artikelbezeichnung', 'configuration__name']
    list_filter = ['source_table', 'configuration__schachttyp']


@admin.register(GNXChamberArticle)
class GNXChamberArticleAdmin(admin.ModelAdmin):
    list_display = ['hvb_size_min', 'hvb_size_max', 'artikelnummer', 'artikelbezeichnung', 'is_automatic']
    search_fields = ['artikelnummer', 'artikelbezeichnung']
    list_filter = ['is_automatic', 'hvb_size_min', 'hvb_size_max']


@admin.register(GNXChamberConfiguration)
class GNXChamberConfigurationAdmin(admin.ModelAdmin):
    list_display = ['bom_configuration', 'gnx_article', 'custom_quantity']
    search_fields = ['bom_configuration__name', 'gnx_article__artikelnummer']
    list_filter = ['gnx_article__hvb_size_min', 'gnx_article__hvb_size_max']