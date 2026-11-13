from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET
from xml.sax.saxutils import escape
from .models import PortfolioItem

def index_view(request):
    proyectos = PortfolioItem.objects.filter(is_published=True).prefetch_related('gallery_images')
    site_url = f'{request.scheme}://{request.get_host()}'
    return render(request, 'core/index.html', {
        'projects': proyectos,
        'site_url': site_url,
    })


def cookies_view(request):
    return render(request, 'core/cookies.html', {
        'site_url': f'{request.scheme}://{request.get_host()}',
    })


@require_GET
def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse('sitemap'))
    body = f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n"
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
def health_check(_request):
    return HttpResponse('ok', content_type='text/plain')
