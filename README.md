# Teletraan Services

Plataforma web de Teletraan Services construida con Django. Incluye páginas públicas de servicios, cuentas de clientes, solicitudes de proyectos y un panel de administración.

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

## Despliegue en Railway

La guía de configuración de PostgreSQL, variables, comandos de despliegue y dominio está en [DEPLOYMENT.md](DEPLOYMENT.md). Railway debe conectarse al repositorio de GitHub y desplegar desde la rama `main`.

El proyecto ofrece `/health/` para la comprobación de estado y los endpoints `/robots.txt` y `/sitemap.xml` para buscadores. La disponibilidad continua, el dominio y la indexación dependen de la configuración y operación de Railway y de los buscadores.
