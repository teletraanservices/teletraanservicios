from django.contrib import admin
from .models import MensajeProyecto, ServicioCliente


@admin.register(ServicioCliente)
class ServicioClienteAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'cliente', 'estado', 'agenda_aceptada', 'fecha_agenda', 'costo_estimado', 'fecha_ingreso')
    list_filter = ('estado', 'agenda_aceptada')
    search_fields = ('equipo', 'cliente__username', 'cliente__email', 'descripcion_falla')
    readonly_fields = ('fecha_ingreso', 'fecha_actualizacion')


@admin.register(MensajeProyecto)
class MensajeProyectoAdmin(admin.ModelAdmin):
    list_display = ('servicio', 'emisor', 'fecha_envio')
    search_fields = ('mensaje', 'emisor__username', 'servicio__equipo')
    readonly_fields = ('fecha_envio',)
