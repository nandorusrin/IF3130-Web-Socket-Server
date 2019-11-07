import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", 4567))
request = ("GET / HTTP/1.1\r\n" +
          "Host: server.example.com\r\n" +
          "Upgrade: websocket\r\n" +
          "Connection: Upgrade\r\n" +
          "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n" +
          "Origin: http://example.com\r\n" +
          "Sec-WebSocket-Protocol: chat, superchat\r\n" +
          "Sec-WebSocket-Version: 13\r\n" + 
          "\r\n")
sock.send(request.encode())
res = sock.recv(1024)
print(res)
