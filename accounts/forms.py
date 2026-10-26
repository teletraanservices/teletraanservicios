from django import forms
from core.models import MensajeProyecto, ServicioCliente


class SolicitudServicioForm(forms.ModelForm):
    class Meta:
        model = ServicioCliente
        fields = ['equipo', 'descripcion_falla']
        widgets = {
            'equipo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Notebook, PC gamer o sitio web'}),
            'descripcion_falla': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Cuéntanos qué necesitas'}),
        }


class MensajeProyectoForm(forms.ModelForm):
    class Meta:
        model = MensajeProyecto
        fields = ['mensaje']
        widgets = {'mensaje': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'maxlength': 2000, 'placeholder': 'Escribe un mensaje…'})}


class ActualizarServicioForm(forms.ModelForm):
    class Meta:
        model = ServicioCliente
        fields = ['estado', 'costo_estimado', 'tiempo_estimado', 'agenda_aceptada', 'detalle_evaluacion']
        widgets = {
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'costo_estimado': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'tiempo_estimado': forms.TextInput(attrs={'class': 'form-control'}),
            'agenda_aceptada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'detalle_evaluacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
