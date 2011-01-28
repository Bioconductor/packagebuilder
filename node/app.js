require.paths.unshift(__dirname+"/lib/")
var io = require('socket.io')
var amqp = require('amqp')
var sys = require('sys')
var path = require('path')
var http = require('http')
var fs = require("fs")
var fu = require("./fu")
var uuid = require('node-uuid');
var exec = require('child_process').exec;


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

var connection = amqp.createConnection({ host: 'merlot2.fhcrc.org' });
 
 
connection.addListener('ready', function(){
  var from_web_exchange = connection.exchange('from_web_exchange', {type: 'fanout', autoDelete: false});
  var from_worker_exchange = connection.exchange('from_worker_exchange', {type: 'fanout', autoDelete: false});
  var fromBuildersQueue = connection.queue(uuid(), {exclusive: true}) //frombuilders
  fromBuildersQueue.bind('from_worker_exchange', '#')
  
  
  app.listen(3000, function(){
  
    console.log('listening for connections on port 3000')
    var socket = io.listen(app);
    
    socket.broadcast("hi there");
    
    fromBuildersQueue.subscribe( {ack:true}, function(message){
      sys.puts("got message: " + message.data.toString());
      var obj = JSON.parse(message.data.toString());
      if (obj['originating_host'] && obj['originating_host'] == hostname) {
          socket.broadcast(message.data.toString())
          fromBuildersQueue.shift()
      }
    })

    
     
    socket.on('connection', function(client){
      client.on('message', function(msg){
        try {
            obj = JSON.parse(msg);
            obj['originating_host'] = hostname;
            msg = JSON.stringify(obj);
        } catch(err) {
            sys.puts("error in JSON processing. Message not properly formed JSON?");
        }
        sys.puts("publishing " + msg);
        from_web_exchange.publish("#", msg); //key.fromweb
      })
      client.on('disconnect', function(){
      })
    })
    
  });
});

