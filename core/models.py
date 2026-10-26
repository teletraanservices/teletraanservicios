from django.conf import settings
from django.db import models


class ServicioCliente(models.Model):
    ESTADOS = [
        ('AGEN', '1. Agenda / Solicitud Recibida'),
        ('CONF', '2. Cita Confirmada'),
        ('EVAL', '3. En Evaluación de Costo'),
        ('COST', '4. Evaluación de Costo Terminada'),
        ('EJE', '5. En Trabajo / Reparación'),
        ('TERM', '6. Proyecto Terminado'),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='core_servicios_cliente',
    )
    equipo = models.CharField(max_length=150, help_text='Ej: PC Gamer / Sistema Web')
    descripcion_falla = models.TextField(verbose_name='Descripción o requerimiento')
    fecha_agenda = models.DateTimeField(null=True, blank=True, verbose_name='Fecha y hora de cita')
    agenda_aceptada = models.BooleanField(default=False, verbose_name='Cita confirmada')
    costo_estimado = models.PositiveIntegerField(null=True, blank=True, verbose_name='Costo estimado (CLP)')
    tiempo_estimado = models.CharField(max_length=100, blank=True, verbose_name='Tiempo estimado')
    detalle_evaluacion = models.TextField(blank=True, verbose_name='Detalle de la evaluación')
    estado = models.CharField(max_length=4, choices=ESTADOS, default='AGEN', db_index=True)
    fecha_ingreso = models.DateTimeField(auto_now_add=True, db_index=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_ingreso']

    def __str__(self):
        return f'#{self.pk} {self.equipo} — {self.get_estado_display()}'


class MensajeProyecto(models.Model):
    servicio = models.ForeignKey(
        ServicioCliente,
        on_delete=models.CASCADE,
        related_name='core_mensajes',
    )
    emisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='core_mensajes_enviados',
    )
    mensaje = models.TextField(max_length=2000)
    fecha_envio = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['fecha_envio']

    def __str__(self):
        return f'Mensaje de {self.emisor} en servicio #{self.servicio_id}'
