# Teletraan Services

Sitio Django para mostrar servicios y proyectos de Teletraan Services. Los visitantes pueden ver el portafolio y contactar al negocio; el acceso al panel y la publicación de proyectos quedan reservados a cuentas administrativas.

## Ejecutar localmente

Requiere Python 3.13.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`. Para administrar los proyectos, inicia sesión en `/accounts/login/`; desde el panel puedes agregar, editar, publicar como borrador y eliminar proyectos. Cada proyecto admite título, descripción, enlace e imágenes o videos opcionales.

El portal de clientes (registro, acceso y solicitudes) está desactivado en `CUSTOMER_PORTAL_ENABLED`. El modelo y las vistas existentes se conservan para retomarlos cuando el portal dinámico esté listo.

## Publicar el sitio

El inicio de sesión y el panel requieren un **servicio web Django**. Un Static Site solo puede servir archivos y no permite iniciar sesión ni guardar proyectos desde la página. Consulta [DEPLOYMENT.md](DEPLOYMENT.md) para configurar el servicio, la base de datos y el almacenamiento de archivos.

Las imágenes, descripciones y enlaces publicados son visibles para cualquiera. Sube únicamente contenido que tengas permiso de mostrar.
