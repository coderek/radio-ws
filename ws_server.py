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

class RadioStream:
  messages = None
  listeners = None
  running = True
  last_msg = None

  def __init__(self, station):
    self.messages = Queue()
    self.listeners = set()
    self.init_thread(station)
    self.init_consumer()
    print('done init {}'.format(active_count()))

  def dispatch(self, msg):
    print(self.listeners)
    for l in self.listeners:
      l.sendMessage(json.dumps(msg))

  def init_consumer(self):

    def consumer_thread(messages, host):
      while host.running:
        try:
          msg = messages.get(timeout=1)
        except Empty:
          continue

        host.last_msg = msg
        host.dispatch(msg)

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
    if self.last_msg:
      listener.sendMessage(json.dumps(self.last_msg))


class RadioMetaServer(WebSocket):

  def handleMessage(self):
    # echo message back to client
    # self.sendMessage(self.data)
    msg = self.data
    station_changed = re.match(RE_STATION_CHANGE, msg)
    if station_changed:
      to = station_changed.group(1)
      print('change station to {} {}'.format(to, active_count()))
      try:
        if not to in current_stations:
          current_stations[to] = RadioStream(
              ("Yes 93.3", "http://mediacorp.rastream.com/933fm"))

        current_stations[to].add_listener(self)
      except Exception as e:
        print(e)

  def handleConnected(self):
    print(self.address, 'connected', self.server.connections.keys())

  def handleClose(self):
    keys = current_stations.keys()
    for k in keys:
      stream = current_stations.get(k)
      stream.listeners.remove(self)
      if not stream.listeners:
        stream.close()
        del current_stations[k]

    print(self.address, 'closed')

server = SimpleWebSocketServer('', 8002, RadioMetaServer)
server.serveforever()
