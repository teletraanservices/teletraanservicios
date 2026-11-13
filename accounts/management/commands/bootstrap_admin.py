import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Crea o actualiza la cuenta administradora usando variables de entorno.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_ADMIN_USERNAME', '').strip()
        email = os.environ.get('DJANGO_ADMIN_EMAIL', '').strip()
        password = os.environ.get('DJANGO_ADMIN_PASSWORD', '')

        if not any((username, email, password)):
            self.stdout.write('No se configuró el administrador inicial; no se hicieron cambios.')
            return
        if not username or not email or not password:
            raise CommandError(
                'Configura DJANGO_ADMIN_USERNAME, DJANGO_ADMIN_EMAIL y '
                'DJANGO_ADMIN_PASSWORD juntos, o elimina las tres variables.'
            )

        user_model = get_user_model()
        user, created = user_model._default_manager.get_or_create(
            **{user_model.USERNAME_FIELD: username},
            defaults={user_model.get_email_field_name(): email},
        )
        user_email_field = user_model.get_email_field_name()
        setattr(user, user_email_field, email)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = 'creada' if created else 'actualizada'
        self.stdout.write(self.style.SUCCESS(f'Cuenta administradora {action}: {username}'))
