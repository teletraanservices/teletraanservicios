# Despliegue en Railway

El repositorio está preparado para Railway con Python 3.13, PostgreSQL, WhiteNoise, Gunicorn y una ruta de comprobación en `/health/`. Railway indica que los servicios nuevos deben configurarse desde el panel o su IaC actual; su archivo antiguo `railway.json` ya no se admite en servicios nuevos.

## 1. Conecta el repositorio

En Railway crea un proyecto, elige **Deploy from GitHub repo** y selecciona el repositorio de Teletraan Services. Configura la raíz del servicio como `/`.

## 2. Añade PostgreSQL

Desde el proyecto crea un servicio PostgreSQL llamado `Postgres`. En las variables del servicio web, agrega:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<clave aleatoria generada fuera del repositorio>
DJANGO_HSTS_SECONDS=0
```

Genera `DJANGO_SECRET_KEY` localmente con:

```powershell
.\venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Genera el dominio público desde **Settings → Networking → Generate Domain**. Después configura:

```text
DJANGO_ALLOWED_HOSTS=<dominio-generado>.up.railway.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://<dominio-generado>.up.railway.app
```

Si conectas un dominio propio, agrégalo también a ambas variables, con `https://` solo en `DJANGO_CSRF_TRUSTED_ORIGINS`. La app ya permite el host que Railway usa para sus health checks.

## 3. Ajusta los comandos del servicio web

En **Settings → Build**:

- Builder: Railpack (detección automática).
- Build command: `python manage.py collectstatic --noinput`

En **Settings → Deploy**:

- Pre-deploy command: `python manage.py migrate`
- Start command: `gunicorn teletraan_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
- Healthcheck path: `/health/`
- Restart policy: `On Failure`

La migración se ejecuta antes de activar cada despliegue. El health check valida la app y la conexión a la base de datos antes de cambiar el tráfico.

## 4. Después del primer despliegue

1. Espera a que el servicio quede activo y abre el dominio generado.
2. Crea el administrador desde **Railway → servicio web → Shell** con `python manage.py createsuperuser`.
3. Ejecuta `python manage.py check --deploy` desde la Shell y revisa las advertencias. Mantén `DJANGO_HSTS_SECONDS=0` hasta confirmar que el dominio definitivo y todos sus subdominios usan HTTPS; después configura HSTS.
4. Revisa `/robots.txt` y `/sitemap.xml`, verifica el dominio en Google Search Console y envía el sitemap.
5. Activa y revisa los respaldos de PostgreSQL en Railway.

El sitio queda público al generar el dominio. Que un buscador lo indexe y lo muestre para una búsqueda concreta depende de sus sistemas; el sitemap facilita el descubrimiento, pero no garantiza indexación ni posición.

> Railway dejó obsoleto `railway.json` y señala que los servicios nuevos se configuran en el panel o con su IaC actual. Por eso no hay un archivo de configuración antiguo en este repositorio.
