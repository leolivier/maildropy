from maildropy import MailDropReader
from email.message import EmailMessage
from dotenv import load_dotenv
import re, os, random, string, time, logging, smtplib, sys
from datetime import datetime
import http.client as http_client
import pytest

# change to true to trace all requests to maildrop.cc
TRACE_REQUESTS=False

def trace_requests():
	http_client.HTTPConnection.debuglevel = 1
	logging.basicConfig()
	logging.getLogger().setLevel(logging.DEBUG)
	requests_log = logging.getLogger("requests.packages.urllib3")
	requests_log.setLevel(logging.DEBUG)
	requests_log.propagate = True

def strip_tags(raw_html):
  cleanr = re.compile(r'<.*?>')
  cleantext = re.sub(cleanr, '', raw_html)
  return cleantext

def compress(raw_html):
	comprsr = re.compile(r'\s+') #remove all spaces
	compressed = re.sub(comprsr, '', raw_html)
	return compressed

class ParamsForTestingMaildropy:
	# define the number of messages sent and tested in the scenario
	nb_msgs_to_test_with=3
	# number max of seconds to wait before mails are received
	receive_timeout=450
	# delay between retries
	delay_between_receive_retries=5
	# templates for the test emails
	subject_template="test maildrop message #%s"
	body_template="""
<html>
	<header>
		<style>
			body {{ color: red;}}
		</style>
	</header>
	<body>
		<h1>Test maildropy on inbox %s</h1>
		<p>This is the test mail body #%s</p>
	</body>
</html>
"""

@pytest.fixture(scope="class")
def getenv():
	load_dotenv()
	return os.environ

@pytest.fixture(scope="class")
def trace_requests_if_needed():
	if TRACE_REQUESTS: trace_requests()

@pytest.fixture(scope="class")
def params(getenv):
		return ParamsForTestingMaildropy()

@pytest.fixture(scope="class")
def maildrop_reader(getenv):
		return MailDropReader(getenv['MAILDROP_INBOX'])

def send_test_mail(params, getenv):
	# get a timestamped email subject and body
	# id = ''.join(random.choice(string.digits) for _ in range(8))
	id = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
	subject = params.subject_template % id
	body = params.body_template % (getenv['MAILDROP_INBOX'], id)
	print(f"subject: {subject}, body: ***{body}***")
	# build a message
	txt_body = strip_tags(body)
	msg = EmailMessage()
	msg.set_content(txt_body)
	msg['Subject'] = subject
	msg['From'] = getenv['FROM_ADDRESS']
	inbox = getenv['MAILDROP_INBOX']
	msg['To'] = f'{inbox}@maildrop.cc'
	msg.add_alternative(body, subtype='html')
	# create an smtp server (ssl or not)
	if getenv['SMTP_SSL_MODE'] == 'SSL':
		s = smtplib.SMTP_SSL(getenv['SMTP_HOST'], getenv['SMTP_PORT'])
	else: 
		s = smtplib.SMTP(getenv['SMTP_HOST'], getenv['SMTP_PORT'])
	if getenv['SMTP_SSL_MODE'] == 'STARTLS':
		s.starttls()
	# login to the SMTP server
	s.login(getenv['SMTP_USERNAME'], getenv['SMTP_PASSWORD'])
	# and send the message
	s.send_message(msg)
	# finally quit
	s.quit()
	return (subject, compress(body))

@pytest.fixture(scope="class")
def send_mails(params, getenv, maildrop_reader):
	# delete sent mails not deleted before starting sending new ones
	# WARNING!!! As we don't master at all how much time it takes to gmail to actually
	# send the emails, we don't know if we will receive new emails after this action
	for msg in maildrop_reader.inbox(): maildrop_reader.delete(msg.id)

	sent_mails = []
	for _ in range(params.nb_msgs_to_test_with):
		sent_mails.append(send_test_mail(params, getenv))
		time.sleep(1)  # rate limiting?

		time_to_wait = params.receive_timeout
		while True:
			assert time_to_wait >= 0, "timeout while waiting for emails arrival"
			sys.stdout.write('*')
			sys.stdout.flush()
			msgs = maildrop_reader.inbox()
			if len(msgs) == params.nb_msgs_to_test_with:
				break
			time.sleep(params.delay_between_receive_retries) # wait before retrying
			time_to_wait -= params.delay_between_receive_retries

		yield sent_mails

		# delete sent mails not deleted before
		# WARNING!!! As we don't master at all how much time it takes to gmail to actually
		# send the emails, we don't know if we will receive new emails after this action
		for msg in maildrop_reader.inbox(): maildrop_reader.delete(msg.id)

class TestMaildropy:

	@pytest.fixture(autouse=True, scope="class")
	def setup(self, trace_requests_if_needed, send_mails):
		pass

	def test_ping(self, maildrop_reader):
		ping_str = "test python maildrop"
		res = maildrop_reader.ping(ping_str)
		assert res == f'pong {ping_str}', f'unexpected pong: {res}'

	def test_inbox(self, maildrop_reader, params):
		msgs = maildrop_reader.inbox()
		assert len(msgs) == params.nb_msgs_to_test_with, f'unexpected number of messages: {len(msgs)}'
		msg = msgs[0]
		assert msg.mailfrom == getenv['FROM_ADDRESS'], f'unexpected sender: {msg.mailfrom}'

	# DOES NOT WORK CURRENTLY
	# def test_filtered_inbox(self, maildrop_reader, send_mails):
	# 	msgs = maildrop_reader.inbox({'subject': self.subjects[0]})
	# 	assert len(msgs) == 1
	# 	msg = msgs[0]
	# 	assert msg.subject == self.subjects[0]
	# 	assert msg.html == self.bodies[0]

	def test_status(self, maildrop_reader):
		status = maildrop_reader.status()
		assert status == 'operational', "maildrop status not operational"

	def test_statistics(self, maildrop_reader):
		blocked, saved = maildrop_reader.statistics()
		assert blocked >= 1, f'unexpected stat: blocked = {blocked}'
		assert saved >= 1, f'unexpected stat: saved = {saved}'

	def test_alias(self, maildrop_reader):
		alias = maildrop_reader.altinbox()
		assert alias is not None, "alias not given by maildrop"


	def test_read_messages(self, maildrop_reader, params, getenv, send_mails):
		sent_mails = send_mails
		msgs = maildrop_reader.inbox()
		for m in msgs:
			msg = maildrop_reader.message(m.id)
			assert msg is not None, "null msg"
			assert msg.mailfrom == getenv['FROM_ADDRESS'], f"msg not sent by right sender: {msg.mailfrom}"
			assert msg.subject in sent_mails.subjects, f"unexpected msg subject: {msg.subject}"
			assert compress(msg.html) in sent_mails.bodies, f"unexpected msg content: ***{msg.html}***"

	def test_delete_messages(self, maildrop_reader, params):
		msgs = maildrop_reader.inbox()
		nbdel = 0
		for msg in msgs:
			assert maildrop_reader.delete(msg.id) == True, f"can't delete message #{msg.id} with subject {msg.subject}"
			nbdel += 1

		assert nbdel == params.nb_msgs_to_test_with, f"{nbdel} messages deleted, exepected {params.nb_msgs_to_test_with}"

		msgs = maildrop_reader.inbox()
		assert len(msgs) == 0, f"all messages should have been deleted"

