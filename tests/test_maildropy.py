
from maildropy import MailDropReader
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import re, os, random, string

# change to true to trace all requests to maildrop.cc
TRACE_REQUESTS=False
if TRACE_REQUESTS:
	import http.client as http_client
	import logging
	http_client.HTTPConnection.debuglevel = 1
	logging.basicConfig()
	logging.getLogger().setLevel(logging.DEBUG)
	requests_log = logging.getLogger("requests.packages.urllib3")
	requests_log.setLevel(logging.DEBUG)
	requests_log.propagate = True

load_dotenv()

def generate_random_string(length):
    return ''.join(random.choice(string.digits) for _ in range(length))

def do(func, *args):
	if not callable(func):
		raise ValueError(f"{func.name} is not callable")
	print(f">>> running test {func.__name__} with args: {args}")
	res = func(*args) if len(args) > 0 else func()
	print(f"<<< end test {func.__name__} with result: {res}")

def strip_tags(raw_html):
  cleanr = re.compile('<.*?>')
  cleantext = re.sub(cleanr, '', raw_html)
  return cleantext

maildrop_inbox = os.environ['MAILDROP_INBOX']
message_test_body = f"""
<html>
	<header>
		<style>
			body {{ color: red;}}
		</style>
	</header>
	<body>
		<h1>Test maildropy on inbox {maildrop_inbox}</h1>
		<p>This is the test mail body #{generate_random_string(8)}</p>
	</body>
</html>
"""
txt_message_test_body = strip_tags(message_test_body)

def send_test_mail(subject='test maildrop'):
	msg = EmailMessage()
	msg.set_content(txt_message_test_body)
	msg['Subject'] = subject
	msg['From'] = os.environ['FROM_ADDRESS']
	msg['To'] = f'{maildrop_inbox}@maildrop.cc'
	msg.add_alternative(message_test_body, subtype='html')
	if os.environ['SMTP_SSL_MODE'] == 'SSL':
		s = smtplib.SMTP_SSL(os.environ['SMTP_HOST'], os.environ['SMTP_PORT'])
	else: 
		s = smtplib.SMTP(os.environ['SMTP_HOST'], os.environ['SMTP_PORT'])
	if os.environ['SMTP_SSL_MODE'] == 'STARTLS':
		s.starttls()
	s.login(os.environ['SMTP_USERNAME'], os.environ['SMTP_PASSWORD'])
	s.send_message(msg)
	s.quit()

reader = MailDropReader(maildrop_inbox)

def test_ping():
	ping_str = "test python maildrop"
	res = reader.ping(ping_str)
	assert res == f'pong {ping_str}', f'unexpected pong: {res}'
	return res

def test_inbox(nbmsgs):
	msgs = reader.inbox()
	assert len(msgs) == nbmsgs, f'unexpected number of messages: {len(msgs)}'
	msg = msgs[0]
	assert msg.mailfrom == os.environ['FROM_ADDRESS'], f'unexpected sender: {msg.mailfrom}'
	return len(msgs)

# DOES NOT WORK CURRENTLY
# def test_filtered_inbox():
# 	subject = 'testing delete'
# 	send_test_mail(subject)
# 	msgs = reader.inbox({'subject': subject})
# 	assert len(msgs) == 1
# 	msg = msgs[0]
# 	assert msg.subject == subject

def test_status():
	status = reader.status()
	assert status == 'operational', "maildrop status not operational"
	return status

def test_statistics():
	blocked, saved = reader.statistics()
	assert blocked >= 1, f'unexpected stat: blocked = {blocked}'
	assert saved >= 1, f'unexpected stat: saved = {saved}'
	return (blocked, saved)

def test_alias():
	alias = reader.altinbox()
	assert alias is not None, "alias not given by maildrop"
	return alias

def test_message(subject):
	msgs = reader.inbox()
	msg_found = 0
	for m in msgs:
		msg = reader.message(m.id)
		assert msg is not None, "null msg"
		assert msg.mailfrom == os.environ['FROM_ADDRESS'], f"msg not sent by right sender: {msg.mailfrom}"
		assert msg.html == message_test_body, f"unexpected msg content: {msg.html}"
		if msg.subject == subject:
			msg_found += 1
			content = msg.html

	assert msg_found == 1, f"subject '{subject} not found in messages or found several times: {msg_found}"
	assert content is not None, f"content of message with subject:{subject} not found"
	return content

def test_delete_message():
	msgs = reader.inbox()
	nmsgs = len(msgs)
	msg = msgs[0]
	id = msg.id
	reader.delete(id)
	msgs = reader.inbox()
	assert len(msgs) == nmsgs - 1, f"messages number should have decreased of one"
	assert id not in [msg.id for msg in msgs], f"message id {id} still in msgs list after deletion"
	return "deleted"

do(test_status)
do(test_statistics)
do(test_ping)
do(test_alias)

nbmsgs = 3
for _ in range(nbmsgs):
	subject = f'testing message #{generate_random_string(8)}'
	do(send_test_mail, subject)

do(test_inbox, nbmsgs)
do(test_message, subject)
do(test_delete_message)
