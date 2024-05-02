import requests
import json
import certifi
import urllib3
import logging

logger = logging.getLogger(__name__)

http = urllib3.PoolManager(
    cert_reqs="CERT_REQUIRED",
    ca_certs=certifi.where()
)

class MailDropMessage:
      def __init__(self, id, headerfrom = None, subject = None, date = None, 
                   mailfrom = None, html = None, ip = None,  
                   helo = None, rcptto = [], data = None):
            self.id = id
            self.headerfrom = headerfrom
            self.subject = subject
            self.date = date
            self.ip = ip
            self.helo = helo
            self.mailfrom = mailfrom
            self.rcptto = rcptto
            self.data = data
            self.html = html

class MailDropReader:
    class MailDropQuery:
        def __init__(self, qtype, name, query, fields=[]):
            self.type = qtype
            self.name = name
            self.query = query
            self.fields = fields

    _maildrop_api = "https://api.maildrop.cc/graphql"

    def __init__(self, inbox: str):
        if '@' in inbox:
            self.inbox_name, domain = inbox.split("@")
            if domain != 'maildrop.cc':
                raise ValueError('inbox email addresses must be in the "maildrop.cc" domain')
        else:
            self.inbox_name = inbox

    def __repr__(self):
        return "<Maildrop[%s]>" % self.inbox_name

    def _call_api(self, query: MailDropQuery):
        fields = ' '.join(s for s in query.fields)
        if fields: fields = f'{{ {fields} }}'
        query_data = f'{{"query": "{query.type} {query.name} {{ {query.query} {fields} }}"}}'
        logger.debug(">>> maildrop query=", query_data)
        response = requests.post(self._maildrop_api, 
                                headers={'content-type': 'application/json'},
                                data=query_data, 
                                verify=True)
        if response.status_code != 200:
          logger.debug(f"inbox call result: {response.text}")
          raise ValueError(response.content)

        json_data = json.loads(response.text)
        return json_data['data']

    def ping(self, message: str ="hello, world!") -> str:
        query = MailDropReader.MailDropQuery(
          qtype = "query",
          name = 'ping',
          query = f'ping(message:\\"{message}\\")',
        )
        res = self._call_api(query)
        logger.debug(f"ping result: {res['ping']}")
        return res['ping']
        
    def inbox(self, filters: dict = None):
        """gets all messages from maildrop inbox. Can be filtered by a dict of MailDropMessage fields"""
        filters_str = ' ' + ' '.join([f'{k}: \\"{v}\\"' for k, v in filters.items()]) if filters else ''
        query = MailDropReader.MailDropQuery(
            qtype = "query",
            name = "inbox",
            # query = f'inbox(mailbox:\\"{self.inbox_name}\\"{filters_str})',
            query = f'inbox(mailbox:\\"{self.inbox_name}\\")',
            fields = ['id', 'mailfrom', 'subject', 'date']
        )
        jdata = self._call_api(query)
        logger.debug(f"inbox call result: {jdata['inbox']}")
        return [MailDropMessage(**mess) for mess in jdata['inbox']]
    
    def message(self, message_id) -> MailDropMessage:
        """get a full message content by its id"""
        query = MailDropReader.MailDropQuery(
          qtype = "query",
          name = 'get_email',
          query = f'message(mailbox:\\"{self.inbox_name}\\", id:\\"{message_id}\\")',
          fields =  ['id', 'headerfrom', 'subject', 'date', 'html', 'ip', 'mailfrom', 'data', 'rcptto', 'helo']
        )
        mess = self._call_api(query)
        mess = mess['message']
        logger.debug(f"message {message_id} call result: {mess}")
        return MailDropMessage(**mess)
    
    def delete(self, message_id) -> bool:
        """delete a message by its id"""
        query = MailDropReader.MailDropQuery(
          qtype = "mutation",
          name = 'delete_message',
          query = f'delete(mailbox:\\"{self.inbox_name}\\", id:\\"{message_id}\\")',
        )
        res = self._call_api(query)
        logger.debug(f"delete {message_id} call result: {res['delete']}")
        return res['delete']
        
    def status(self) -> str:
        """Returns the maildrop platform status. Can be 'operational' or an error string"""
        query = MailDropReader.MailDropQuery(
          qtype = "query",
          name = "status",
          query="status"
        )
        res = self._call_api(query)
        return res['status']
        
    def statistics(self):
        """returns maildrop statistics in the form of a tuple (blocked, saved)"""
        query = MailDropReader.MailDropQuery(
          qtype = "query",
          name = "statistics",
          query="statistics { blocked saved }"
        )
        res = self._call_api(query)
        return (res['statistics']['blocked'], res['statistics']['saved'])
        
    def altinbox(self) -> str:
        """returns an alias for the inbox that can be used in subsequent MailDropReaders"""
        query = MailDropReader.MailDropQuery(
          qtype = "query",
          name = "alternate_inbox",
          query = f'altinbox(mailbox:\\"{self.inbox_name}\\")',
        )
        res = self._call_api(query)
        return res['altinbox']
