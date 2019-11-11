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

from WebsocketException import WSException

MAX_DATA_SIZE = 1024
WS_MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
SUBMISSION_CHECKSUM = md5(open('ok_boomer.zip', "rb").read()).hexdigest()

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
      if(self.send_handshake(parsed_header) != 0):  # or else connection broken
        try:
          self.maintain_communication()
        except WSException as err:
          print('Exception', err.code, err.message)
          if (err.code in [WSException.PROTOCOL_ERROR, WSException.UNCONSISTENT_TYPE_ERROR]):
            exception_msg = Frame(1, Frame.cls_frame, struct.pack('!H', err.code) + (err.message).encode())
            self.conn.send(exception_msg.toFrame())
          
    else:
      self.send_400()
    
    # close tcp connection
    self.conn.close()
  
  def maintain_communication(self):
    context = COMMAND_CONTEXT.NONE
    payload_context = ''
    while(True):
      message = self.conn.recv(2147483633 + 14)
      if (len(message) == 0):
        raise WSException(WSException.CONNECTION_CLOSED)
      
      try:
        parsed_msg, need_more = Frame.toUnframe(message)
      except:
        raise WSException(WSException.PROTOCOL_ERROR, "Error while parsing frame")
      curr_recv = parsed_msg.payload_len
      while (curr_recv < need_more):
        another_message = self.conn.recv(need_more - curr_recv)
        if (len(another_message) == 0):
          raise WSException(WSException.CONNECTION_CLOSED)

        another_message = Frame.toUnmask(parsed_msg.getMaskKey(), another_message)
        
        if (context == COMMAND_CONTEXT.ECHO or parsed_msg.opcode == Frame.txt_frame):
          another_message = another_message.decode()
        else:
          another_message = bytearray(another_message)
        
        parsed_msg.concatPayload(another_message)
        curr_recv += len(another_message)

      if (parsed_msg.opcode == Frame.cls_frame):
        # respond to CLOSE control frame
        close_msg = Frame(1, Frame.cls_frame, struct.pack('!H', 1000))
        self.conn.send(close_msg.toFrame())
        break
      elif (parsed_msg.opcode == Frame.ping_frame):
        if (parsed_msg.FIN != 1):
          raise WSException(WSException.PROTOCOL_ERROR, 'received fragmented control frame')
        # respond to PING control frame
        pong_msg = Frame(1, Frame.pong_frame, b'', False)
        self.conn.send(pong_msg.toFrame())
      else:
        payload = parsed_msg.getPayload()
        if (parsed_msg.opcode == Frame.txt_frame): # accept new text message
          # if (context == COMMAND_CONTEXT.SUBMISSION):
          #   raise WSException(WSException.UNCONSISTENT_TYPE_ERROR, 'another text frame interleaved with current context')
          if (payload[0] == '!'): # getting first command message
            if (payload[:5] == '!echo'):
              context = COMMAND_CONTEXT.ECHO
              payload_context = payload[6:]
            elif (payload[:11] == '!submission'):
              context = COMMAND_CONTEXT.SUBMISSION

          if (parsed_msg.FIN == 1): # first and last message
            # execute & send reply based on command
            if (context == COMMAND_CONTEXT.ECHO):
              echo_reply = Frame(1, Frame.txt_frame, payload_context)
              self.conn.send(echo_reply.toFrame())
              
              payload_context = ''
              context = COMMAND_CONTEXT.NONE
            elif (context == COMMAND_CONTEXT.SUBMISSION):
              filename = 'ok_boomer.zip'
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

          else: # not final message
            if (COMMAND_CONTEXT.ECHO):
              payload_context += payload
        elif (parsed_msg.opcode == Frame.bin_frame):
          # if (context != COMMAND_CONTEXT.SUBMISSION):
          #   raise WSException(WSException.UNCONSISTENT_TYPE_ERROR, 'another bin frame interleaved with current context')
          if (parsed_msg.FIN == 1):  #first and last message
            if (context == COMMAND_CONTEXT.SUBMISSION):
              
              checksum = md5(payload).hexdigest()

              answer = '1' if (checksum == SUBMISSION_CHECKSUM) else '0'
              check_msg = Frame(1, Frame.txt_frame, answer)
              self.conn.send(check_msg.toFrame())

              context = COMMAND_CONTEXT.NONE
          else:
            payload_context = payload
        elif (parsed_msg.opcode == Frame.con_frame):
          if (context == COMMAND_CONTEXT.ECHO and parsed_msg.FIN == 1):
            try:
              payload = payload.decode()
            except:
              raise WSException(WSException.UNCONSISTENT_TYPE_ERROR, 'getting binary payload instead of text')

            payload_context += payload
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
            context = COMMAND_CONTEXT.NONE
          elif (context == COMMAND_CONTEXT.ECHO and parsed_msg.FIN == 0):
            payload_context += payload
          elif (context == COMMAND_CONTEXT.SUBMISSION and parsed_msg.FIN == 1):
            payload_context += payload
            checksum = md5(payload_context).hexdigest()

            answer = '1' if (checksum == SUBMISSION_CHECKSUM) else '0'
            check_msg = Frame(1, Frame.txt_frame, answer)
            self.conn.send(check_msg.toFrame())

            payload_context = ''
            context = COMMAND_CONTEXT.NONE
          elif (context == COMMAND_CONTEXT.SUBMISSION and parsed_msg.FIN == 0):
            payload_context += payload

  
  def connection_failed(self):
    self.conn.close()

  def parse_header(self, header):
    parsed_header = {}
    parsed_header['Endpoint'] = re.findall(r'GET (/[\w/]*) HTTP/[1\.1|2\.0|3\.0]', header[0])[0]

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

    return (self.conn.send(response.encode()))
  
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
    header_check = [False] * 6
    for line in header:
      if (re.match(r'GET /\w* HTTP/[1\.1|2\.0|3\.0]', line)):
        header_check[0] = True
      if (line == 'Upgrade: websocket'):
        header_check[1] = True
      elif (line == 'Connection: Upgrade'):
        header_check[2] = True
      elif (re.match(r'Sec-WebSocket-Version: 13', line)):
        header_check[3] = True
      elif (re.match(r'Host: [\.\w\:]+', line)):
        header_check[4] = True
      elif (re.match(r'Sec-WebSocket-Key: [A-Za-z0-9\+\-\\\.\~\/]{22}\=\=', line)):
        header_check[5] = True
    
    return all(header_check)

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
    ct = 0
    while (True):
      conn, addr = self.socket.accept()
      ct += 1
      print('a connection establised')
      ws_conn = WebsocketConnection(conn)
      ws_conn.start()

def main():
  host = '127.0.0.1'; port = 8000
  if (len(sys.argv) >= 3):
    host = sys.argv[1]
    port = int(sys.argv[2])
  
  ws_server = WebsocketServer(host, port)
  ws_server.start_server()
  ws_server.accept_connection()

main()
