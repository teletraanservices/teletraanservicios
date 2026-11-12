# Despliegue estático en Render

El sitio público se genera durante el build y se sirve como archivos estáticos. No requiere PostgreSQL, Shell de pago, contraseña de administrador, API de correo ni un servidor Django en producción.

## Crear el Static Site

1. En Render, elige **New → Static Site** y conecta `teletraanservices/teletraanservicios`, rama `main`.
2. Configura el directorio raíz como la raíz del repositorio.
3. Usa estos valores:

   - **Build Command:** `pip install -r requirements-static.txt && python build_static_site.py`
   - **Publish Directory:** `dist`
4. En **Environment**, configura `SITE_URL` con la URL HTTPS pública asignada al nuevo Static Site, por ejemplo `https://nombre-del-sitio.onrender.com`.
5. Activa los despliegues automáticos desde `main`.
6. Espera el estado **Live** y prueba `/`, `/cookies/`, `/robots.txt` y `/sitemap.xml`.

No agregues `DATABASE_URL`, `DJANGO_SECRET_KEY`, `RESEND_API_KEY` ni variables SMTP: el sitio estático no las utiliza. El build no ejecuta migraciones ni consultas a una base de datos.

## Servicio Django anterior

El Web Service Django anterior es independiente del nuevo Static Site. Manténlo hasta verificar que el Static Site funciona; luego puedes detenerlo desde Render para evitar servir dos versiones. El nuevo Static Site tendrá su propia URL `onrender.com`. Sin un dominio propio, no se puede conservar exactamente la URL anterior del Web Service en ambos servicios a la vez.

La versión estática no incluye rutas de cuentas, inicio de sesión, solicitudes, conversaciones, panel Django ni recuperación de contraseña. El acceso de edición es el control de permisos de GitHub sobre el repositorio: solo las cuentas con permiso de escritura pueden publicar cambios.

## Editar el portafolio

El archivo `content/projects.json` contiene los proyectos. Sube medios pequeños a `core/static/core/media/projects/` y edita el JSON en GitHub. Cada commit en `main` inicia un nuevo build. Las rutas de imagen y video parten de `core/static/`; imágenes de hasta 10 MB y videos de hasta 25 MB se aceptan. Para videos más grandes, publica el video en un servicio externo y agrega su URL HTTPS a `video_url`.

La carpeta `dist/` se genera en cada build y está excluida del repositorio. El contenido en el portafolio es público; publica únicamente material que tengas permiso de mostrar.

## Pruebas y vista previa local

```powershell
pip install -r requirements-static.txt
python manage.py test core.tests
python build_static_site.py
python -m http.server 8000 --directory dist
```

Abre `http://127.0.0.1:8000/` para revisar la vista previa. El archivo `SITE_URL` configura enlaces canónicos y el sitemap del sitio publicado; localmente puede apuntar a la URL pública hasta que el servicio de Render esté creado.
