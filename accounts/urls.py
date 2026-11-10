from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views
from .forms import SetPasswordForm

urlpatterns = [
    path('login/', views.SiteLoginView.as_view(), name='login'),
    path('password-reset/', views.SitePasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        form_class=SetPasswordForm,
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
    path('register/', views.register_view, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    path('admin-panel/clientes/<int:user_id>/estado/', views.toggle_customer_active_view, name='customer_toggle_active'),
    path('portfolio/nuevo/', views.portfolio_item_create_view, name='portfolio_create'),
    path('portfolio/<int:item_id>/editar/', views.portfolio_item_edit_view, name='portfolio_edit'),
    path('portfolio/<int:item_id>/eliminar/', views.portfolio_item_delete_view, name='portfolio_delete'),
    path('servicio/<int:servicio_id>/mensaje/', views.enviar_mensaje_view, name='enviar_mensaje'),
    path('servicio/<int:servicio_id>/mensajes/nuevos/', views.nuevos_mensajes_view, name='nuevos_mensajes'),
]
