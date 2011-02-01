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


//global variables
var gotSvnInfo = false;
var gotDcfInfo = false;
var nodes = [];

jQuery(function(){
    
  setupUI();
    
  var socket;
  
  socket = new io.Socket(socketHost);
  
  socket.connect();

  log("is socket connecting? " + socket.connecting);
  log("is socket connected? " + socket.connected);
  
  
  jQuery('#start_build_button').click(function(){
    // todo - make sure that svn_url points to hedgehog, otherwise it's more likely
    // we could be building a malicious package
    initUI();
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
    switch(obj['status']) {
        case 'svn_info':
            handleSvnInfo(obj);
            break;
        case 'dcf_info':
            handleDcfInfo(obj);
            break;
        case 'node_info':
            gotNewNode(obj);
            break;
        case 'build_not_required':
            handleBuildNotRequired(obj);
            break;
        case 'building':
            handleBuilding(obj);
            break;
        case 'complete':
            handleComplete(obj);
            break;
        case 'post_processing':
            handlePostProcessing(obj);
            break;
        case 'build_failed':
            handleBuildFailed(obj);
            break;
        default:
            break;
    }
    
    /*
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
    */
  })
  
  
})

var handleSvnInfo = function(message) {
    if (gotSvnInfo) return;
    gotSvnInfo = true;
    jQuery("#svn_info_snapshot_date").html(message['time']);
    jQuery("#svn_info_svn_url").html(message['URL']);
    jQuery("#svn_last_changed_rev").html(message['Last Changed Rev']);
    jQuery("#svn_revision").html(message['Revision']);
    jQuery("#svn_last_changed_date").html(message['Last Changed Date']);
}

var handleDcfInfo = function(message) {
    if (gotDcfInfo) return;
    gotDcfInfo = true;
    jQuery("#package_name").html(message['package_name']);
    jQuery("#package_version").html(message['version']);
    var maintainer = message['maintainer'].split(" <")[0];
    jQuery("#package_maintainer").html(maintainer);
}

var gotNewNode = function(message) {
    var nodeName = message['builder_id'];
    nodes.push(nodeName);
    
    var os = message['os'];
    var arch = message['arch'];
    
    //todo- grab this from html file instead of constructing string in js
	//<!-- change to e.g. nodeinfo_lamb2 -->
	var s = "";
	s += '<tr id="nodeinfo_' + nodeName + '">\n';
	//<!-- class should be e.g. "node lamb2" -->
	s += '<TD colspan="4" class="node ' + nodeName + '" style="text-align: left">\n';
	s+= '	<I id="nodeinfo_'+nodeName+'">' + nodeName + '</I>&nbsp;</TD>\n';
	//	<!-- class should be e.g. "node lamb2"-->
	s +='	<TD class="node ' + nodeName + '" style="text-align: left">\n';
	s +='		<SPAN style="font-size: smaller;">' + os +  '/' + arch +  '</SPAN>\n';
	s += '&nbsp;</TD><TD class="status ' + nodeName + ' buildsrc">\n';
	s += '<span id="'+nodeName+'_buildstatus"><a href="#' +nodeName+'_anchor"><SPAN class="IN_PROGRESS ' + nodeName + '_EVENT">&nbsp;IN&nbsp;PROGRESS&nbsp;</SPAN></a></span></TD>\n';
	s += '</tr>\n';

    jQuery("#nodeinfo_append_to_me").append(s);
    
    var summaryTemplate = jQuery("#summary_template").html();
    
    jQuery("#summaries").append(summaryTemplate.replace(/NODENAME/g, nodeName));
    
    
}


var handleEvent = function(event, node) {
    var msg;
    var selector = "." + node + "_EVENT";
    log("in handleEvent, node = " + node + ", event = " + event);
    jQuery(selector).removeClass("OK ERROR WARNINGS IN_PROGRESS skipped TIMEOUT");
    msg = "&nbsp;&nbsp;" + event.replace(/_/g, " ") + "&nbsp;&nbsp;";
    jQuery(selector).addClass(event);
    jQuery(selector).html(msg);
    
}

var handleBuildNotRequired = function(message) {
    var nodeName = message['builder_id'];
    var selector = "#" + nodeName + "_console"
    jQuery(selector).append(message['body']);
    handleEvent("skipped", nodeName);
}

var handleBuilding = function(message) {
    var nodeName = message['builder_id'];
    var selector = "#" + nodeName + "_console"
    jQuery(selector).append(message['body']);
}


var handleComplete = function(message) {
    var nodeName = message['builder_id'];
    handleEvent("OK", nodeName);
    
}

var handlePostProcessing = function(message) {
    var nodeName = message['builder_id'];
    if (message['retcode'] != 0) {
        handleEvent("ERROR", nodeName);
        message['body'] = "ERROR during step: " + message['body'];
    }
    selector = "#" + nodeName + "_post_processing";
    jQuery(selector).html(message['body']);
}


var handleBuildFailed = function(message) {
    var nodeName = message['builder_id'];
    handleEvent("ERROR", nodeName);
}

var setupUI = function() {
    jQuery("#summary_template").hide();
    jQuery("#initially_hidden").hide();
}


var initUI = function() {
    jQuery("#initially_hidden").show();
}


var pad = function(input) {
    var s = "" + input;
    if (s.length == 1) {
        return "0" + s;
    }
    return s;
}

