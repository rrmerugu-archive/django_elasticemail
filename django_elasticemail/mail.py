from __future__ import unicode_literals

import six
import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address
from django.utils.encoding import force_text
import logging
logger = logging.getLogger(__name__)
from requests.packages.urllib3.filepost import encode_multipart_formdata

__version__ = '0.0.1'
version = __version__

"""
https://elasticemail.com/api-documentation/send
https://elasticemail.com/support/http-api

"""

# A mapping of smtp headers to API key names, along
# with a callable to transform them somehow (if nec.)
#
# https://documentation.mailgun.com/user_manual.html#sending-via-smtp
# https://documentation.mailgun.com/api-sending.html#sending
#
# structure is SMTP_HEADER: (api_name, data_transform_function)
HEADERS_MAP = {
    'Content-type': 'application/x-www-form-urlencoded',
    'Accept': 'text/plain'
}


class ElasticEmailAPIError(Exception):
    pass


class ElasticEmailBackend(BaseEmailBackend):
    """A Django Email backend that uses mailgun.
    """

    def __init__(self, fail_silently=False, *args, **kwargs):
        api_key, username = (kwargs.pop('api_key', None),
                                   kwargs.pop('username', None))

        super(ElasticEmailBackend, self).__init__(
            fail_silently=fail_silently,
            *args, **kwargs)

        try:
            self._api_key = api_key or getattr(settings, 'ELASTICEMAIL_API_KEY')
            self._username = username or getattr(settings, 'ELASTICEMAIL_USERNAME')

        except AttributeError:
            if fail_silently:
                self._api_key, self._username = None
            else:
                raise

        self._api_url = "https://api.elasticemail.com/mailer/send"
        self._headers_map = HEADERS_MAP

    def open(self):
        """Stub for open connection, all sends are done over HTTP POSTs
        """
        pass

    def close(self):
        """Close any open HTTP connections to the API server.
        """
        pass

    def _map_smtp_headers_to_api_parameters(self, email_message):
        """
        Map the values passed in SMTP headers to API-ready
        2-item tuples present in HEADERS_MAP

        header values must be a single string or list or tuple of strings

        :return: 2-item tuples of the form (api_name, api_values)
        """
        api_data = []
        for smtp_key, api_transformer in six.iteritems(self._headers_map):
            data_to_transform = email_message.extra_headers.pop(smtp_key, None)
            if data_to_transform is not None:
                if isinstance(data_to_transform, (list, tuple)):
                    # map each value in the tuple/list
                    for data in data_to_transform:
                        api_data.append((api_transformer[0], api_transformer[1](data)))
                elif isinstance(data_to_transform, dict):
                    for data in six.iteritems(data_to_transform):
                        api_data.append(api_transformer(data))
                else:
                    # we only have one value
                    api_data.append((api_transformer[0], api_transformer[1](data_to_transform)))
        return api_data

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        from_email = sanitize_address(email_message.from_email, email_message.encoding)

        to_recipients = [sanitize_address(addr, email_message.encoding)
                      for addr in email_message.to]

        try:
            post_data = []
            post_data.append(('to', (",".join(to_recipients)),))
            if email_message.bcc:
                bcc_recipients = [sanitize_address(addr, email_message.encoding) for addr in email_message.bcc]
                post_data.append(('bcc', (",".join(bcc_recipients)),))
            if email_message.cc:
                cc_recipients = [sanitize_address(addr, email_message.encoding) for addr in email_message.cc]
                post_data.append(('cc', (",".join(cc_recipients)),))
            post_data.append(('text', email_message.body,))
            post_data.append(('subject', email_message.subject,))
            post_data.append(('from', from_email,))

            # get our recipient variables if they were passed in
            recipient_variables = email_message.extra_headers.pop('recipient_variables', None)
            if recipient_variables is not None:
                post_data.append(('recipient-variables', recipient_variables, ))

            for name, value in self._map_smtp_headers_to_api_parameters(email_message):
                post_data.append((name, value, ))

            if hasattr(email_message, 'alternatives') and email_message.alternatives:
                for alt in email_message.alternatives:
                    if alt[1] == 'text/html':
                        post_data.append(('html', alt[0],))
                        break
            if hasattr(email_message, 'template') and email_message.template:
                post_data.append(('template', email_message.template,))

                # not delete the 'alternatives', 'text'




            if hasattr(email_message,'merge_vars') and email_message.merge_vars:
                for k, v in email_message.merge_vars.iteritems():
                    post_data.append(('merge_%s'% k, v))



            logger.debug(post_data)
            # Map Reply-To header if present
            try:
                if email_message.reply_to:
                    post_data.append((
                        "h:Reply-To",
                        ", ".join(map(force_text, email_message.reply_to)),
                    ))
            except AttributeError:
                pass

            if email_message.attachments:
                for attachment in email_message.attachments:
                    post_data.append(('attachment', (attachment[0], attachment[1],)))
                content, header = encode_multipart_formdata(post_data)
                headers = {'Content-Type': header,
                           'username': self._username,
                           'api_key': self._api_url
                           }
            else:
                content = post_data
                headers = None
            logger.debug('###=======')
            logger.debug(content)
            logger.debug(headers)

            response = requests.post(self._api_url ,
                    auth=("api", self._api_key),
                    data=content, headers=headers)

            logger.debug(response.status_code)
            logger.debug(response.text)
            email_response = response.text
            logger.debug('#=======')
        except:
            if not self.fail_silently:
                raise
            return False, email_response

        if response.status_code != 200:
            if not self.fail_silently:
                raise ElasticEmailAPIError(response)
            return False, email_response

        return True, email_response

    def send_messages(self, email_messages):
        """Sends one or more EmailMessage objects and returns the number of
        email messages sent.
        """
        if not email_messages:
            return

        num_sent = 0
        for message in email_messages:
            if self._send(message):
                num_sent += 1

        return num_sent