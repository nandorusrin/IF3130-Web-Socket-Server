import socket
import re

MAX_DATA_SIZE = 1024
WS_MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class WebsocketConnection:
  def __init__(self, conn):
    self.conn = conn
    self.hostaddr, self.port = self.conn.getpeername()

    header, body = self.get_payload(self.conn)
    if (self.validate_opening(header)):
      print(header, '\n\n', body)
    else:
      print('sending 400')
      self.send_400()
  
  def send_400(self):
    response = ("HTTP/1.1 400 Bad Request\r\n" +
                "Content-Type: text/plain\r\n" +
                "Connection: close\r\n" +
                "\r\n" +
                "Incorrect request")
    self.conn.send(response.encode())
  
  def get_payload(self, conn):
    payload = (self.conn.recv(MAX_DATA_SIZE)).decode().split('\r\n')
    
    # parse header & body
    header = []; body = []
    bound = 0
    payload_len = len(payload)
    i = 0
    while (i < payload_len):
      if (payload[i] == ''):
        if (i+1 < payload_len and payload[i+1] == ''):
          bound = i
          break
      i += 1
    
    if (bound > 0):  # bound found
      header = payload[:bound]
      body = payload[bound+2:]
    else:
      header = payload
    
    return (header, body)
  
  def validate_opening(self, header):
    header_check = [False] * 4
    for line in header:
      if (re.match(r'GET /\w* HTTP\/1\.1', line)):
        header_check[0] = True
      if (line == 'Upgrade: websocket'):
        header_check[1] = True
      elif (line == 'Connection: Upgrade'):
        header_check[2] = True
      elif (re.match(r'Sec-WebSocket-Version: \d+', line)):
        header_check[3] = True
    
    return all(header_check)

class WebsocketServer:
  def __init__(self, port= 4567, host='localhost'):
    self.port = port
    self.host = host
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  
  def start_server(self):
    self.socket.bind((self.host, self.port))
    self.socket.listen(2);
    print('Server started on ', self.host, ':', self.port, sep='')

  def accept_connection(self):
    conn, addr = self.socket.accept()
    ws_conn = WebsocketConnection(conn)

def main():
  ws_server = WebsocketServer()
  ws_server.start_server()
  while (True):
    ws_server.accept_connection()

main()
