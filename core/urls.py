from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('cookies/', views.cookies_view, name='cookies'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap'),
    path('health/', views.health_check, name='health_check'),
]
