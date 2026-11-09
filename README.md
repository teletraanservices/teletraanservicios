# Teletraan Services

Plataforma web de Teletraan Services construida con Django. Incluye páginas públicas de servicios y portafolio, cuentas de clientes, solicitudes y conversaciones, además de un panel de administración para gestionar proyectos publicados.

## Desarrollo local

Requiere Python 3.13.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`. Para la configuración local opcional, copia `.env.example` a `.env` y completa los valores. No publiques `.env` ni credenciales.

## Despliegue en Render

La guía para configurar el Web Service, PostgreSQL, variables, comandos de despliegue, correo y dominio en Render está en [DEPLOYMENT.md](DEPLOYMENT.md). Conecta Render al repositorio de GitHub y despliega desde la rama `main`.

El proyecto ofrece `/health/` para la comprobación de estado y los endpoints `/robots.txt` y `/sitemap.xml` para buscadores. La disponibilidad, el dominio y la indexación dependen de la configuración de Render y de los buscadores.
