# A Python package to read emails from maildrop.cc

__THIS IS STILL WIP__

This package provides a very simple class MailDropReader that mimics the graphql API of maildrop.cc.
You create a new reader with `MailDropReader(<your maildrop.cc inbox name>)
The methods are:
* __status()__: provides the current maildrop.cc status. Returns 'operational' or an error string from the server
* __ping(string)__: pings the maildrop.cc server with the given string. Returns 'pong <string>'
* __inbox()__: returns all messages of your inbox (currently returns ALL messages, the filters aren't working). Returns a list of messages with only basic fields filled.
* __message(message_id)__: returns a full message including its body, its sender IP, ...
* __delete__(message_id)__: deletes a message by its id. Returns True if ok
* __statistics()__: returns maildrop.cc statistics. Returns a tuple (blocked, saved)
* __altinbox()__: returns an alias for your inbox. Subsequent MailDropReaders created with this alias will return messages from the original inbox

## Example:
```python
from maildropy import MailDropReader
reader = MailDropReader("my_own-inbox")

msgs = reader.inbox()
for msg in msgs:
  print(f"subject: {msg.subject}, from: {msg.mailfrom}, date:{msg.date}")
  message = reader.message(msg.id)
  print(f"content: {message.html}, ip={message.ip}, headerfrom={message.headerfrom}"
```
 
