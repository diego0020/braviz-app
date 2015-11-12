var braviz = (function(){
function connect_to_ws(message_handler){
var last_message = null;
var message_getter = null;
var errorSleepTime = 500;
var raw_socket;
 function openWS() {
    var address = "ws://" + window.location.host + "/messages_ws";
    raw_socket = new WebSocket(address);
    raw_socket.onerror=function () {
    if (errorSleepTime < 5000){
    errorSleepTime*=2;
    }
    };
    raw_socket.onmessage = function(e) {
      if (last_message==e.data){
      return;
      }
      message = JSON.parse(e.data);
      message_handler(message);
      }
      raw_socket.onclose = function(e) {
      window.setTimeout(openWS, errorSleepTime);
    };
  }
  openWS();
  var socket={};
  socket.send = function(msg){
    last_message = msg;
    raw_socket.send(msg);
  }
  return socket;
}

var braviz_module = {};
braviz_module.connect_to_ws = connect_to_ws;
return braviz_module;
})();