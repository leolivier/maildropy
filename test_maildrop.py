from .maildrop import MailDropReader
from django.test import TestCase
from django.core import mail
from django.conf import settings
from django.utils.html import strip_tags

# change to true to trace all requests to maildrop.cc
TRACE_REQUESTS=True
if TRACE_REQUESTS:
	import http.client as http_client
	import logging
	http_client.HTTPConnection.debuglevel = 1
	logging.basicConfig()
	logging.getLogger().setLevel(logging.DEBUG)
	requests_log = logging.getLogger("requests.packages.urllib3")
	requests_log.setLevel(logging.DEBUG)
	requests_log.propagate = True


maildrop_inbox = 'test-maildrop'
message_test_body = """
<html>
	<header>
		<style>
			body { color: red;}
		</style>
	</header>
	<body>
		<p>This is the test mail body</p>
	</body>
</html>
"""

class MailDropTests(TestCase):

	def setUp(self):
		self.maildrop = MailDropReader(maildrop_inbox)

	def test_ping(self):
		ping_str = "test python maildrop"
		res = self.maildrop.ping(ping_str)
		self.assertEqual(res, f'pong {ping_str}')
		# print(res)

	def send_test_mail(self, subject='test maildrop'):
		self.assertIsNotNone(settings.EMAIL_HOST_USER)
		mail.send_mail(f'{subject}', strip_tags(message_test_body), settings.DEFAULT_FROM_EMAIL,
			recipient_list=[maildrop_inbox], html_message=message_test_body, fail_silently=False)
		self.assertEqual(len(mail.outbox), 1)
		self.assertEqual(mail.outbox[0].subject, subject)

	def test_inbox(self):
		self.send_test_mail('testing inbox')
		msgs = self.maildrop.inbox()
		self.assertEqual(len(msgs), 1)
		msg = msgs[0]
		# print("headerfrom=", msg.headerfrom)
		self.assertEqual(msg.mailfrom, settings.DEFAULT_FROM_EMAIL)

	# def test_filtered_inbox(self):
	# 	subject = 'testing delete'
	# 	self.send_test_mail(subject)
	# 	msgs = self.maildrop.inbox({'subject': subject})
	# 	self.assertCountEqual(msgs, 1)
	# 	msg = msgs[0]
	# 	self.assertEqual(msg.subject, subject)

	def test_status(self):
		self.assertEqual(self.maildrop.status(), 'operational')

	def test_statistics(self):
		blocked, saved = self.maildrop.statistics()
		self.assertGreater(blocked, 1)
		self.assertGreater(saved, 1)

	def test_alias(self):
		alias = self.maildrop.altinbox()
		print('alias=', alias)
		self.assertIsNotNone(alias)

	def test_message(self):
		subject = 'test read message'
		self.send_test_mail(subject)
		msgs = self.maildrop.inbox()

		for m in msgs:
			msg = self.maildrop.message(m.id)
			self.assertIsNotNone(msg)
			self.assertEqual(msg.mailfrom, settings.DEFAULT_FROM_EMAIL)
		
		self.assertIn(subject, [msg.subject for msg in msgs])

	def test_delete_message(self):
		msgs = self.maildrop.inbox()
		nmsgs = len(msgs)
		if nmsgs == 0:
			self.send_test_mail('testing inbox')
			msgs = self.maildrop.inbox()
			nmsgs = len(msgs)
		self.assertGreater(nmsgs, 0)
		msg = msgs[0]
		self.maildrop.delete(msg.id)
		msgs = self.maildrop.inbox()
		self.assertEqual(len(msgs), nmsgs - 1)

		