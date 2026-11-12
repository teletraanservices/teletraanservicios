from io import BytesIO
import json
import tempfile

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from unittest.mock import MagicMock, patch

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

	@override_settings(MAILERS={
		'default': {
			'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
			'OPTIONS': {'host': ''},
		},
	})
	def test_reset_form_warns_when_production_email_is_not_configured(self):
		response = self.client.get(reverse('password_reset'))

		self.assertContains(response, 'todavía no está habilitada')

	@override_settings(MAILERS={
		'default': {
			'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
			'OPTIONS': {'host': ''},
		},
	})
	def test_unconfigured_smtp_never_claims_a_recovery_email_was_sent(self):
		response = self.client.post(reverse('password_reset'), {'email': self.user.email})

		self.assertEqual(response.status_code, 503)
		self.assertContains(response, 'no se envió ningún enlace', status_code=503)
		self.assertEqual(len(mail.outbox), 0)

	@override_settings(
		MAILERS={
			'default': {
				'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
				'OPTIONS': {'host': 'smtp.example.com'},
			},
		},
		DEFAULT_FROM_EMAIL='no-reply@localhost',
	)
	def test_local_placeholder_sender_is_not_accepted_in_production(self):
		response = self.client.post(reverse('password_reset'), {'email': self.user.email})

		self.assertEqual(response.status_code, 503)
		self.assertContains(response, 'no se envió ningún enlace', status_code=503)

	@override_settings(MAILERS={
		'default': {
			'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
			'OPTIONS': {'host': 'smtp.example.com'},
		},
	})
	@patch('accounts.views.mail.get_connection')
	def test_smtp_connection_failure_is_reported_without_success_redirect(self, get_connection):
		get_connection.return_value.open.side_effect = OSError('SMTP unavailable')

		response = self.client.post(reverse('password_reset'), {'email': self.user.email})

		self.assertEqual(response.status_code, 503)
		self.assertContains(response, 'no se envió ningún enlace', status_code=503)
		get_connection.return_value.close.assert_not_called()

	@override_settings(
		MAILERS={
			'default': {
				'BACKEND': 'accounts.email_backend.ResendEmailBackend',
				'OPTIONS': {'api_key': 'test-api-key'},
			},
		},
		DEFAULT_FROM_EMAIL='Teletraan <no-reply@example.com>',
	)
	@patch('accounts.email_backend.urlopen')
	def test_password_reset_sends_through_resend_https_api(self, urlopen_mock):
		api_response = MagicMock()
		api_response.status = 200
		urlopen_mock.return_value.__enter__.return_value = api_response

		response = self.client.post(reverse('password_reset'), {'email': self.user.email})

		self.assertRedirects(response, reverse('password_reset_done'))
		request = urlopen_mock.call_args.args[0]
		payload = json.loads(request.data)
		self.assertEqual(request.full_url, 'https://api.resend.com/emails')
		self.assertEqual(request.get_header('Authorization'), ' '.join(('Bearer', 'test-api-key')))
		self.assertEqual(payload['from'], 'Teletraan <no-reply@example.com>')
		self.assertEqual(payload['to'], [self.user.email])
		self.assertIn('/accounts/reset/', payload['text'])
		api_response.read.assert_called_once()

	@override_settings(
		MAILERS={
			'default': {
				'BACKEND': 'accounts.email_backend.ResendEmailBackend',
				'OPTIONS': {'api_key': 'test-api-key'},
			},
		},
		DEFAULT_FROM_EMAIL='Teletraan <no-reply@example.com>',
	)
	@patch('accounts.email_backend.urlopen', side_effect=OSError('API unavailable'))
	def test_resend_api_failure_is_reported_instead_of_claiming_success(self, urlopen_mock):
		with self.assertLogs('accounts.views', level='ERROR'):
			response = self.client.post(reverse('password_reset'), {'email': self.user.email})

		self.assertEqual(response.status_code, 503)
		self.assertContains(response, 'no se envió ningún enlace', status_code=503)
		urlopen_mock.assert_called_once()


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

	def test_staff_can_search_and_filter_orders(self):
		matching_service = ServicioCliente.objects.create(
			cliente=self.client_user,
			equipo='Notebook de diseño',
			descripcion_falla='La pantalla no enciende.',
			estado='EVAL',
		)
		ServicioCliente.objects.create(
			cliente=self.client_user,
			equipo='PC de oficina',
			descripcion_falla='Requiere mantenimiento.',
			estado='TERM',
		)
		self.client.force_login(self.admin)

		response = self.client.get(reverse('admin_panel'), {
			'tab': 'ordenes',
			'q': 'Notebook',
			'status': 'EVAL',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, f'#{matching_service.pk} · Notebook de diseño')
		self.assertNotContains(response, 'PC de oficina')
		self.assertEqual(response.context['servicios'].paginator.count, 1)

	def test_invalid_order_date_range_does_not_return_unfiltered_orders(self):
		ServicioCliente.objects.create(
			cliente=self.client_user,
			equipo='Orden que no debe aparecer',
			descripcion_falla='Descripción',
		)
		self.client.force_login(self.admin)

		response = self.client.get(reverse('admin_panel'), {
			'tab': 'ordenes',
			'date_from': '2026-03-20',
			'date_to': '2026-03-01',
		})

		self.assertEqual(response.context['servicios'].paginator.count, 0)
		self.assertContains(response, 'La fecha inicial no puede ser posterior a la fecha final.')
		self.assertNotContains(response, 'Orden que no debe aparecer')

	def test_staff_can_search_clients_and_filter_active_accounts(self):
		self.client_user.first_name = 'Camila'
		self.client_user.save(update_fields=['first_name'])
		User.objects.create_user(username='other-client', password='test-password')
		self.client.force_login(self.admin)

		response = self.client.get(reverse('admin_panel'), {
			'tab': 'clientes',
			'q': 'Camila',
			'active': 'active',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Camila')
		self.assertNotContains(response, 'other-client')
		self.assertEqual(response.context['clientes'].paginator.count, 1)

	def test_staff_can_deactivate_and_reactivate_customer(self):
		self.client.force_login(self.admin)

		response = self.client.post(
			reverse('customer_toggle_active', args=[self.client_user.pk]),
			{'q': 'customer', 'active': 'active', 'clients_page': '1'},
		)
		self.assertRedirects(
			response,
			f"{reverse('admin_panel')}?q=customer&clients_page=1&active=inactive&tab=clientes",
		)
		self.client_user.refresh_from_db()
		self.assertFalse(self.client_user.is_active)

		response = self.client.post(
			reverse('customer_toggle_active', args=[self.client_user.pk]),
			{'q': 'customer', 'active': 'inactive'},
		)
		self.assertEqual(response.status_code, 302)
		self.client_user.refresh_from_db()
		self.assertTrue(self.client_user.is_active)

	def test_staff_cannot_change_another_admin_account_status(self):
		self.client.force_login(self.admin)
		response = self.client.post(
			reverse('customer_toggle_active', args=[self.admin.pk]),
		)

		self.assertEqual(response.status_code, 404)
		self.admin.refresh_from_db()
		self.assertTrue(self.admin.is_active)

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

	@patch('core.views.load_projects')
	def test_homepage_only_shows_published_projects(self, load_projects):
		load_projects.return_value = [{
			'title': 'Visible',
			'description': 'Proyecto publicado.',
			'video_url': 'https://www.youtube.com/watch?v=example',
			'project_url': 'https://example.com/proyecto',
			'video_file': '',
			'image': '',
		}]

		response = self.client.get('/')

		self.assertContains(response, 'Visible')
		self.assertContains(response, 'https://example.com/proyecto')
		self.assertContains(response, 'https://www.youtube.com/watch?v=example')

	def test_homepage_displays_clickable_business_contacts(self):
		response = self.client.get(reverse('index'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'href="https://wa.me/56966526276"')
		self.assertContains(response, 'href="mailto:teletraanservices@gmail.com"')
		self.assertContains(response, 'href="https://www.instagram.com/teletraan._services/"')
		self.assertContains(response, '+56 9 6652 6276')
		self.assertContains(response, '@teletraan._services')

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
