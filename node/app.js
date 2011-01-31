
// remember to start me with sudo so that flashpolicy file can be served on port 843:
// sudo node app.js
require.paths.unshift(__dirname+"/lib/")
/*
Install Socket.IO-node as follows:
git clone https://github.com/LearnBoost/Socket.IO-node.git
cd Socket.IO-node
git submodule update --init --recursive
*/
var io = require("./Socket.IO-node"); 
var amqp = require('amqp')
var sys = require('sys')
var path = require('path')
var http = require('http')
var fs = require("fs")
var fu = require("./fu")
var uuid = require('node-uuid');
var exec = require('child_process').exec;
var packagebuilder = require('./packagebuilder');


var app = require('appserver').createServer()


app.get('/', function(req, response){
    var filename = path.join(process.cwd(), "public/index.html");
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



var hostname;
 exec("hostname", function (error, stdout, sterr) {
     hostname = stdout.trim();
     sys.puts("hostname = " + hostname);
 });

//var connection = amqp.createConnection({ host: 'merlot2.fhcrc.org' });
var connection = amqp.createConnection({ host: packagebuilder.socketServer }); 
 
connection.addListener('ready', function(){
  var from_web_exchange = connection.exchange('from_web_exchange', {type: 'fanout', autoDelete: false});
  var from_worker_exchange = connection.exchange('from_worker_exchange', {type: 'fanout', autoDelete: false});
  var fromBuildersQueue = connection.queue(uuid(), {exclusive: true}) //frombuilders
  fromBuildersQueue.bind('from_worker_exchange', '#')
  
  
  app.listen(3000, function(){
  
    console.log('listening for connections on port 3000')
    var socket = io.listen(app);
    
    
    fromBuildersQueue.subscribe( {ack:true}, function(message){
      sys.puts("got message: " + message.data.toString());
      var obj = JSON.parse(message.data.toString());
      if (obj['originating_host'] && obj['originating_host'] == hostname) {
          var clientId = obj['client_id'];
          sys.puts("message came from " + clientId);
          var deafClients = [];
          
          for (var key in socket.clients) {
              if (key != null && key != clientId) {
                  deafClients.push(key);
              }
          }
          
          socket.broadcast(message.data.toString(), deafClients);
          fromBuildersQueue.shift()
      }
    })

    
    socket.on('clientConnect', function(client) {
        // an alias for socket.on('connection'), apparently.
    });
    
    socket.on('clientDisconnect', function(client){
        sys.puts("this client just disconnected: " + client.sessionId);
        sys.puts("this brings the total number of clients to: " + numClients(socket));
    });
     
    socket.on('connection', function(client){
      sys.puts("new client connected with id " + client.sessionId);
      sys.puts("this brings the total number of clients to: " + numClients(socket));
      
      
      client.on('message', function(msg){
        sys.puts("in on.message");
        try {
            obj = JSON.parse(msg);
            obj['originating_host'] = hostname;
            obj['client_id'] = client.sessionId;
            msg = JSON.stringify(obj);
        } catch(err) {
            sys.puts("error in JSON processing. Message not properly formed JSON?");
        }
        sys.puts("publishing " + msg);
        from_web_exchange.publish("#", msg); //key.fromweb
      })
      client.on('disconnect', function(){
          sys.puts("this client just disconnected: " + client.sessionId);
          sys.puts("this brings the total number of clients to: " + numClients(socket));
          
      })
    })
    
  });
});

var numClients = function(ioObj) {
    var i = 0;
    for (var key in ioObj.clients) {
        i++;
    }
    return i;
}