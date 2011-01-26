jQuery(function(){
  var socket = new io.Socket('dhcp151078') 
  socket.connect();
  
  
  var consoles = jQuery("#consoles").html();
  jQuery("#consoles").html("");
  
  jQuery('#start_build_button').click(function(){
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
    obj['force'] = (jQuery("#force:checked").val() == 'true') ? true : false;
    var jsonStr = JSON.stringify(obj); // todo - make sure browser has this method, if not use Douglas Crockford's
    //console.log("sending json:\n" + jsonStr);
    jQuery("#build_start").html("<p><a href='/'>New Build</a><p>\n")
   socket.send(jsonStr); 
  })
  
  socket.on('message', function(data){
    console.log("got message: " + data)
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

