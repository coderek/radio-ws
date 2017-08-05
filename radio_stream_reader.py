import json
from threading import active_count
from urllib.parse import unquote, urlparse
import sys
from http.client import HTTPConnection
from logger import logger

station = ("Yes 93.3", "http://mediacorp.rastream.com/933fm")


def listen_to_station(station, radio_streamer):
  url = urlparse(station[1])

  conn = HTTPConnection(url.hostname, timeout=4)
  conn.request('get', url.path, headers={'Icy-MetaData': '1'})
  res = conn.getresponse()

  metaint = int(res.getheader('icy-metaint', '0'))

  if not metaint:
    logger.info('Endpoint does not support icy-metaint')
    return

  def parse(s):
    return json.loads(s) if s.startswith('{') else s

  while radio_streamer.running:
    try:
      res.read(metaint)
      l = int(ord(res.read(1))) * 16
      if l:
        bytes = res.read(l)
        txt = bytes.decode()
        parts = [[parse(unquote(p.strip(' \'\"'))) for p in phrase.split('=')] for phrase in txt.strip().split(';')[:-1]]
        obj = {'title': parts[0][1]}
        try:
          if 'current_song' in parts[1][1]:
            obj['coverUrl'] = parts[1][1]['current_song']['coverUrl']
        except Exception as e:
          logger.error(e)


        radio_streamer.messages.put(obj, timeout=1)
    except Exception as e:
      logger.info(e)
      res.close()
      break

  if not res.closed:
    res.close()

  conn.close()
  logger.info('closed producer thread {} {}'.format(active_count(), res.closed))

  return
