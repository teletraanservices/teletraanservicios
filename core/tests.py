import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from core.project_content import load_projects


class StaticPortfolioTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.static_root = self.root / 'static'
        from core.project_content import STATIC_SOURCE_DIR
        shutil.copytree(STATIC_SOURCE_DIR, self.static_root)
        media_dir = self.static_root / 'core' / 'media' / 'projects'
        (media_dir / 'sample.webp').write_bytes(b'test image')
        (media_dir / 'sample.mp4').write_bytes(b'test video')
        self.projects_file = self.root / 'projects.json'

    def write_projects(self, projects):
        self.projects_file.write_text(json.dumps(projects), encoding='utf-8')

    def test_project_manifest_orders_published_items_and_hides_drafts(self):
        self.write_projects([
            {
                'title': 'Segundo',
                'description': 'Segundo proyecto.',
                'image': 'core/media/projects/sample.webp',
                'position': 2,
            },
            {
                'title': 'Borrador',
                'description': 'No publicar.',
                'image': 'core/media/projects/sample.webp',
                'published': False,
            },
            {
                'title': 'Primero',
                'description': 'Primer proyecto.',
                'video_file': 'core/media/projects/sample.mp4',
                'position': 1,
            },
        ])

        projects = load_projects(self.projects_file, self.static_root)

        self.assertEqual([project['title'] for project in projects], ['Primero', 'Segundo'])
        self.assertEqual(projects[0]['video_file'], 'core/media/projects/sample.mp4')

    def test_manifest_rejects_non_https_project_links(self):
        self.write_projects([{
            'title': 'Enlace inseguro',
            'description': 'Enlace que no debe publicarse.',
            'image': 'core/media/projects/sample.webp',
            'project_url': 'http://example.com',
        }])

        with self.assertRaisesMessage(ValueError, 'project_url'):
            load_projects(self.projects_file, self.static_root)

    def test_manifest_rejects_media_outside_the_project_asset_folder(self):
        self.write_projects([{
            'title': 'Ruta inválida',
            'description': 'No permitir rutas arbitrarias.',
            'image': '../secret.jpg',
        }])

        with self.assertRaisesMessage(ValueError, 'Ruta de archivo no permitida'):
            load_projects(self.projects_file, self.static_root)

    def test_public_homepage_has_contacts_but_no_customer_login(self):
        response = self.client.get(reverse('index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'https://wa.me/56966526276')
        self.assertContains(response, 'teletraanservices@gmail.com')
        self.assertContains(response, '@teletraan._services')
        self.assertNotContains(response, '/accounts/login/')
        self.assertNotContains(response, 'Crear cuenta')

    def test_static_build_contains_public_pages_without_database_routes(self):
        from build_static_site import build_site

        self.write_projects([{
            'title': 'Proyecto estático',
            'description': 'Descripción de prueba.',
            'image': 'core/media/projects/sample.webp',
            'project_url': 'https://example.com/proyecto',
        }])
        output_dir = self.root / 'dist'
        stale_auth_script = output_dir / 'static' / 'core' / 'js' / 'auth.js'
        stale_auth_script.parent.mkdir(parents=True)
        stale_auth_script.write_text('stale', encoding='utf-8')
        with (
            patch('core.project_content.PROJECTS_FILE', self.projects_file),
            patch('build_static_site.STATIC_SOURCE_DIR', self.static_root),
            patch('build_static_site.SITE_URL', 'https://example.test'),
        ):
            build_site(output_dir)

        homepage = (output_dir / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Proyecto estático', homepage)
        self.assertIn('https://example.com/proyecto', homepage)
        self.assertIn('https://wa.me/56966526276', homepage)
        self.assertNotIn('/accounts/login/', homepage)
        self.assertTrue((output_dir / 'cookies' / 'index.html').is_file())
        self.assertTrue((output_dir / 'robots.txt').is_file())
        self.assertTrue((output_dir / 'sitemap.xml').is_file())
        self.assertTrue((output_dir / 'static' / 'core' / 'media' / 'projects' / 'sample.webp').is_file())
        self.assertFalse((output_dir / 'static' / 'core' / 'js' / 'auth.js').exists())
        self.assertFalse((output_dir / 'static' / 'core' / 'js' / 'chat.js').exists())
