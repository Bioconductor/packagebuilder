
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

 io.configure(function () {
   io.set('transports', ["websocket", "htmlfile", "xhr-polling", "jsonp-polling"]);
 });

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
        var clientId = "_" + socket.id + "_"
        sys.puts("setting client_id to " + clientId)
        obj['client_id'] = clientId;
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
client.subscribe("/topic/builderevents", function(data){
    sys.puts("got message: " + data.body);
    var obj;
    try {
        obj = JSON.parse(data.body);
    } catch(err) {
        sys.puts("error in JSON processing. Message not properly formed JSON?");
    }
    sys.puts("after json processing")
    try {
        var clientId = obj['client_id'];  
    } catch (err) {
        sys.puts("object does not include client_id, bailing...")
        return;
    }
    sys.puts("now what is clientId? " + clientId)

    for (var i = 0; i < io.sockets.clients().length; i++) {
        var cl = io.sockets.clients()[i];
      var m = "_" + cl.id + "_";
      sys.puts("id of client is " + m)
      if (m == clientId) {
          sys.puts("a match!")
          cl.emit("message", data.body)
          break;
      }
    }
});
sys.puts("after subscribing to queue");

console.log("Static file server running => CTRL + C to shutdown");



