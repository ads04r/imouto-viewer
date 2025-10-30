import imaplib, email, email.header, email.parser, email.message, datetime
from dateutil import tz

from viewer.models import RemoteInteraction

import logging
logger = logging.getLogger(__name__)

def import_sms_from_imap(user, host, username, password, inbox='INBOX', countrycode='44'):
	"""
	For users using the Android app 'SMS Backup+', this function gets the user's text messages that have been stored on
	an IMAP mail server by the app and imports them into Imouto Viewer as RemoteInteraction objects.

	:param host: The host name or IP address of the IMAP server.
	:param username: The username needed to log into the IMAP server.
	:param password: The password needed to log into the IMAP server.
	:param inbox: The name of the inbox in which to search for new messages.
	:param countrycode: This is the dialling code for the country in which the user is based. It's a dirty hack for standardising UK phone numbers to avoid duplicates; it causes the function to attempt to deduplicate if set to '44', or do nothing if set to anything else.
	:return: The number of new messages imported.
	:rtype: int
	"""
	try:
		minmsg = RemoteInteraction.objects.filter(user=user, type='sms').order_by('-time')[0]
	except:
		minmsg = RemoteInteraction.objects.filter(user=user).order_by('time')[0]
	mindt = minmsg.time
	minds = mindt.strftime("%-d-%b-%Y")

	acc = imaplib.IMAP4_SSL(host)
	try:
		rv, data = acc.login(username, password);
	except imaplib.IMAP4.error:
		return -1

	rv, mailboxes = acc.list()
	rv, data = acc.select(inbox)
	rv, data = acc.search(None, '(SINCE "' + minds + '")')

	ct = 0

	if rv == 'OK':

		for i in data[0].split():
			rv, data = acc.fetch(i, '(RFC822)')
			if rv != 'OK':
				continue
			msg = email.message_from_string(data[0][1].decode('utf-8'))
			email.header.decode_header(msg['Subject'])
			dtpl = email.utils.parsedate_tz(msg['Date'])
			dt = datetime.datetime(*dtpl[0:6], tzinfo=tz.tzoffset('FLT', dtpl[9]))
			body = msg.get_payload()
			if((type(body)) is list):
				body = body[0]
			if isinstance(body, email.message.Message):
				body = body.get_payload()

			if dt < mindt:
				continue

			body = body.replace('=2E', '.').replace('=\r\n', '')
			parser = email.parser.HeaderParser()
			headers = parser.parsestr(msg.as_string())
			msgtype = headers['X-smssync-datatype']

			if msgtype != 'SMS':
				continue

			number = str(headers['X-smssync-address']).replace(' ', '')
			if number[0] == '0':
				number = '+' + countrycode + number[1:]
			smstype = int(headers['X-smssync-type'])
			if smstype == 1:
				incoming = True
			else:
				incoming = False

			try:
				msg = RemoteInteraction.objects.get(user=user, type='sms', time=dt, address=number, incoming=incoming, title='', message=body)
			except:
				msg = RemoteInteraction(user=user, type='sms', time=dt, address=number, incoming=incoming, title='', message=body)
				ct = ct + 1
				msg.save()

	return ct

def import_calls_from_imap(user, host, username, password, inbox='INBOX', countrycode='44'):
	"""
	For users using the Android app 'SMS Backup+', this function gets the user's phone call history that has been stored on
	an IMAP mail server by the app and imports them into Imouto Viewer as RemoteInteraction objects.

	:param host: The host name or IP address of the IMAP server.
	:param username: The username needed to log into the IMAP server.
	:param password: The password needed to log into the IMAP server.
	:param inbox: The name of the inbox in which to search for new messages.
	:param countrycode: This is the dialling code for the country in which the user is based. It's a dirty hack for standardising UK phone numbers to avoid duplicates; it causes the function to attempt to deduplicate if set to '44', or do nothing if set to anything else.
	:return: The number of new messages imported.
	:rtype: int
	"""
	try:
		minmsg = RemoteInteraction.objects.filter(user=user, type='phone-call').order_by('-time')[0]
	except:
		minmsg = RemoteInteraction.objects.filter(user=user).order_by('time')[0]
	mindt = minmsg.time
	minds = mindt.strftime("%-d-%b-%Y")

	acc = imaplib.IMAP4_SSL(host)
	try:
		rv, data = acc.login(username, password);
	except imaplib.IMAP4.error:
		return -1

	rv, mailboxes = acc.list()
	rv, data = acc.select('"' + inbox + '"')
	rv, data = acc.search(None, '(SINCE "' + minds + '")')

	ct = 0

	if rv == 'OK':

		for i in data[0].split():
			rv, data = acc.fetch(i, '(RFC822)')
			if rv != 'OK':
				continue
			msg = email.message_from_string(data[0][1].decode('utf-8'))
			email.header.decode_header(msg['Subject'])
			dtpl = email.utils.parsedate_tz(msg['Date'])
			dt = datetime.datetime(*dtpl[0:6], tzinfo=tz.tzoffset('FLT', dtpl[9]))
			body = msg.get_payload()
			if((type(body)) is list):
				body = body[0]
			if isinstance(body, email.message.Message):
				body = body.get_payload()

			if dt < mindt:
				continue

			body = body.replace('=2E', '.').replace('=\r\n', '')
			parser = email.parser.HeaderParser()
			headers = parser.parsestr(msg.as_string())
			msgtype = headers['X-smssync-datatype']

			if msgtype != 'CALLLOG':
				continue

			number = str(headers['X-smssync-address']).replace(' ', '')
			if len(number) == 0:
				continue
			if number[0] == '0':
				number = '+' + countrycode + number[1:]
			if body.endswith('(outgoing call)'):
				incoming = False
			else:
				incoming = True

			try:
				msg = RemoteInteraction.objects.get(user=user, type='phone-call', time=dt, address=number, incoming=incoming, title='', message=body)
			except:
				msg = RemoteInteraction(user=user, type='phone-call', time=dt, address=number, incoming=incoming, title='', message=body)
				msg.save()
				ct = ct + 1
				msg.save()

	return ct
