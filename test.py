import asyncio
from urllib.parse import unquote, urlparse
from http.client import HTTPConnection
import logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

l = logging.getLogger('name')

def test():
    l.error(Exception("wrong"))

# test()


class MyProto(asyncio.Protocol):
  def connection_made(self, transport):
    print('connection made')

station = ("Yes 93.3", "http://mediacorp.rastream.com/933fm")
loop = asyncio.get_event_loop()
connection = loop.create_connection(
    MyProto, host='mediacorp.rastream.com'
    )

async def conn():
  url = urlparse(station[1])
  conn = HTTPConnection(url.hostname, timeout=4)
  conn.request('get', url.path, headers={'Icy-MetaData': '1'})
  res = conn.getresponse()
  print('connected')
  loop.call_soon(hello)
  print('closed')
  conn.close()


def hello():
  print('hello asyncio')

loop.run_until_complete(conn())
loop.close()

print('123')

