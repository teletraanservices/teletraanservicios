from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

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

	def test_remember_me_keeps_session_for_thirty_days(self):
		self.client.post('/accounts/login/', {
			'username': self.user.username,
			'password': 'secure-test-password',
			'remember_me': 'on',
		})

		self.assertEqual(self.client.session.get_expiry_age(), 30 * 24 * 60 * 60)

	def test_session_expires_when_browser_closes_by_default(self):
		self.client.post('/accounts/login/', {
			'username': self.user.username,
			'password': 'secure-test-password',
		})

		self.assertTrue(self.client.session.get_expire_at_browser_close())


class PasswordResetExperienceTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username='cliente',
			email='cliente@example.com',
			password='secure-test-password',
		)

	@override_settings(MAILERS={
		'default': {
			'BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
			'OPTIONS': {},
		},
	})
	def test_password_reset_sends_one_time_link_and_changes_password(self):
		response = self.client.post(reverse('password_reset'), {'email': self.user.email})

		self.assertRedirects(response, reverse('password_reset_done'))
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('Instrucciones para recuperar tu contraseña', mail.outbox[0].subject)

		reset_path = mail.outbox[0].body.split('http://testserver', 1)[1].splitlines()[0]
		response = self.client.get(reset_path, follow=True)
		self.assertContains(response, 'Crea una contraseña nueva')

		response = self.client.post(response.request['PATH_INFO'], {
			'new_password1': 'another-secure-password',
			'new_password2': 'another-secure-password',
		})

		self.assertRedirects(response, reverse('password_reset_complete'))
		self.user.refresh_from_db()
		self.assertTrue(self.user.check_password('another-secure-password'))

	@override_settings(MAILERS={
		'default': {
			'BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
			'OPTIONS': {},
		},
	})
	def test_unknown_email_gets_same_confirmation_without_sending_mail(self):
		response = self.client.post(reverse('password_reset'), {'email': 'unknown@example.com'})

		self.assertRedirects(response, reverse('password_reset_done'))
		self.assertEqual(len(mail.outbox), 0)
		self.assertContains(self.client.get(reverse('password_reset_done')), 'Si existe una cuenta activa')


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
