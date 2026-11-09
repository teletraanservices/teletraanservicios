from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import MensajeProyecto, PortfolioItem, ServicioCliente
from .forms import (
    ActualizarServicioForm,
    LoginForm,
    MensajeProyectoForm,
    PortfolioItemForm,
    SolicitudServicioForm,
)


class SiteLoginView(LoginView):
    template_name = 'core/login.html'
    authentication_form = LoginForm

    def form_valid(self, form):
        response = super().form_valid(form)
        session_age = 30 * 24 * 60 * 60 if form.cleaned_data.get('remember_me') else 0
        self.request.session.set_expiry(session_age)
        return response


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

    servicios = ServicioCliente.objects.select_related('cliente').prefetch_related(
        Prefetch('core_mensajes', queryset=MensajeProyecto.objects.select_related('emisor'))
    )
    clientes = User.objects.filter(is_staff=False, is_superuser=False).annotate(
        total_servicios=Count('core_servicios_cliente', distinct=True)
    ).order_by('-date_joined')
    proyectos = PortfolioItem.objects.all()
    return render(request, 'accounts/admin_panel.html', {
        'servicios': servicios,
        'clientes': clientes,
        'proyectos': proyectos,
        'estados': ServicioCliente.ESTADOS,
        'mensaje_form': MensajeProyectoForm(),
    })


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
