from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    path('servicio/<int:servicio_id>/mensaje/', views.enviar_mensaje_view, name='enviar_mensaje'),
    path('servicio/<int:servicio_id>/mensajes/nuevos/', views.nuevos_mensajes_view, name='nuevos_mensajes'),
]
