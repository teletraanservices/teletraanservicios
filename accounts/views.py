from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.conf import settings
from django.core import mail
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from urllib.parse import urlencode
from django.views.decorators.http import require_POST
from smtplib import SMTPException
import logging

from core.models import MensajeProyecto, PortfolioImage, PortfolioItem, ServicioCliente
from .forms import (
    AdminClientFilterForm,
    AdminOrderFilterForm,
    ActualizarServicioForm,
    LoginForm,
    MensajeProyectoForm,
    PasswordResetForm,
    PortfolioItemForm,
    SolicitudServicioForm,
)

logger = logging.getLogger(__name__)


class SiteLoginView(LoginView):
    template_name = 'core/login.html'
    authentication_form = LoginForm

    def get_success_url(self):
        return reverse('admin_panel' if self.request.user.is_staff else 'dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_portal_enabled'] = settings.CUSTOMER_PORTAL_ENABLED
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        session_age = 30 * 24 * 60 * 60 if form.cleaned_data.get('remember_me') else 0
        self.request.session.set_expiry(session_age)
        return response


class SitePasswordResetView(auth_views.PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.txt'
    subject_template_name = 'accounts/password_reset_subject.txt'
    form_class = PasswordResetForm

    def email_service_configured(self):
        mailer = settings.MAILERS['default']
        if mailer['BACKEND'] == 'accounts.email_backend.ResendEmailBackend':
            return bool(
                mailer.get('OPTIONS', {}).get('api_key')
                and settings.DEFAULT_FROM_EMAIL
                and not settings.DEFAULT_FROM_EMAIL.endswith('@localhost')
            )
        if mailer['BACKEND'] != 'django.core.mail.backends.smtp.EmailBackend':
            return True
        return bool(
            mailer.get('OPTIONS', {}).get('host')
            and settings.DEFAULT_FROM_EMAIL
            and not settings.DEFAULT_FROM_EMAIL.endswith('@localhost')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email_service_configured'] = self.email_service_configured()
        return context

    def form_valid(self, form):
        if not self.email_service_configured():
            return self.render_to_response(
                self.get_context_data(form=form, email_unavailable=True),
                status=503,
            )

        try:
            if settings.MAILERS['default']['BACKEND'] == 'django.core.mail.backends.smtp.EmailBackend':
                connection = mail.get_connection()
                if connection.open() is False:
                    raise OSError('El proveedor de correo no pudo abrir una conexión.')
                connection.close()
            return super().form_valid(form)
        except (OSError, SMTPException):
            logger.exception('No se pudo entregar el correo de recuperación de contraseña.')
            return self.render_to_response(
                self.get_context_data(form=form, email_unavailable=True),
                status=503,
            )


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Tu cuenta quedó creada. Ya puedes solicitar y seguir tus servicios.')
        return redirect('dashboard')
    return render(request, 'core/register.html', {'form': form})


@login_required
def dashboard_view(request):
    if request.user.is_staff:
        return redirect('admin_panel')
    solicitud_form = SolicitudServicioForm()
    if request.method == 'POST':
        solicitud_form = SolicitudServicioForm(request.POST)
        if solicitud_form.is_valid():
            servicio = solicitud_form.save(commit=False)
            servicio.cliente = request.user
            servicio.save()
            messages.success(request, 'Recibimos tu solicitud. Puedes conversar con nuestro equipo desde esta orden.')
            return redirect('dashboard')
    mensajes = MensajeProyecto.objects.select_related('emisor')
    servicios = ServicioCliente.objects.filter(cliente=request.user).prefetch_related(
        Prefetch('core_mensajes', queryset=mensajes)
    )
    return render(request, 'accounts/dashboard.html', {
        'servicios': servicios,
        'solicitud_form': solicitud_form,
        'mensaje_form': MensajeProyectoForm(),
    })


@staff_member_required(login_url='login')
def admin_panel_view(request):
    return render(request, 'accounts/admin_panel.html', {
        'proyectos': PortfolioItem.objects.all(),
    })


@staff_member_required
@require_POST
def toggle_customer_active_view(request, user_id):
    customer = get_object_or_404(
        User,
        pk=user_id,
        is_staff=False,
        is_superuser=False,
    )
    customer.is_active = not customer.is_active
    customer.save(update_fields=['is_active'])
    if customer.is_active:
        messages.success(request, f'La cuenta de {customer.username} fue activada.')
    else:
        messages.success(request, f'La cuenta de {customer.username} fue desactivada.')

    query = {
        key: request.POST[key]
        for key in ('q', 'clients_page')
        if request.POST.get(key)
    }
    query['active'] = 'active' if customer.is_active else 'inactive'
    query['tab'] = 'clientes'
    return redirect(f'{reverse("admin_panel")}?{urlencode(query)}')


@staff_member_required(login_url='login')
def portfolio_item_create_view(request):
    form = PortfolioItemForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
    )
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        _save_extra_portfolio_images(item, form)
        messages.success(request, 'Proyecto agregado al portafolio.')
        return redirect('admin_panel')
    return render(request, 'accounts/portfolio_form.html', {'form': form, 'heading': 'Agregar proyecto'})


@staff_member_required(login_url='login')
def portfolio_item_edit_view(request, item_id):
    item = get_object_or_404(PortfolioItem, pk=item_id)
    old_image = item.image
    old_gallery_images = list(item.gallery_images.all())
    old_video = item.video.name
    form = PortfolioItemForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
        instance=item,
    )
    if request.method == 'POST' and form.is_valid():
        uploaded_images = form.fields['image'].uploaded_images
        item = form.save()
        if uploaded_images:
            item.gallery_images.all().delete()
            _save_extra_portfolio_images(item, form)
            if old_image and old_image.name != item.image.name:
                old_image.storage.delete(old_image.name)
            for gallery_image in old_gallery_images:
                gallery_image.image.storage.delete(gallery_image.image.name)
        if old_video and old_video != item.video.name:
            item.video.storage.delete(old_video)
        messages.success(request, 'Proyecto actualizado.')
        return redirect('admin_panel')
    return render(request, 'accounts/portfolio_form.html', {
        'form': form,
        'heading': 'Editar proyecto',
        'item': item,
    })


