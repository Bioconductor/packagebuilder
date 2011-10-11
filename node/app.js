
// remember to start me with sudo so that flashpolicy file can be served on port 843:
// sudo node app.js
require.paths.unshift(__dirname+"/lib/")
var sys = require('sys')
var path = require('path')
var url = require("url")
var fu = require("./fu")
var uuid = require('node-uuid');
var exec = require('child_process').exec;
var packagebuilder = require('./packagebuilder');
var stomp = require("./stomp");
var express = require("express")


var port = 4000;

var app = require("http").createServer(handler),
 io = require("socket.io").listen(app),
 fs = require("fs");

app.listen(port);




function handler(request, response) {

  var uri = url.parse(request.url).pathname
    , filename = path.join(process.cwd() + "/public/", uri);
  
  path.exists(filename, function(exists) {
    if(!exists) {
      response.writeHead(404, {"Content-Type": "text/plain"});
      response.write("404 Not Found\n");
      response.end();
      return;
    }

	if (fs.statSync(filename).isDirectory()) filename += '/index.html';

    fs.readFile(filename, "binary", function(err, file) {
      if(err) {        
        response.writeHead(500, {"Content-Type": "text/plain"});
        response.write(err + "\n");
        response.end();
        return;
      }

      response.writeHead(200);
      response.write(file, "binary");
      response.end();
    });
  });
}


io.sockets.on('connection', function (socket) {
  sys.puts("in connection");
  sys.puts("socket.id = " + socket.id); //yes
  
  socket.on('disconnect', function(){
      sys.puts("this client just disconnected: " + socket.id);
      sys.puts("removing " + socket.id + " from clients")
  })
  socket.on('message', function(msg){
    sys.puts("in on.message");
    try {
        obj = JSON.parse(msg);
        obj['client_id'] = socket.id;
        obj['originating_host'] = "TODO ADD ORIGINATING HOST";
        obj['dev'] = dev;
        msg = JSON.stringify(obj);
    } catch(err) {
        sys.puts("error in JSON processing. Message not properly formed JSON?");
    }
    sys.puts("publishing " + msg);
    client.publish("/topic/buildjobs", msg);
  })
  
  
});

var client = new stomp.Client("merlot2.fhcrc.org", 61613);

sys.puts("before subscribing to queue");
client.subscribe("/queue/builderevents", function(data){
    sys.puts("got message: " + data.body);
    try {
        var obj = JSON.parse(data.body);
    } catch(err) {
        sys.puts("error in JSON processing. Message not properly formed JSON?");
      }
    var clientId = obj['client_id'];
      
    sys.puts("now what is clientId? " + clientId)

    for (var i = 0; i < io.sockets.clients().length; i++) {
      sys.puts("id of client is " + io.sockets.clients()[i].id)
      if (io.sockets.clients()[i].id == clientId) {
          sys.puts("a match!")
          io.sockets.clients()[i].emit("message", data.body)
          break;
      }
    }
});
sys.puts("after subscribing to queue");

console.log("Static file server running => CTRL + C to shutdown");



