from django.contrib.auth.models import User
from django.test import TestCase

from core.models import PortfolioItem


class PortfolioAccessTests(TestCase):
	def setUp(self):
		self.admin = User.objects.create_user(username='owner', password='test-password', is_staff=True)
		self.client_user = User.objects.create_user(username='customer', password='test-password')

	def test_staff_can_open_portfolio_form(self):
		self.client.force_login(self.admin)

		response = self.client.get('/accounts/portfolio/nuevo/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'enctype="multipart/form-data"')

	def test_staff_can_publish_project(self):
		self.client.force_login(self.admin)
		response = self.client.post('/accounts/portfolio/nuevo/', {
			'title': 'Sitio de muestra',
			'description': 'Diseño y desarrollo web.',
			'video_url': 'https://www.youtube.com/watch?v=example',
			'project_url': 'https://example.com',
			'is_published': 'on',
			'position': '0',
		})

		self.assertRedirects(response, '/accounts/admin-panel/')
		self.assertTrue(PortfolioItem.objects.filter(title='Sitio de muestra', is_published=True).exists())

	def test_customer_cannot_manage_portfolio(self):
		self.client.force_login(self.client_user)
		response = self.client.post('/accounts/portfolio/nuevo/', {
			'title': 'Proyecto no autorizado',
			'description': 'No debería guardarse.',
			'video_url': 'https://www.youtube.com/watch?v=example',
			'is_published': 'on',
			'position': '0',
		})

		self.assertNotEqual(response.status_code, 200)
		self.assertFalse(PortfolioItem.objects.filter(title='Proyecto no autorizado').exists())

	def test_homepage_only_shows_published_projects(self):
		PortfolioItem.objects.create(
			title='Visible',
			description='Proyecto publicado.',
			video_url='https://www.youtube.com/watch?v=example',
			is_published=True,
		)
		PortfolioItem.objects.create(
			title='Privado',
			description='Borrador interno.',
			video_url='https://www.youtube.com/watch?v=example',
			is_published=False,
		)

		response = self.client.get('/')

		self.assertContains(response, 'Visible')
		self.assertNotContains(response, 'Privado')