@staff_member_required(login_url='login')
@require_POST
def portfolio_item_delete_view(request, item_id):
    item = get_object_or_404(PortfolioItem, pk=item_id)
    image = item.image
    gallery_images = list(item.gallery_images.all())
    video = item.video
    item.delete()
    if image:
        image.storage.delete(image.name)
    for gallery_image in gallery_images:
        gallery_image.image.storage.delete(gallery_image.image.name)
    if video:
        video.storage.delete(video.name)
    messages.success(request, 'Proyecto retirado del portafolio.')
    return redirect('admin_panel')


def _save_extra_portfolio_images(item, form):
    for position, uploaded_image in enumerate(form.fields['image'].uploaded_images[1:], start=1):
        PortfolioImage.objects.create(portfolio_item=item, image=uploaded_image, position=position)


@login_required
@require_POST
def enviar_mensaje_view(request, servicio_id):
    servicio = get_object_or_404(ServicioCliente, pk=servicio_id)
    if not request.user.is_staff and servicio.cliente_id != request.user.pk:
        messages.error(request, 'No tienes permiso para acceder a esta conversación.')
        return redirect('dashboard')
    form = MensajeProyectoForm(request.POST)
    if form.is_valid():
        mensaje = form.save(commit=False)
        mensaje.servicio = servicio
        mensaje.emisor = request.user
        mensaje.save()
        messages.success(request, 'Mensaje enviado.')
    else:
        messages.error(request, 'El mensaje no puede estar vacío y debe tener hasta 2000 caracteres.')
    return redirect('admin_panel' if request.user.is_staff else 'dashboard')


@login_required
def nuevos_mensajes_view(request, servicio_id):
    servicio = get_object_or_404(ServicioCliente, pk=servicio_id)
    if not request.user.is_staff and servicio.cliente_id != request.user.pk:
        return JsonResponse({'error': 'forbidden'}, status=403)
    try:
        after_id = max(0, int(request.GET.get('after', 0)))
    except (TypeError, ValueError):
        after_id = 0
    nuevos = servicio.core_mensajes.filter(pk__gt=after_id).select_related('emisor').order_by('pk')[:100]
    return JsonResponse({'messages': [{
        'id': message.pk,
        'author': message.emisor.username,
        'sent_at': message.fecha_envio.strftime('%d/%m/%Y %H:%M'),
        'text': message.mensaje,
        'staff': message.emisor.is_staff,
    } for message in nuevos]})
