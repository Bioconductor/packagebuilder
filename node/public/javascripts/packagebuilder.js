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

String.prototype.endsWith = function(suffix) {
    return this.indexOf(suffix, this.length - suffix.length) !== -1;
};

//global variables
var gotSvnInfo = false;
var gotDcfInfo = false;
var nodes = [];
var handledInvalidUrl = false;
var packageName;
var gotFirstNode = false;

jQuery(function(){
  
  jQuery("#svn_url").focus();
  setupUI();
    
  var socket;
  
  //socket = new io.Socket(socketHost);
  
  //socket.connect();
  
  socket = io.connect("http://" + socketHost + ":4000",
    {transports: ["websocket", "htmlfile", "xhr-polling", "jsonp-polling"]});


  // doesn't work. var session = socket.listener.server.viewHelpers;
  log("socket id = " + socket.id);
  log("is socket connecting? " + socket.connecting);
  log("is socket connected? " + socket.connected);
  
  
  jQuery('#start_build_button').click(function(){
    obj = {};
    obj['r_version'] = jQuery("#r_version").val();
    obj['repository'] = jQuery("#repository").val();

    /*
    if (obj['r_version'] == "2.14" && obj['repository'] == 'course') {
        alert("Packages in the course repository can only be built with R 2.13.");
        return;
    }
    */
    
    
    initUI();
    var svn_url = jQuery("#svn_url").val();
    var d = new Date();
    var timestamp = "" + d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) +
      pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds());
    var tmp = svn_url.replace(/\/$/, "").split("/");
    var pkg = tmp[tmp.length -1];
    if (pkg.endsWith(".tar.gz")) {
        tmp = pkg.split("_")
        pkg = tmp[0]
    }
    var job_id = pkg + "_" + timestamp;
    obj['job_id'] = job_id;
    d = new Date();
    obj['time'] = "" + d;
    obj['svn_url'] = svn_url;
    obj['force'] = (jQuery("#force:checked").val() == 'true') ? true : false;
    var jsonStr = JSON.stringify(obj); 
    jQuery("#build_start").html("<p><a href='/'>New Build</a><p>\n")
    log("sending message: " + jsonStr);
   socket.send(jsonStr); 
  })
  
  
  socket.on('connect', function(data) {
      log("in socket connect function");
      log("socket id = " + socket.clientId);
      
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
        case 'checking':
            handleChecking(obj);
            break;
        case 'buildingbin':
            handleBuildingBin(obj);
            break;
        case 'complete':
            handleComplete(obj);
            break;
        case 'post_processing':
            handlePostProcessing(obj);
            break;
        case 'post_processing_complete':
            handlePostProcessingComplete(obj);
            break;
        case 'build_failed':
            handleBuildFailed(obj);
            break;
        case 'r_cmd':
            handleBuildStart(obj);
            break;
        case 'r_buildbin_cmd':
            handleRBuildBinCmd(obj);
            break;
        case 'build_complete':
            handleBuildComplete(obj);
            break;
        case 'buildbin_complete':
            handleBuildBinComplete(obj);
            break;
        case 'invalid_url':
            handleInvalidUrl(obj);
            break;
        case 'check_cmd':
            handleCheckCmd(obj);
            break;
        case 'check_complete':
            handleCheckComplete(obj);
            break;
        case 'starting_buildbin':
            handleStartingBuildBin(obj);
            break;
        case 'skip_buildbin':
            handleSkipBuildBin(obj);
            break;
        default:
            break;
    }
    
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
    if (!gotDcfInfo) {
        gotDcfInfo = true;
        packageName = message['package_name'];
        jQuery("#package_name").html(packageName);
        jQuery("#package_version").html(message['version']);
        var maintainer = message['maintainer'].split(" <")[0];
        jQuery("#package_maintainer").html(maintainer);
    }
    var nodeName = message['builder_id'];
    jQuery("#" + nodeName + "_package_name").html(message['package_name']);
    jQuery("#" + nodeName + "_version").html(message['version']);
    
}

