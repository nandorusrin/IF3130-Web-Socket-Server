var socket = new WebSocket("ws://127.0.0.1:4567")
socket.onopen = function(event) {
  console.log('Hello sent')
  socket.send("Hello");
}

socket.onmessage = function(event) {
  console.log('on message')
  console.log(event.data)
}

socket.onclose = function(event) {
  console.log(event)
}