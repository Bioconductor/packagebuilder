// logging functions:
var fb_lite = false;
try {
	if (firebug) {
		fb_lite = true;  
		firebug.d.console.cmd.log("initializing firebug logging");
	}
} catch(e) {
	// do nothing
}



function log(message) {
	if (fb_lite) {  
		console.log(message);
	} else {
		if (window.console) {
			console.log(message);
		} 
	}
	if (window.dump) {
	    dump(message + "\n");
	}
}



jQuery(function(){
  var socket;
  var socketHost = 'dhcp151078'; // todo unhardcode
  /*
  if (jQuery.browser.mozilla) {
      transports = ['xhr-multipart','websocket', 'flashsocket', 'htmlfile', 'xhr-polling'];
      socket = new io.Socket(socketHost, {transports: transports});
  } else {
      socket = new io.Socket(socketHost);
      
  }*/
  
  socket = new io.Socket(socketHost);
  
  socket.connect();

  log("is socket connecting? " + socket.connecting);
  log("is socket connected? " + socket.connected);
  
  var consoles = jQuery("#consoles").html();
  jQuery("#consoles").html("");
  
  jQuery('#start_build_button').click(function(){
    // todo - make sure that svn_url points to hedgehog, otherwise it's more likely
    // we could be building a malicious package
    obj = {};
    var svn_url = jQuery("#svn_url").val();
    var d = new Date();
    var timestamp = "" + d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) +
      pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds());
    var tmp = svn_url.replace(/\/$/, "").split("/");
    var pkg = tmp[tmp.length -1];
    var job_id = pkg + "_" + timestamp;
    obj['job_id'] = job_id;
    obj['svn_url'] = svn_url;
    obj['r_version'] = jQuery("#r_version").val();
    obj['repository'] = jQuery("#repository").val();
    obj['force'] = (jQuery("#force:checked").val() == 'true') ? true : false;
    var jsonStr = JSON.stringify(obj); // todo - make sure browser has this method, if not use Douglas Crockford's
    //log("sending json:\n" + jsonStr);
    jQuery("#build_start").html("<p><a href='/'>New Build</a><p>\n")
   socket.send(jsonStr); 
  })
  
  
  socket.on('connect', function(data) {
      log("in socket connect function");
      log("\tis socket connecting? " + socket.connecting);
      log("\tis socket connected? " + socket.connected);
      
  });
  
  socket.on('message', function(data){
    log("got message: " + data)
    obj = jQuery.parseJSON(data);
    if (obj['first_message']) {
        var s = "<b>Node: " + obj['builder_id'] + "</b><br/>\n";
        s += "<pre id='builder_" + obj['builder_id'] + "'>";
        s += obj['body']
        s += "</pre>\n<p>&nbsp;</p>\n";
        jQuery("#consoles").append(s)
    } else {
        var selector = "#builder_" + obj['builder_id'];
        jQuery(selector).append(obj['body']);
    }
    
  })
  
  
})

var pad = function(input) {
    var s = "" + input;
    if (s.length == 1) {
        return "0" + s;
    }
    return s;
}

