import requests
import json
import re
from threading import active_count
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from queue import Queue, Empty
from threading import Thread
from radio_stream_reader import listen_to_station
from logger import logger
from stations import Stations
from threading import Lock


RE_STATION_CHANGE = r'CHANGE_STATION\|(\d{2,3}\.\d)'
PORT = 8080

stations = Stations()

class StationNotFoundException(Exception): pass


class RadioMetaServer(WebSocket):

  def handleMessage(self):
    # echo message back to client
    # self.sendMessage(self.data)
    msg = self.data
    station_changed = re.match(RE_STATION_CHANGE, msg)
    if station_changed:
      to = station_changed.group(1)
      try:
        stations.on_switch_station(to, self.send_message)
      except Exception as e:
        logger.exception(e)

  def send_message(self, msg):
    return super().sendMessage(json.dumps(msg))

  def handleConnected(self):
    pass
    # logger.info(self.address + ' connected ' + ', '.join(self.server.connections.keys()))

  def handleClose(self):
    stations.unsubscribe_station(self.send_message)
    logger.info(self.address + ' closed')

server = SimpleWebSocketServer('', PORT, RadioMetaServer)
logger.info("Start server at port {}".format(PORT))
server.serveforever()
