# Desplegar el sitio Django

El panel de administración guarda proyectos en la base de datos; por eso el sitio debe ejecutarse como un **Web Service**, no como un Static Site.

## Configuración en Render

1. Crea un Web Service conectado al repositorio y selecciona Python.
2. Configura el build command como `pip install -r requirements.txt`.
3. Configura el start command como `python manage.py migrate && gunicorn teletraan_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`.
4. Configura `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY` con un valor secreto largo, `DJANGO_ALLOWED_HOSTS` con el host del servicio y `DATABASE_URL` con una base PostgreSQL persistente.
5. Si quieres subir imágenes o videos desde el panel, configura almacenamiento persistente para `MEDIA_ROOT` o un bucket S3 mediante las variables `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`. El disco local efímero del servicio puede perder los archivos al volver a desplegar.
6. Cuando el servicio esté disponible, crea la cuenta del administrador desde la Shell del servicio con `python manage.py createsuperuser`. El formulario público no permite registrar usuarios y acepta únicamente cuentas con permiso de staff.
7. Abre `/accounts/login/`, inicia sesión y agrega tus proyectos. Activa «Publicado» para mostrarlos en la sección pública.

El portal de clientes permanece desactivado (`CUSTOMER_PORTAL_ENABLED = False`): no hay registro ni acceso de clientes disponible. Al preparar esa etapa, configura una base de datos persistente y activa el ajuste para publicar sus rutas.

Configura también `DJANGO_CSRF_TRUSTED_ORIGINS` con los orígenes HTTPS usados por el sitio si el proveedor lo requiere. No publiques el valor de `DJANGO_SECRET_KEY` ni credenciales de base de datos o almacenamiento.

## Desarrollo local

```powershell
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Los archivos locales se guardan en `media/`. `python build_static_site.py` sigue disponible para generar una vista estática de los proyectos incluidos en `content/projects.json`, pero esa salida no incluye login ni panel de administración.
