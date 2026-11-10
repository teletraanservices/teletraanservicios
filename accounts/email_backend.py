import json
from smtplib import SMTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    api_url = 'https://api.resend.com/emails'

    def __init__(
        self,
        fail_silently=None,
        api_key=None,
        *,
        alias=None,
        _ignore_unknown_kwargs=None,
    ):
        backend_options = {
            'alias': alias,
            '_ignore_unknown_kwargs': _ignore_unknown_kwargs,
        }
        if fail_silently is not None:
            backend_options['fail_silently'] = fail_silently
        super().__init__(**backend_options)
        self.api_key = api_key or settings.RESEND_API_KEY

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.api_key:
            raise ImproperlyConfigured('Define RESEND_API_KEY para enviar correos.')

        sent = 0
        for message in email_messages:
            payload = {
                'from': message.from_email,
                'to': message.to,
                'subject': message.subject,
            }
            if message.cc:
                payload['cc'] = message.cc
            if message.bcc:
                payload['bcc'] = message.bcc
            if message.reply_to:
                payload['reply_to'] = message.reply_to

            if message.content_subtype == 'html':
                payload['html'] = message.body
            else:
                payload['text'] = message.body
            for alternative in getattr(message, 'alternatives', ()):
                if alternative.mimetype == 'text/html':
                    payload['html'] = alternative.content

            if message.extra_headers:
                payload['headers'] = message.extra_headers

            request = Request(
                self.api_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Authorization': ' '.join(('Bearer', self.api_key)),
                    'Content-Type': 'application/json',
                },
                method='POST',
            )
            try:
                with urlopen(request, timeout=10) as response:
                    if not 200 <= response.status < 300:
                        raise SMTPException(
                            f'Resend API rechazó el correo (HTTP {response.status}).'
                        )
                    response.read()
            except HTTPError as error:
                raise SMTPException(
                    f'Resend API rechazó el correo (HTTP {error.code}).'
                ) from error
            except URLError as error:
                raise OSError('No se pudo conectar con Resend API.') from error

            sent += 1
        return sent
