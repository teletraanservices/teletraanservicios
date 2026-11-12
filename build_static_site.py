import json
import os
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape


BASE_DIR = Path(__file__).resolve().parent
SITE_URL = os.environ.get('SITE_URL', 'https://teletraanservicios.onrender.com').rstrip('/')
OUTPUT_DIR = BASE_DIR / 'dist'
STATIC_SOURCE_DIR = BASE_DIR / 'core' / 'static'


def build_site(output_dir=OUTPUT_DIR):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teletraan_backend.settings')
    os.environ['DJANGO_DEBUG'] = 'true'
    parsed_site_url = urlsplit(SITE_URL)
    site_host = parsed_site_url.netloc
    if parsed_site_url.scheme != 'https' or not site_host:
        raise ValueError('SITE_URL debe ser una URL HTTPS completa.')
    os.environ.setdefault('DJANGO_ALLOWED_HOSTS', site_host)

    import django
    from django.conf import settings

    django.setup()
    if site_host not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append(site_host)

    from django.template.loader import get_template
    from django.test import RequestFactory
    from core.project_content import load_projects

    output_dir = Path(output_dir)
    static_output = output_dir / 'static'
    output_dir.mkdir(parents=True, exist_ok=True)
    if static_output.exists():
        shutil.rmtree(static_output)
    for asset in (
        Path('core/css/style.css'),
        Path('core/img/teletraan-logo.jpg'),
        Path('core/img/teletraan-mark.png'),
        Path('core/js/cookie-notice.js'),
    ):
        source = STATIC_SOURCE_DIR / asset
        destination = static_output / asset
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    project_media = STATIC_SOURCE_DIR / 'core' / 'media' / 'projects'
    if project_media.is_dir():
        shutil.copytree(project_media, static_output / 'core' / 'media' / 'projects', dirs_exist_ok=True)

    host = site_host
    request = RequestFactory().get('/', HTTP_HOST=host, secure=True)
    context = {
        'projects': load_projects(static_source_dir=STATIC_SOURCE_DIR),
        'request': request,
        'site_url': SITE_URL,
    }
    (output_dir / 'index.html').write_text(
        get_template('core/index.html').render(context),
        encoding='utf-8',
    )

    cookies_request = RequestFactory().get('/cookies/', HTTP_HOST=host, secure=True)
    cookies_context = {'request': cookies_request, 'site_url': SITE_URL}
    cookies_dir = output_dir / 'cookies'
    cookies_dir.mkdir(parents=True, exist_ok=True)
    (cookies_dir / 'index.html').write_text(
        get_template('core/cookies.html').render(cookies_context),
        encoding='utf-8',
    )

    (output_dir / 'robots.txt').write_text(
        f'User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n',
        encoding='utf-8',
    )
    (output_dir / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{escape(SITE_URL)}/</loc></url>'
        '</urlset>',
        encoding='utf-8',
    )
    (output_dir / '404.html').write_text(
        '<!doctype html><html lang="es"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>No encontrado | Teletraan Services</title>'
        '<p>La página que buscas no existe. <a href="/">Volver al inicio</a></p></html>',
        encoding='utf-8',
    )
    return output_dir


if __name__ == '__main__':
    result = build_site()
    project_count = len(json.loads((BASE_DIR / 'content' / 'projects.json').read_text(encoding='utf-8')))
    print(f'Sitio estático generado en {result} ({project_count} proyectos configurados).')
