from django.http import HttpResponse
from django.db import DatabaseError, connection
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET
from xml.sax.saxutils import escape

def index_view(request):
    return render(request, 'core/index.html')


def cookies_view(request):
    return render(request, 'core/cookies.html')


@require_GET
def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse('sitemap'))
    body = f"User-agent: *\nAllow: /\nDisallow: /accounts/\nDisallow: /admin/\nSitemap: {sitemap_url}\n"
    return HttpResponse(body, content_type='text/plain; charset=utf-8')


@require_GET
def sitemap_xml(request):
    homepage = escape(request.build_absolute_uri(reverse('index')))
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{homepage}</loc></url>'
        '</urlset>'
    )
    return HttpResponse(body, content_type='application/xml; charset=utf-8')


@require_GET
def health_check(request):
    try:
        connection.ensure_connection()
    except DatabaseError:
        return HttpResponse('unhealthy', status=503, content_type='text/plain')
    return HttpResponse('ok', content_type='text/plain')
