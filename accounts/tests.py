from io import BytesIO
import tempfile

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from core.models import MensajeProyecto, PortfolioItem, ServicioCliente


class LoginExperienceTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='cliente', password='secure-test-password')

	def test_login_page_has_accessible_password_visibility_control(self):
		response = self.client.get('/accounts/login/')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'data-password-toggle')
		self.assertContains(response, 'aria-controls="id_password"')
		self.assertContains(response, 'class="row justify-content-center w-100"')

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
		self.media_dir = tempfile.TemporaryDirectory()
		self.addCleanup(self.media_dir.cleanup)
		self.enterContext(override_settings(MEDIA_ROOT=self.media_dir.name))

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

	def test_staff_can_upload_project_image_and_video_with_links(self):
		image_content = BytesIO()
		Image.new('RGB', (2, 2), color='blue').save(image_content, format='PNG')
		image = SimpleUploadedFile('captura.png', image_content.getvalue(), content_type='image/png')
		video = SimpleUploadedFile('demo.mp4', b'mp4 test content', content_type='video/mp4')
		self.client.force_login(self.admin)

		response = self.client.post(reverse('portfolio_create'), {
			'title': 'Proyecto multimedia',
			'description': 'Captura, video y enlaces del proyecto.',
			'image': image,
			'video': video,
			'video_url': 'https://example.com/demo',
			'project_url': 'https://example.com/proyecto',
			'is_published': 'on',
			'position': '0',
		})

		self.assertRedirects(response, reverse('admin_panel'))
		project = PortfolioItem.objects.get(title='Proyecto multimedia')
		self.assertTrue(project.image.name.endswith('captura.png'))
		self.assertTrue(project.video.name.endswith('demo.mp4'))
		self.assertEqual(project.video_url, 'https://example.com/demo')
		self.assertEqual(project.project_url, 'https://example.com/proyecto')
		self.assertTrue(project.is_published)

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

	def test_staff_panel_loads_orders_and_conversation_history(self):
		service = ServicioCliente.objects.create(
			cliente=self.client_user,
			equipo='Sitio web',
			descripcion_falla='Necesito actualizar el sitio.',
		)
		MensajeProyecto.objects.create(
			servicio=service,
			emisor=self.client_user,
			mensaje='¿Cómo va mi solicitud?',
		)
		self.client.force_login(self.admin)

		response = self.client.get(reverse('admin_panel'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '¿Cómo va mi solicitud?')

	def test_client_dashboard_loads_own_conversation_history(self):
		service = ServicioCliente.objects.create(
			cliente=self.client_user,
			equipo='Sitio web',
			descripcion_falla='Necesito actualizar el sitio.',
		)
		MensajeProyecto.objects.create(
			servicio=service,
			emisor=self.admin,
			mensaje='Ya revisé tu solicitud.',
		)
		self.client.force_login(self.client_user)

		response = self.client.get(reverse('dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Ya revisé tu solicitud.')

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

	def test_staff_can_update_any_order_and_reply_to_its_customer(self):
		service = ServicioCliente.objects.create(
			cliente=self.client_user,
			equipo='Sitio web',
			descripcion_falla='Necesito actualizar el sitio.',
		)
		self.client.force_login(self.admin)

		response = self.client.post(reverse('admin_panel'), {
			'servicio_id': service.pk,
			'estado': 'COST',
			'costo_estimado': '25000',
			'tiempo_estimado': '2 días',
			'agenda_aceptada': 'on',
			'detalle_evaluacion': 'Evaluación completa.',
		})
		self.assertRedirects(response, reverse('admin_panel'))

		response = self.client.post(
			reverse('enviar_mensaje', args=[service.pk]),
			{'mensaje': 'Ya revisé tu solicitud.'},
		)
		self.assertRedirects(response, reverse('admin_panel'))

		service.refresh_from_db()
		self.assertEqual(service.estado, 'COST')
		self.assertEqual(service.costo_estimado, 25000)
		self.assertTrue(service.agenda_aceptada)
		self.assertTrue(MensajeProyecto.objects.filter(
			servicio=service,
			emisor=self.admin,
			mensaje='Ya revisé tu solicitud.',
		).exists())
