import re
from logger import logger
import requests
from queue import Queue, Empty
import json
from urllib.parse import unquote, urlparse
from http.client import HTTPConnection
from threading import Thread, Lock


STATION_LIST_ENDPOINT = 'http://derekzeng.me/radio_stations'

class Stations:

  def __init__(self):
    self.stations = {}
    res = requests.get(STATION_LIST_ENDPOINT)
    if res.status_code >= 300 or res.status_code < 200:
      raise Exception("Failed to grab radio station list")

    stations = res.json()['stations']
    for stat in stations:
      self.stations[stat.get('name')] = {
        'url': stat.get('url'), 'connection': None
      }

    logger.info('Loaded {} stations'.format(len(self.stations)))
    self.cb_registry = {}

  def on_switch_station(self, name, cb):
    if re.match(r'^\d{2,3}\.\d$', name):
      for sname in self.stations:
        try:
          sname.index(name)
          name = sname
          break
        except:
          continue

    if not name in self.stations:
      logger.info('Requested station {} is not found'.format(name))
      return

    if cb in self.cb_registry:
      self.unsubscribe_station(self.cb_registry.get(cb), cb)

    station_object = self.stations.get(name)
    if station_object.get('connection') == None:
      try:
        station_object['connection'] = Station(name, station_object.get('url'))
        station_object['connection'].on()
      except Exception as e:
        logger.exception(e)

    self.subscribe_station(name, cb)

  def subscribe_station(self, name, cb):
    logger.info('Subscribe_station to {}'.format(name))
    station_object = self.stations.get(name).get('connection')
    station_object.subscribe(cb)
    self.cb_registry[cb] = name

  def unsubscribe_station(self, name, cb):
    logger.info('Unsubscribe_station from {}'.format(name))
    station_object = self.stations.get(name)
    if station_object.get('connection') != None:
      conn = station_object.get('connection')
      conn.unsubscribe(cb)
      del self.cb_registry[cb]
      if conn.empty():
        conn.off()
        station_object['connection'] = None



class Station:
  connection = None
  name = None
  url = None

  def __init__(self, name, url):
    logger.info('Initializing station {} '.format(name))
    self.listeners = set([])
    self.name = name
    self.url = url
    self.lock = Lock()

  def on(self):
    logger.info('Turnning on {}'.format(self))
    self.running = True
    self._init_connection()

  def on_message(self, msg):
    logger.info('{} on_message {}'.format(self, msg.get('title')))

    # need to synchronize
    # connection thread may call on_message before last notify finishes
    self.notify(msg)

  def notify(self, msg):
    with self.lock:
      for callback in self.listeners:
        callback(msg)

  def subscribe(self, cb):
    logger.debug('Subscribe {} to {}'.format(cb, self))
    with self.lock:
      self.listeners.add(cb)

  def unsubscribe(self, cb):
    logger.debug('Unsubscribe {} from {}'.format(cb, self))
    with self.lock:
      self.listeners.remove(cb)

  def _init_connection(self):
    if self.connection and self.connection.is_alive():
      logger.info('Connection is already running')
      return

    self.connection = Thread(
        target=Station._connect_to_station,
        args=(self,))
    self.connection.start()

  def _connect_to_station(self):
    '''
    call self.on_message when a message arrives
    call self.on_disconnect when connection is lost
    '''
    url = urlparse(self.url)
    conn = HTTPConnection(url.hostname, timeout=4)

    try:
      conn.request('get', url.path, headers={'Icy-MetaData': '1'})
    except Exception as e:
      logger.exception(e)
      return

    res = conn.getresponse()
    metaint = int(res.getheader('icy-metaint', '0'))
    logger.debug('icy-metaint is {} for {}'.format(metaint, self))

    if not metaint:
      logger.info('Endpoint does not support icy-metaint')
      return

    def parse(s):
      return json.loads(s) if s.startswith('{') else s

    logger.debug('Starting message loop for {}'.format(self))
    while self.running:
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
            # No cover url
            continue

          self.on_message(obj)
      except Exception as e:
        logger.exception(e)
        res.close()
        break

    if not res.closed:
      res.close()

    conn.close()
    logger.info('Closing connection for {}'.format(self))
    self.on_disconnect()

  def empty(self):
    with self.lock:
      return len(self.listeners) == 0

  def on_disconnect(self):
    logger.info('{} disconnected'.format(self))

  def off(self):
    self.running = False

  def __repr__(self):
    return 'Station {}: {}'.format(self.name, self.url)



# stations = Stations()
# stations.on_switch_station(
#     '93.3', lambda msg: print("I got a message {}".format(msg.get('title'))))
#
#
