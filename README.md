# Teletraan Services

Sitio público estático para mostrar servicios, proyectos y datos de contacto de Teletraan Services. La publicación no usa base de datos, cuentas de clientes, chat ni correo automático. Solo las personas con permiso de escritura en el repositorio de GitHub pueden modificar el contenido publicado.

## Probar localmente

Requiere Python 3.13.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-static.txt
python build_static_site.py
python -m http.server 8000 --directory dist
```

Abre `http://127.0.0.1:8000/`. El generador produce `dist/`; esa carpeta es temporal y no se sube a GitHub.

## Publicar y administrar proyectos

Los proyectos se administran desde GitHub, usando tu cuenta personal. En la web de GitHub:

1. Abre `content/projects.json` y pulsa el lápiz para editarlo.
2. Agrega un objeto JSON por proyecto usando el ejemplo de abajo.
3. Para imágenes o videos pequeños, sube el archivo a `core/static/core/media/projects/` mediante **Add file → Upload files**. Respeta los límites: imágenes hasta 10 MB y videos hasta 25 MB.
4. En `image` o `video_file`, escribe la ruta desde `core/static/`. Para videos grandes, usa `video_url` (por ejemplo, un enlace público de YouTube).
5. Guarda los cambios en la rama `main`. Render reconstruye el sitio estático y publica los proyectos marcados `published: true`.

Ejemplo para `content/projects.json`:

```json
[
  {
    "title": "Sitio para mi cliente",
    "description": "Diseño y desarrollo de una página web adaptable.",
    "image": "core/media/projects/sitio-cliente.webp",
    "video_file": "",
    "video_url": "https://www.youtube.com/watch?v=ID_DEL_VIDEO",
    "project_url": "https://ejemplo.cl",
    "published": true,
    "position": 1
  }
]
```

`image`, `video_file`, `video_url` y `project_url` son opcionales, pero cada proyecto debe tener al menos una imagen o un video. Los enlaces deben usar HTTPS. Cambia `published` a `false` para guardar un borrador y usa `position` para ordenar los proyectos.

La página y las imágenes del portafolio son públicas. No subas trabajos privados de clientes, contraseñas ni información personal. El sitio muestra tus enlaces de WhatsApp, correo e Instagram; los visitantes no pueden iniciar sesión ni modificar el contenido.

## Despliegue en Render

Sigue [DEPLOYMENT.md](DEPLOYMENT.md) para crear el servicio de tipo **Static Site**. La configuración de un Web Service Django antiguo no publica este sitio estático.
