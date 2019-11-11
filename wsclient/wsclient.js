var socket = new WebSocket("ws://fcad9774.ngrok.io")
// var socket = new WebSocket("ws://127.0.0.1:4567")
var dataBlob;
socket.onopen = function(event) {
  console.log('Connection opened', event)
}

socket.onmessage = function(event) {
  var data = event.data
  console.log('on message', data)
  if (data instanceof Blob) {
    socket.send(data)
  }
}

socket.onclose = function(event) {
  console.log('Connection closed', event)
}

function send_cmd(cmd) {
  socket.send(cmd)
  // socket.send("!echo Dalam tugas besar ini, kalian akan mengimplementasikan sebuah websocket server \
  // sederhana. Implementasi harus dibuat dari layer 4 dengan menggunakan TCP \
  // socket, tidak boleh menggunaan HTTP server yang sudah ada. Untuk detail \
  // protokol websocket, kalian dapat membaca dokumen rfc berikut \
  // https://tools.ietf.org/html/rfc6455. Server yang kalian buat harus memperhatikan \
  // beberapa fungsionalitas, antara lain : \
  // 1. Handshake (opening & closing) \n\r\
  // 2. Framing (parsing & building) \
  // 3. Control frame (PING, PONG, CLOSE, dll) \
  // Selain itu, server juga memiliki beberapa perintah yang harus diimplementasikan,\
  // antara lain : \
  // 1. Client akan mengirimkan payload text berisi !!echo asjdhas dashdkjashdashd ksahd ks")
}

function close_conn() {
  socket.close(1000, 'mau close aja')
}