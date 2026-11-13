from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth.forms import SetPasswordForm as DjangoSetPasswordForm
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from core.models import (
    MAX_PORTFOLIO_IMAGES,
    MensajeProyecto,
    PortfolioItem,
    ServicioCliente,
    validate_portfolio_file_size,
)


class MultipleImageInput(forms.FileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleImageInput

    def __init__(self, *args, **kwargs):
        self.uploaded_images = []
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        self.uploaded_images = []
        if data in self.empty_values:
            return super().clean(data, initial)

        uploads = list(data) if isinstance(data, (list, tuple)) else [data]
        if len(uploads) > MAX_PORTFOLIO_IMAGES:
            raise ValidationError(f'Puedes subir un máximo de {MAX_PORTFOLIO_IMAGES} imágenes por proyecto.')

        self.uploaded_images = uploads
        cleaned_uploads = [super(MultipleImageField, self).clean(upload) for upload in uploads]
        return cleaned_uploads[0]


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(
        required=False,
        label='Mantener mi sesión iniciada durante 30 días',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

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

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        from django.conf import settings
        if not settings.CUSTOMER_PORTAL_ENABLED and not user.is_staff:
            raise self.get_invalid_login_error()


class PasswordResetForm(DjangoPasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'email',
            'autofocus': True,
            'placeholder': 'nombre@correo.com',
        })

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = loader.render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)
        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_body = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_body, 'text/html')
        email_message.send()


class SetPasswordForm(DjangoSetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('new_password1', 'new_password2'):
            self.fields[name].widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'new-password',
                'placeholder': 'Ingresa una contraseña segura',
                'data-password-input': '',
            })


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


class AdminOrderFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        max_length=100,
        label='Buscar órdenes',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'N.º de orden, cliente o descripción',
        }),
    )
    status = forms.ChoiceField(
        required=False,
        label='Estado',
        choices=[('', 'Todos los estados'), *ServicioCliente.ESTADOS],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    date_from = forms.DateField(
        required=False,
        label='Desde',
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    date_to = forms.DateField(
        required=False,
        label='Hasta',
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError('La fecha inicial no puede ser posterior a la fecha final.')
        return cleaned_data


class AdminClientFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        max_length=100,
        label='Buscar clientes',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre, usuario o correo',
        }),
    )
    active = forms.ChoiceField(
        required=False,
        label='Estado de cuenta',
        choices=[('', 'Todas las cuentas'), ('active', 'Activas'), ('inactive', 'Desactivadas')],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class PortfolioItemForm(forms.ModelForm):
    image = MultipleImageField(
        required=False,
        label='Imágenes del proyecto',
        help_text=(
            'Selecciona hasta 10 imágenes JPG, PNG o WebP (máximo 100 MB cada una). '
            'La primera será la portada. Al editar, subir imágenes nuevas reemplaza la galería actual.'
        ),
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']),
            validate_portfolio_file_size,
        ],
    )

    class Meta:
        model = PortfolioItem
        fields = ['title', 'description', 'image', 'video', 'video_url', 'project_url', 'is_published', 'position']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'image': MultipleImageInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/png,image/webp'}),
            'video': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'video/mp4,video/webm'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'project_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'position': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
