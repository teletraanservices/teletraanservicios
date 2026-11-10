# Despliegue en Render

Esta guía configura el proyecto Django en Render con PostgreSQL, archivos estáticos servidos por WhiteNoise y Gunicorn. No subas claves, contraseñas ni archivos `.env` al repositorio.

## 1. Conecta el repositorio y crea PostgreSQL

1. En Render, crea un **PostgreSQL** administrado y un **Web Service** conectado al repositorio `teletraanservices/teletraanservicios`, rama `main`, directorio raíz.
2. Usa el mismo proyecto y región para la base y el servicio web.
3. En las variables del Web Service, agrega `DATABASE_URL` con la **Internal Database URL** de la base PostgreSQL de Render. No uses la URL externa desde el servicio en la misma región.

## 2. Configura el Web Service

En **Settings → Build & Deploy** configura:

- Runtime: Python.
- Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Start command: `gunicorn teletraan_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
- Health Check Path: `/health/`

En el apartado **Pre-Deploy Command**, si está disponible para el plan, configura:

```text
python manage.py migrate
```

Así las migraciones terminan antes de desplegar la nueva versión. Si el plan no ofrece Pre-Deploy Command, ejecuta `python manage.py migrate` desde la Shell del servicio después de respaldar la base y antes de enviar tráfico al código que requiere esas migraciones.

## 3. Variables de entorno

En **Environment** del Web Service configura:

```text
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<clave aleatoria larga y privada>
DJANGO_ALLOWED_HOSTS=<nombre-del-servicio>.onrender.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<nombre-del-servicio>.onrender.com
DJANGO_HSTS_SECONDS=0
DATABASE_URL=<Internal Database URL de PostgreSQL>
```

Render proporciona `RENDER_EXTERNAL_HOSTNAME`; Django lo agrega automáticamente a `ALLOWED_HOSTS`. `DJANGO_ALLOWED_HOSTS` permite definir hosts adicionales de manera explícita. Si usas un dominio propio, agrégalo a `DJANGO_ALLOWED_HOSTS` y agrega su origen con `https://` a `DJANGO_CSRF_TRUSTED_ORIGINS`.

Genera `DJANGO_SECRET_KEY` de forma local sin guardarla en el repositorio:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Mantén `DJANGO_HSTS_SECONDS=0` hasta confirmar que el dominio definitivo y todos los subdominios que correspondan usan HTTPS. Luego configura HSTS con un valor apropiado. No cambies `DJANGO_DEBUG` a verdadero en producción.

## 4. Correo para recuperación de contraseña

La app usa el correo guardado en la cuenta para enviar un enlace temporal de un solo uso. En Render Free los servicios no pueden abrir conexiones salientes en los puertos SMTP 25, 465 y 587 ([límites de Render](https://render.com/docs/free)); por eso la integración recomendada usa la [API HTTPS de Resend](https://resend.com/docs/api-reference/emails/send-email) (puerto 443), no SMTP. Crea una API key, verifica tu dominio y agrega al Web Service:

```text
RESEND_API_KEY=<API key de Resend>
DEFAULT_FROM_EMAIL=Teletraan Services <no-reply@tu-dominio-verificado.cl>
```

Marca `RESEND_API_KEY` como secreta en Render. El remitente debe pertenecer al dominio verificado en el proveedor. En un plan Render que permita SMTP, también se puede dejar `RESEND_API_KEY` sin configurar y usar `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` y `SMTP_USE_TLS=true`. En desarrollo Django imprime el mensaje en la consola; en producción, si falta el proveedor o el remitente verificado, la pantalla de recuperación informa que no se envió ningún enlace. La app reporta los fallos de entrega en lugar de confirmar un envío fallido.

Después de guardar las variables, espera a que Render aplique la configuración y prueba `/accounts/password-reset/` con una cuenta cuyo correo controles. Confirma la recepción (incluida la carpeta de spam) y revisa el registro de envíos del proveedor. También puedes probar el envío desde la Shell de Render con:

```text
python manage.py shell -c "from django.core.mail import send_mail; send_mail('Prueba Teletraan', 'Correo de prueba.', None, ['TU_CORREO_VERIFICADO'])"
```

La recuperación de contraseña envía automáticamente su enlace cuando el formulario se envía, la cuenta está activa y tiene un correo asociado. Para cuentas no encontradas la respuesta es la misma y no revela si ese correo está registrado.

## 5. Después del primer despliegue

1. Espera que Render muestre el servicio como **Live** y prueba `/health/`, `/accounts/login/` y la página pública.
2. Desde la Shell del Web Service crea el administrador con `python manage.py createsuperuser`.
3. Ejecuta `python manage.py check --deploy` y revisa sus advertencias.
4. Revisa `/robots.txt` y `/sitemap.xml`; registra el dominio en Google Search Console y envía el sitemap.
5. Activa y verifica los respaldos de PostgreSQL en Render.

## Portafolio y archivos multimedia

El almacenamiento local de Render puede ser efímero; no dependas de él para conservar imágenes y videos de usuarios. Para medios persistentes configura un bucket S3 compatible (AWS S3, Cloudflare R2 u otro) y agrega estas variables al Web Service:

```text
AWS_STORAGE_BUCKET_NAME=<nombre-del-bucket>
AWS_ACCESS_KEY_ID=<clave-del-bucket>
AWS_SECRET_ACCESS_KEY=<secreto-del-bucket>
AWS_S3_REGION_NAME=<region>
AWS_S3_ENDPOINT_URL=<endpoint-s3-compatible>
AWS_QUERYSTRING_AUTH=true
```

Guarda las credenciales como variables secretas y configura el acceso del bucket según el proveedor. `AWS_QUERYSTRING_AUTH=true` genera enlaces firmados; usa `false` solo si el bucket y sus archivos deben ser públicos. Sin un bucket S3, los medios se guardan en el sistema de archivos local del servicio y pueden perderse al reiniciar o desplegar.

En el panel se puede agregar una imagen JPG, PNG o WebP, un video MP4 o WebM de hasta 100 MB, o un enlace de video. Los enlaces del sitio y del video son opcionales.

El dominio queda disponible al crear el Web Service. Que un buscador indexe el sitio y lo muestre para una búsqueda depende de sus sistemas; el sitemap facilita el descubrimiento, pero no garantiza indexación ni posición.
