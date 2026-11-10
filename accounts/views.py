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

from core.models import MensajeProyecto, PortfolioItem, ServicioCliente
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


@staff_member_required
def admin_panel_view(request):
    if request.method == 'POST':
        servicio = get_object_or_404(ServicioCliente, pk=request.POST.get('servicio_id'))
        form = ActualizarServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            messages.success(request, f'Orden #{servicio.pk} actualizada.')
        else:
            messages.error(request, 'No se pudo actualizar la orden. Revisa los valores ingresados.')
        return redirect('admin_panel')

    all_services = ServicioCliente.objects.all()
    service_summary = all_services.aggregate(
        total=Count('pk'),
        completed=Count('pk', filter=Q(estado='TERM')),
    )
    order_counts = {
        'total': service_summary['total'],
        'open': service_summary['total'] - service_summary['completed'],
        'completed': service_summary['completed'],
    }

    active_tab = request.GET.get('tab')
    if active_tab not in {'ordenes', 'clientes', 'portafolio'}:
        active_tab = 'ordenes'

    order_filter = AdminOrderFilterForm(
        request.GET if active_tab == 'ordenes' else None
    )
    services = all_services
    if order_filter.is_valid():
        search = order_filter.cleaned_data['q'].strip()
        if search:
            search_query = (
                Q(equipo__icontains=search)
                | Q(descripcion_falla__icontains=search)
                | Q(cliente__username__icontains=search)
                | Q(cliente__first_name__icontains=search)
                | Q(cliente__last_name__icontains=search)
                | Q(cliente__email__icontains=search)
            )
            if search.isdecimal() and len(search) <= 19:
                order_id = int(search)
                if order_id <= 9223372036854775807:
                    search_query |= Q(pk=order_id)
            services = services.filter(search_query)
        if order_filter.cleaned_data['status']:
            services = services.filter(estado=order_filter.cleaned_data['status'])
        if order_filter.cleaned_data['date_from']:
            services = services.filter(
                fecha_ingreso__date__gte=order_filter.cleaned_data['date_from']
            )
        if order_filter.cleaned_data['date_to']:
            services = services.filter(
                fecha_ingreso__date__lte=order_filter.cleaned_data['date_to']
            )
    else:
        services = all_services.none()

    services = services.select_related('cliente').prefetch_related(
        Prefetch('core_mensajes', queryset=MensajeProyecto.objects.select_related('emisor'))
    )
    order_page = Paginator(services, 20).get_page(request.GET.get('orders_page'))

    all_clients = User.objects.filter(is_staff=False, is_superuser=False)
    client_filter = AdminClientFilterForm(
        request.GET if active_tab == 'clientes' else None
    )
    filtered_clients = all_clients
    if client_filter.is_valid():
        search = client_filter.cleaned_data['q'].strip()
        if search:
            filtered_clients = filtered_clients.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        if client_filter.cleaned_data['active'] == 'active':
            filtered_clients = filtered_clients.filter(is_active=True)
        elif client_filter.cleaned_data['active'] == 'inactive':
            filtered_clients = filtered_clients.filter(is_active=False)
    else:
        filtered_clients = all_clients.none()

    clients_page = Paginator(
        filtered_clients.annotate(
            total_servicios=Count('core_servicios_cliente', distinct=True)
        ).order_by('-date_joined'),
        25,
    ).get_page(request.GET.get('clients_page'))

    proyectos = PortfolioItem.objects.all()
    query_params = request.GET.copy()
    query_params.pop('orders_page', None)
    query_params.pop('clients_page', None)
    query_params['tab'] = active_tab
    return render(request, 'accounts/admin_panel.html', {
        'servicios': order_page,
        'clientes': clients_page,
        'proyectos': proyectos,
        'estados': ServicioCliente.ESTADOS,
        'mensaje_form': MensajeProyectoForm(),
        'order_filter': order_filter,
        'client_filter': client_filter,
        'order_counts': order_counts,
        'orders_query': query_params.urlencode(),
        'clients_query': query_params.urlencode(),
        'active_tab': active_tab,
        'total_clients': all_clients.count(),
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


@staff_member_required
def portfolio_item_create_view(request):
    form = PortfolioItemForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Proyecto agregado al portafolio.')
        return redirect('admin_panel')
    return render(request, 'accounts/portfolio_form.html', {'form': form, 'heading': 'Agregar proyecto'})


@staff_member_required
def portfolio_item_edit_view(request, item_id):
    item = get_object_or_404(PortfolioItem, pk=item_id)
    old_image = item.image.name
    old_video = item.video.name
    form = PortfolioItemForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
        instance=item,
    )
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        if old_image and old_image != item.image.name:
            item.image.storage.delete(old_image)
        if old_video and old_video != item.video.name:
            item.video.storage.delete(old_video)
        messages.success(request, 'Proyecto actualizado.')
        return redirect('admin_panel')
    return render(request, 'accounts/portfolio_form.html', {
        'form': form,
        'heading': 'Editar proyecto',
        'item': item,
    })


@staff_member_required
@require_POST
def portfolio_item_delete_view(request, item_id):
    item = get_object_or_404(PortfolioItem, pk=item_id)
    image = item.image
    video = item.video
    item.delete()
    if image:
        image.storage.delete(image.name)
    if video:
        video.storage.delete(video.name)
    messages.success(request, 'Proyecto retirado del portafolio.')
    return redirect('admin_panel')


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