var gotNewNode = function(message) {
    var nodeName = message['builder_id'];
    nodes.push(nodeName);
    
    var os = message['os'];
    var arch = message['arch'];
    
    //todo- grab this from html file instead of constructing string in js
	//<!-- change to e.g. nodeinfo_lamb2 -->
	/*
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
    */
    
    s = jQuery("#appendMe").html().replace(/NODENAME/g, nodeName);
    s = s.replace(/<tr>/gi, "");
    s - s.replace(/<tbody>/gi, "");
    s = s.replace(/<\/tr>/gi, "");
    s - s.replace(/<\/tbody>/gi, "");
    
    
    jQuery("#nodeinfo_append_to_me").append(s);
    jQuery("#nodeinfo_" + nodeName).html(os + "/" + arch);
    
    var summaryTemplate = jQuery("#summary_template").html();
    
    jQuery("#summaries").append(summaryTemplate.replace(/NODENAME/g, nodeName));
    jQuery("#" + nodeName + "_r_version").html(message['r_version']);
    jQuery("#" + nodeName + "_build_id").html(message['job_id']);

    if (!gotFirstNode) {
        jQuery("#status_header").append(jQuery("#get_header_here").html());
    }
    gotFirstNode = true;
}


var handleEvent = function(event, node, stage) {
    var msg;
    var selector;
    if (stage == "build")
        selector = "." + node + "_EVENT";
    else
        selector = "." + node + "_" + stage.toUpperCase() + "_EVENT";
        
    log("in handleEvent, node = " + node + ", event = " + event, " stage = " + stage);
    jQuery(selector).removeClass("OK ERROR WARNINGS IN_PROGRESS skipped TIMEOUT");
    msg = "&nbsp;&nbsp;" + event.replace(/_/g, "&nbsp;") + "&nbsp;&nbsp;"; 
    jQuery(selector).addClass(event);
    jQuery(selector).html(msg);
    if (event == "ERROR" && stage == "build") {
        handleEvent("skipped", nodeName, "check");
        handleEvent("skipped", nodeName, "buildbin");
        handleEvent("skipped", nodeName, "postprocessing");
    }
    
}

var handleBuildNotRequired = function(message) {
    var nodeName = message['builder_id'];
    var selector = "#" + nodeName + "_console"
    jQuery(selector).append(message['body']);
    var script = 'source("http://bioconductor.org/course-packages/courseInstall.R")\n' +
        'courseInstall("' + packageName + '")';
    selector = "#" + nodeName + "_install_command";
    jQuery(selector).html(script); 
    handleEvent("skipped", nodeName, "build");
}

var handleBuilding = function(message) {
    var nodeName = message['builder_id'];
    var selector = "#" + nodeName + "_console"
    jQuery(selector).append(message['body']);
}

var handleChecking = function(message) {
    var nodeName = message['builder_id'];
    var selector = "#" + nodeName + "_check_console"
    jQuery(selector).append(message['body']);
}

var handleBuildingBin = function(message) {
    var nodeName = message['builder_id'];
    var selector = "#" + nodeName + "_buildbin_console"
    jQuery(selector).append(message['body']);
}



var handleComplete = function(message) {
    var nodeName = message['builder_id'];
    if (message['result'] == 0) {
        handleEvent("OK", nodeName, "postprocessing");
    } else {
        handleEvent("ERROR", nodeName, "postprocessing");
    }
}

var handleRBuildBinCmd = function(message) {
    var nodeName = message['builder_id'];
    jQuery("#" + nodeName + "_buildbin_command").html(message['body']);
}

var handleBuildComplete = function(message) {
    var nodeName = message['builder_id'];
    jQuery("#" + nodeName + "_ended_at").html(message['time']);
    jQuery("#" + nodeName + "_elapsed_time").html(message['elapsed_time']);
    jQuery("#" + nodeName + "_ret_code").html(message['result_code']);
    var status;
    if (message['result_code'] == 0) {
        if (message['warnings']) {
            status = "WARNINGS";
        } else {
            status = "OK";
        }
    } else {
        status = "ERROR";
    }
    handleEvent(status, nodeName, "build")
}

