from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('configurator/', views.configurator, name='configurator'),
    path('configurations/', views.configuration_list, name='configuration_list'),
    path('configuration/<int:config_id>/', views.view_configuration, name='view_configuration'),
    path('configuration/<int:config_id>/delete/', views.delete_configuration, name='delete_configuration'),
    
    # API endpoints
    path('api/sonden-durchmesser-options/', views.get_sonden_durchmesser_options, name='get_sonden_durchmesser_options'),
    path('api/sonden-options/', views.get_sonden_options, name='get_sonden_options'),
    path('api/sondenabstand-options/', views.get_sondenabstand_options, name='get_sondenabstand_options'),
    path('api/allowed-hvb-sizes/', views.get_allowed_hvb_sizes, name='get_allowed_hvb_sizes'),
    path('api/schachtgrenze-info/', views.get_schachtgrenze_info, name='get_schachtgrenze_info'),
    path('api/dfm-options/', views.get_dfm_options, name='get_dfm_options'),
    path('api/check-configuration/', views.check_existing_configuration, name='check_existing_configuration'),
    path('api/gnx-chamber-articles/', views.get_gnx_chamber_articles, name='get_gnx_chamber_articles'),
    path('api/generate-bom/', views.generate_bom, name='generate_bom'),
    path('api/update-probes/', views.update_probes_endpoint, name='update_probes_endpoint'),
    path('api/debug-probes/', views.debug_probes_endpoint, name='debug_probes_endpoint'),
    path('api/test/', views.test_endpoint, name='test_endpoint'),
]
