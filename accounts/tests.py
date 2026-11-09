from django.contrib.auth.models import User
from django.test import TestCase

from core.models import PortfolioItem


class LoginExperienceTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='cliente', password='secure-test-password')

	def test_login_page_has_accessible_password_visibility_control(self):
		response = self.client.get('/accounts/login/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'data-password-toggle')
		self.assertContains(response, 'aria-controls="id_password"')

	def test_invalid_credentials_show_clear_error(self):
		response = self.client.post('/accounts/login/', {
			'username': self.user.username,
			'password': 'incorrecta',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Usuario o contraseña incorrectos.')
		self.assertNotIn('_auth_user_id', self.client.session)

	def test_empty_login_fields_show_spanish_errors(self):
		response = self.client.post('/accounts/login/', {})

		self.assertContains(response, 'Ingresa tu nombre de usuario.')
		self.assertContains(response, 'Ingresa tu contraseña.')

	def test_valid_credentials_log_user_in(self):
		response = self.client.post('/accounts/login/', {
			'username': self.user.username,
			'password': 'secure-test-password',
		})

		self.assertRedirects(response, '/accounts/dashboard/')
		self.assertIn('_auth_user_id', self.client.session)


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