var handleBuildBinComplete = function(message) {
    var nodeName = message['builder_id'];
    jQuery("#" + nodeName + "_ended_at").html(message['time']);
    jQuery("#" + nodeName + "_elapsed_time").html(message['elapsed_time']);
    jQuery("#" + nodeName + "_ret_code").html(message['result_code']);
    var status;
    if (message['result_code'] == 0) {
        if (message['warnings']) {
            status = "WARNINGS";
        } else {
            status = "OK";
        }
    } else {
        status = "ERROR";
    }
    handleEvent(status, nodeName, "buildbin")
}


var handlePostProcessing = function(message) {
    var nodeName = message['builder_id'];
    if (message['retcode'] != 0) {
        handleEvent("ERROR", nodeName, "build");
        message['body'] = "ERROR during step: " + message['body'];
    }
    selector = "#" + nodeName + "_post_processing";
    jQuery(selector).append(message['body'] + "...");
    if (message['body'] == 'Synced repository to website' || message['body'] == "Skipped synchronization step") {
        jQuery(selector).append("DONE.");
    }
    if (message['build_product'] && message['url']) {
        var url = "<a href='"+ message['url']  + "'>" + message['build_product'] + "</a>"
        jQuery("#" + nodeName + "_build_product").html(url);
        var script;
        if (message['url'].match(/scratch/)) {
            script = 'source("http://bioconductor.org/scratch-repos/pkgInstall.R")\n' +
                'pkgInstall("' + packageName + '")';
        } else {
            script = 'source("http://bioconductor.org/course-packages/courseInstall.R")\n' +
                'courseInstall("' + packageName + '")';
        }
        jQuery("#" + nodeName + "_install_command").html(script);
    }
    if (message['filesize']) {
        jQuery("#" + nodeName + "_file_size").html(message['filesize']);
    }
}

var handlePostProcessingComplete = function(message) {
    var nodeName = message['builder_id'];
    if (message['retcode'] != 0) {
        handleEvent("ERROR", nodeName, "postprocessing"); 
    } else {
        handleEvent("OK", nodeName, "postprocessing");
    }
    
}

var handleBuildFailed = function(message) {
    var nodeName = message['builder_id'];
    handleEvent("ERROR", nodeName, "build");
}

var handleBuildStart = function(message) {
    var nodeName = message['builder_id'];
    jQuery("#" + nodeName + "_command").html(message['body'])
    jQuery("#" + nodeName + "_started_at").html(message['time']);
}

var handleInvalidUrl = function(message) {
    if (handledInvalidUrl) return;
    handledInvalidUrl = true;
    jQuery("#error").html(message['body']);
    jQuery("#initially_hidden").hide();
}

var handleCheckCmd = function(message) {
    var nodeName = message['builder_id'];
    // todo add time
    jQuery("#" + nodeName + "_check_command").html(message['body']);
    handleEvent("IN_PROGRESS", nodeName, "check") 
}

handleStartingBuildBin = function(message) {
    var nodeName = message['builder_id'];
    // todo add time
    handleEvent("IN_PROGRESS", nodeName, "buildbin")
}

handleSkipBuildBin = function(message) {
    var nodeName = message['builder_id'];
    // todo add time
    handleEvent("skipped", nodeName, "buildbin");
}

handleCheckComplete = function(message) {
    var nodeName = message['builder_id'];
    // todo add time
    var status;
    if (message['result_code'] == 0) {
        if (message['warnings']) {
            status = "WARNINGS"
        } else {
            status = "OK"
        }
    } else {
        status = "ERROR";
    }
    handleEvent(status, nodeName, "check");
}


var setupUI = function() {
    jQuery("#summary_template").hide();
    jQuery("#initially_hidden").hide();
    jQuery(".hideMe").hide();
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

