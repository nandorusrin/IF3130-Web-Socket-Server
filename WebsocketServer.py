import socket
import re
import threading
import time
import struct
import os
import sys
from hashlib import sha1, md5
from base64 import b64encode
from frame import Frame

MAX_DATA_SIZE = 1024
WS_MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class COMMAND_CONTEXT:
  NONE = 0
  ECHO = 1
  SUBMISSION = 2
  CHECK = 3

class WebsocketConnection(threading.Thread):
  def __init__(self, conn):
    threading.Thread.__init__(self)
    self.conn = conn
    self.hostaddr, self.port = self.conn.getpeername()

  # thread run
  def run(self):
    header, body = self.get_parse_first_request()
    if (self.validate_opening(header)):
      parsed_header = self.parse_header(header)
      self.send_handshake(parsed_header)
      self.maintain_communication()
    else:
      self.send_400()
    
    # close tcp connection
    self.conn.close()
  
  def maintain_communication(self):
    recv_fragment = False
    context = COMMAND_CONTEXT.NONE
    payload_context = ''
    while(True):
      message = self.conn.recv(Frame.SIZE_UINT16)
      parsed_msg = Frame.toUnframe(message)

      if (parsed_msg.opcode == Frame.cls_frame):
        # respond to CLOSE control frame
        close_msg = Frame(1, Frame.cls_frame, struct.pack('!H', 1000))
        self.conn.send(close_msg.toFrame())
        break
      elif (parsed_msg.opcode == Frame.ping_frame):
        # respond to PING control frame
        pong_msg = Frame(1, Frame.pong_frame, b'', False, parsed_msg.rsv1, parsed_msg.rsv2, parsed_msg.rsv3)
        self.conn.send(pong_msg.toFrame())
      else:
        if (parsed_msg.opcode == Frame.txt_frame): # accept new message
          payload = parsed_msg.getPayload()

          if (payload[0] == '!'): # getting first command message
            if (payload[:5] == '!echo'):
              context = COMMAND_CONTEXT.ECHO
              payload_context += payload[6:]
            elif (payload[:11] == '!submission'):
              context = COMMAND_CONTEXT.SUBMISSION
            elif (payload[:6] == '!check'):
              context = COMMAND_CONTEXT.CHECK
              payload_context += payload[7:]

          if (parsed_msg.FIN == 1): # is the final message
            # execute & send reply based on command
            if (context == COMMAND_CONTEXT.ECHO):
              echo_reply = ''
              if (len(payload_context) <= Frame.SIZE_UINT16):
                echo_reply = Frame(1, Frame.txt_frame, payload_context, parsed_msg.rsv1, parsed_msg.rsv2, parsed_msg.rsv3)
                self.conn.send(echo_reply.toFrame())
              else:
                sent_ct = 0; payload_context_len = len(payload_context)
                while (sent_ct < payload_context_len):
                  if (sent_ct == 0):
                    echo_reply = Frame(0, Frame.txt_frame, payload_context[:Frame.SIZE_UINT16])
                    sent_ct += Frame.SIZE_UINT16
                  elif (sent_ct + Frame.SIZE_UINT16 <= payload_context_len):
                    echo_reply = Frame(0, Frame.con_frame, payload_context[sent_ct:sent_ct+Frame.SIZE_UINT16])
                    sent_ct += Frame.SIZE_UINT16
                  else:
                    echo_reply = Frame(1, Frame.con_frame, payload_context[sent_ct:sent_ct+Frame.SIZE_UINT16])
                    sent_ct = payload_context_len
                  
                  self.conn.send(echo_reply.toFrame)
              
              payload_context = ''
            elif (context == COMMAND_CONTEXT.SUBMISSION):
              filename = 'readme.zip'
              fp = open(filename, "rb")

              file_size = os.path.getsize(filename)
              sent_ct = 0
              framed_msg = ''
              while (sent_ct < file_size):
                raw_bin = fp.read(Frame.SIZE_UINT16);
                if (sent_ct == 0):
                  final = 1 if len(raw_bin) >= file_size else 0

                  framed_msg = Frame(final, Frame.bin_frame, raw_bin)
                elif (sent_ct < file_size):
                  framed_msg = Frame(0, Frame.con_frame, raw_bin)
                else: # last message
                  framed_msg = Frame(1, Frame.con_frame, raw_bin)
                sent_ct += Frame.SIZE_UINT16
                self.conn.send(framed_msg.toFrame())

              fp.close()
            elif (context == COMMAND_CONTEXT.CHECK):
              filename = 'readme.zip'
              fp = open(filename, "rb")
              checksum = md5(fp.read()).hexdigest()
              
              answer = '1' if (checksum == payload_context) else '0'
              check_msg = Frame(1, Frame.txt_frame, answer)
              self.conn.send(check_msg.toFrame())

              payload_context = ''

            context = COMMAND_CONTEXT.NONE
          else: # not final message
            if (COMMAND_CONTEXT.ECHO):
              payload_context += payload
  
  def connection_failed(self):
    self.conn.close()

  def parse_header(self, header):
    parsed_header = {}
    parsed_header['Endpoint'] = re.findall(r'GET (/[\w/]*) HTTP/1\.1', header[0])[0]

    fields = ['Host', 'Sec-WebSocket-Key', 'Origin', 'Sec-WebSocket-Protocol', 'Sec-WebSocket-Version']

    for line in header[1:]:
      for i in range(len(fields)):
        if (re.match(r'(' + re.escape(fields[i]) + r')' + r': (.+)', line)):
          key_field, val_field = re.findall(r'([\w\-]+): (.+)', line)[0]
          parsed_header[key_field] = val_field
    
    return parsed_header

  def generate_ws_accept(self, sec_ws_key):
    digest_obj = sha1((sec_ws_key + WS_MAGIC_STRING).encode())
    return b64encode(digest_obj.digest()).decode()

  def send_handshake(self, parsed_header):
    ws_accept = self.generate_ws_accept(parsed_header['Sec-WebSocket-Key'])
    response = ("HTTP/1.1 101 Switching Protocols\r\n" +
                "Upgrade: websocket\r\n" +
                "Connection: Upgrade\r\n" +
                "Sec-WebSocket-Accept: "+ ws_accept +"\r\n")
    if 'Sec-WebSocket-Protocol' in parsed_header:
      response += "Sec-WebSocket-Protocol: "+ parsed_header['Sec-WebSocket-Protocol'] +"\r\n"
    
    response += "\r\n"

    self.conn.send(response.encode())
  
  def send_400(self):
    response = ("HTTP/1.1 400 Bad Request\r\n" +
                "Content-Type: text/plain\r\n" +
                "Connection: close\r\n" +
                "\r\n" +
                "Incorrect request")
    self.conn.send(response.encode())
  
  def get_parse_first_request(self):
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
      if (re.match(r'GET /\w* HTTP/1\.1', line)):
        header_check[0] = True
      if (line == 'Upgrade: websocket'):
        header_check[1] = True
      elif (line == 'Connection: Upgrade'):
        header_check[2] = True
      elif (re.match(r'Sec-WebSocket-Version: \d+', line)):
        header_check[3] = True
    
    return all(header_check)

  def close_connection(self):
    #  TODO: The server MUST close the connection upon receiving a
    #  frame that is not masked
    #   In this case, a server MAY send a Close
    #  frame with a status code of 1002 (protocol error)
    pass

class WebsocketServer:
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  
  def start_server(self):
    self.socket.bind((self.host, self.port))
    self.socket.listen(2);
    print('Server started on ', self.host, ':', self.port, sep='')

  def accept_connection(self):
    thread_list = []
    while (True):
      conn, addr = self.socket.accept()
      ws_conn = WebsocketConnection(conn)
      ws_conn.start()

def main():
  host = '127.0.0.1'; port = 4567
  if (len(sys.argv) >= 3):
    host = sys.argv[1]
    port = int(sys.argv[2])
  
  ws_server = WebsocketServer(host, port)
  ws_server.start_server()
  while (True):
    ws_server.accept_connection()

main()
