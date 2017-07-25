import requests
import json
import re
from threading import active_count
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from queue import Queue, Empty
from threading import Thread
from radio_stream_reader import listen_to_station

RE_STATION_CHANGE = r'CHANGE_STATION\|(\d{2,3}\.\d)'
current_stations = {}


res = requests.get('http://derekzeng.me/radio_stations')
if res.status_code >= 300 or res.status_code < 200:
  raise Exception("Failed to grab radio station list")

stations = res.json()['stations']

class StationNotFoundException(Exception): pass


def get_station(to):
  station = list(filter(lambda s: to in s.get('name'), stations))
  if station:
    return (station[0]['name'], station[0]['url'])

  raise StationNotFoundException


class RadioStream:

  def __init__(self, station):
    self.messages = Queue()
    self.running = True
    self.listeners = set()
    self.init_thread(station)
    self.init_consumer()
    print('done init {}'.format(active_count()))

  def dispatch(self, msg):
    for l in self.listeners:
      l.sendMessage(json.dumps(msg))

  def init_consumer(self):

    def consumer_thread(messages, host):
      while host.running:
        try:
          msg = messages.get(timeout=1)
        except Empty:
          continue

        host.dispatch(msg)
      print('closed consumer thread {}'.format(active_count()))

    self.consumer = Thread(target=consumer_thread, args=(self.messages, self))
    self.consumer.start()

  def close(self):
    self.running = False
    self.producer.join()
    self.consumer.join()

  def init_thread(self, station):
    self.producer = Thread(
        target=listen_to_station,
        args=(station, self))
    self.producer.start()

  def add_listener(self, listener):
    self.listeners.add(listener)

  def remove_listener(self, listener):
    keys = current_stations.keys()
    for k in list(keys):
      stream = current_stations.get(k)
      stream.listeners.remove(listener)
      if not stream.listeners:
        del current_stations[k]
        stream.close()


class RadioMetaServer(WebSocket):

  def handleMessage(self):
    # echo message back to client
    # self.sendMessage(self.data)
    msg = self.data
    station_changed = re.match(RE_STATION_CHANGE, msg)
    if station_changed:
      try:
        if self.radio_station:
          self.radio_station.remove_listener(self)
      except Exception as e:
        print(e)

      to = station_changed.group(1)
      print('change station to {} {}'.format(to, active_count()))
      try:
        if not to in current_stations:
          self.radio_station = RadioStream(get_station(to))
          current_stations[to] = self.radio_station
        current_stations[to].add_listener(self)
      except Exception as e:
        print(e)

  def handleConnected(self):
    print(self.address, 'connected', self.server.connections.keys())

  def handleClose(self):
    if self.radio_station:
      self.radio_station.remove_listener(self)
      self.radio_station = None

    print(self.address, 'closed')

server = SimpleWebSocketServer('', 8002, RadioMetaServer)
server.serveforever()
