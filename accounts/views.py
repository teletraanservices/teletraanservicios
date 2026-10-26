from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import MensajeProyecto, ServicioCliente
from .forms import ActualizarServicioForm, MensajeProyectoForm, SolicitudServicioForm


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
        Prefetch('mensajes', queryset=mensajes)
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
        Prefetch('mensajes', queryset=MensajeProyecto.objects.select_related('emisor'))
    )
    clientes = User.objects.filter(is_staff=False, is_superuser=False).annotate(
        total_servicios=Count('servicios', distinct=True)
    ).order_by('-date_joined')
    return render(request, 'accounts/admin_panel.html', {
        'servicios': servicios,
        'clientes': clientes,
        'estados': ServicioCliente.ESTADOS,
        'mensaje_form': MensajeProyectoForm(),
    })


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
    nuevos = servicio.mensajes.filter(pk__gt=after_id).select_related('emisor').order_by('pk')[:100]
    return JsonResponse({'messages': [{
        'id': message.pk,
        'author': message.emisor.username,
        'sent_at': message.fecha_envio.strftime('%d/%m/%Y %H:%M'),
        'text': message.mensaje,
        'staff': message.emisor.is_staff,
    } for message in nuevos]})
