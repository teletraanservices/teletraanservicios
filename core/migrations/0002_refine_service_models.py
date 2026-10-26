from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(model_name='serviciocliente', old_name='tipo_equipo', new_name='equipo'),
        migrations.RenameField(model_name='serviciocliente', old_name='descripcion_problema', new_name='descripcion_falla'),
        migrations.AlterField(model_name='serviciocliente', name='equipo', field=models.CharField(help_text='Ej: PC Gamer / Sistema Web', max_length=150)),
        migrations.AlterField(model_name='serviciocliente', name='cliente', field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='servicios', to=settings.AUTH_USER_MODEL)),
        migrations.AlterField(model_name='serviciocliente', name='descripcion_falla', field=models.TextField(verbose_name='Descripción o requerimiento')),
        migrations.AlterField(model_name='serviciocliente', name='estado', field=models.CharField(choices=[('AGEN', '1. Agenda / Solicitud Recibida'), ('CONF', '2. Cita Confirmada'), ('EVAL', '3. En Evaluación de Costo'), ('COST', '4. Evaluación de Costo Terminada'), ('EJE', '5. En Trabajo / Reparación'), ('TERM', '6. Proyecto Terminado')], db_index=True, default='AGEN', max_length=4)),
        migrations.AlterField(model_name='serviciocliente', name='costo_estimado', field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Costo estimado (CLP)')),
        migrations.AddField(model_name='serviciocliente', name='fecha_agenda', field=models.DateTimeField(blank=True, null=True, verbose_name='Fecha y hora de cita')),
        migrations.AddField(model_name='serviciocliente', name='agenda_aceptada', field=models.BooleanField(default=False, verbose_name='Cita confirmada')),
        migrations.AddField(model_name='serviciocliente', name='tiempo_estimado', field=models.CharField(blank=True, max_length=100, verbose_name='Tiempo estimado')),
        migrations.AddField(model_name='serviciocliente', name='detalle_evaluacion', field=models.TextField(blank=True, verbose_name='Detalle de la evaluación')),
        migrations.AddField(model_name='serviciocliente', name='fecha_actualizacion', field=models.DateTimeField(auto_now=True)),
        migrations.AlterField(model_name='mensajeproyecto', name='servicio', field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensajes', to='core.serviciocliente')),
        migrations.AlterField(model_name='mensajeproyecto', name='emisor', field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensajes_proyecto', to=settings.AUTH_USER_MODEL)),
        migrations.AlterField(model_name='mensajeproyecto', name='mensaje', field=models.TextField(max_length=2000)),
        migrations.AlterField(model_name='mensajeproyecto', name='fecha_envio', field=models.DateTimeField(auto_now_add=True, db_index=True)),
    ]
