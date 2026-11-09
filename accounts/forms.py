from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from core.models import MensajeProyecto, PortfolioItem, ServicioCliente


class LoginForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        'inactive': 'Esta cuenta está inactiva. Contacta al administrador.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'username',
            'autofocus': True,
            'placeholder': 'Tu usuario',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'current-password',
            'placeholder': 'Tu contraseña',
            'aria-describedby': 'password-help',
        })
        self.fields['username'].error_messages['required'] = 'Ingresa tu nombre de usuario.'
        self.fields['password'].error_messages['required'] = 'Ingresa tu contraseña.'
        for name in ('username', 'password'):
            if self[name].errors:
                self.fields[name].widget.attrs.update({
                    'class': 'form-control is-invalid',
                    'aria-invalid': 'true',
                    'aria-describedby': f'{name}-error',
                })

    def get_invalid_login_error(self):
        return ValidationError(
            'Usuario o contraseña incorrectos. Verifica tus datos e inténtalo nuevamente.',
            code='invalid_login',
        )


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


class PortfolioItemForm(forms.ModelForm):
    class Meta:
        model = PortfolioItem
        fields = ['title', 'description', 'image', 'video', 'video_url', 'project_url', 'is_published', 'position']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,image/webp'}),
            'video': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'video/mp4,video/webm'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'project_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'position': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
