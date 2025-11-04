from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('configurator/', views.configurator, name='configurator'),
    path('configurations/', views.configuration_list, name='configuration_list'),
    path('configuration/<int:config_id>/', views.view_configuration, name='view_configuration'),
    path('configuration/<int:config_id>/delete/', views.delete_configuration, name='delete_configuration'),
    
    # API endpoints
    path('api/sonden-options/', views.get_sonden_options, name='get_sonden_options'),
    path('api/sondenabstand-options/', views.get_sondenabstand_options, name='get_sondenabstand_options'),
    path('api/check-configuration/', views.check_existing_configuration, name='check_existing_configuration'),
    path('api/gnx-chamber-articles/', views.get_gnx_chamber_articles, name='get_gnx_chamber_articles'),
    path('api/generate-bom/', views.generate_bom, name='generate_bom'),
    path('api/update-probes/', views.update_probes_endpoint, name='update_probes_endpoint'),
]
