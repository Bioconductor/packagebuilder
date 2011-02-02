#!/usr/bin/env python


## Assume this script is started by a shell script which has read 
## BBS variables and also changed to the correct directory.

import pika
import os
import sys
import json
import subprocess
import thread
import time
import datetime
import shlex
import platform
    


def send_message(msg, status=None):
    merged_dict = {}
    merged_dict['builder_id'] = builder_id
    merged_dict['originating_host'] = manifest['originating_host']
    merged_dict['client_id'] = manifest['client_id']
    now = datetime.datetime.now()
    merged_dict['time'] = str(now)
    if type(msg) is dict:
        merged_dict.update(msg)
        if not ('status' in merged_dict.keys()):
            if not (status == None):
                merged_dict['status'] = status
    else:
        merged_dict['body'] = msg
        if not (status == None):
            merged_dict['status'] = status
    json_str = json.dumps(merged_dict)
    print "sending message:"
    print json_str
    print
    channel.basic_publish(exchange='from_worker_exchange',
                          routing_key="key.frombuilders",
                          body= json_str)


def send_dcf_info(dcf_file):
    send_message({"status": "dcf_info", "package_name": dcf_file.getValue("Package"),
        "maintainer": dcf_file.getValue("Maintainer"), "version": dcf_file.getValue("Version")})

def is_build_required(manifest):
    global package_name
    package_name = manifest['job_id'].split("_")[0]
    description_url = manifest['svn_url'].rstrip("/") + "/DESCRIPTION"
    print "description_url = " + description_url
    print "svn_user ="  + os.getenv("SVN_USER")
    print "svn_pass = " + os.getenv("SVN_PASS")
    try:
        
        description = subprocess.Popen(["curl", "-k", "-s", 
            "--user", "%s:%s" % (os.getenv("SVN_USER"), os.getenv("SVN_PASS")),
            description_url], stdout=subprocess.PIPE).communicate()[0] # todo - handle it if description does not exist
    except:
        print "Unexpected error:", sys.exc_info()[0]

    print "debug -- description ="
    print description
    print "description length = %d" % len(description)
    
    dcf_file = dcf.DcfRecordParser(description.rstrip().split("\n"))
    send_dcf_info(dcf_file)
    
    if ("force" in manifest.keys()):
        if (manifest['force'] == True):
            return(True)

    svn_version = dcf_file.getValue("Version")
            
    bioc_r_map = {"2.7": "2.12", "2.8": "2.13", "2.9": "2.14", "2.10": "2.15"} # need a better way to determine R version
    r_version = bioc_r_map[os.getenv("BBS_BIOC_VERSION")]
    pkg_type = BBScorevars.getNodeSpec(builder_id, "pkgType")
    
    cran_repo_map = { \
        'source': "src/contrib", \
        'win.binary': "bin/windows/contrib/" + r_version, \
        'win64.binary': "bin/windows64/contrib/" + r_version, \
        'mac.binary.leopard': "bin/macosx/leopard/contrib/" + r_version \
    }
    # todo - put repos url in config file (or get it from user)
    repository_url = "http://bioconductor.org/course-packages/%s/PACKAGES" % cran_repo_map[pkg_type]
    packages = subprocess.Popen(["curl", "-k", "-s", repository_url],
        stdout=subprocess.PIPE).communicate()[0]
    inpackage = False
    repository_version = False
    for line in packages.split("\n"):
        if line == "Package: %s" % package_name:
            inpackage = True
        if (line.startswith("Version: ") and inpackage):
            repository_version = line.split(": ")[1]
            break
    if not repository_version:
        return True # package hasn't been pushed to repo before
    print "[%s] svn version is %s, repository version is %s" % (package_name, svn_version,
        repository_version)
    return(svn_version != repository_version)


def tail(filename):
    global thread_is_done
    global message_sequence
    prevsize = 0
    while 1:
        time.sleep(0.2)
        #print ".",
        if not os.path.isfile(filename):
            continue
        st = os.stat(filename)
        if st.st_size == 0:
            continue
        if stop_thread == True:
            num_bytes_to_read = st.st_size - prevsize
            f = open(filename, 'r')
            f.seek(prevsize)
            bytes = f.read(num_bytes_to_read)
            f.close()
            print bytes,
            sys.stdout.flush()
            send_message({"status": "building", "sequence": message_sequence, "body": bytes})
            prevsize = st.st_size
            thread_is_done = True
            print "Thread says I'm done"
            break # not needed here but might be needed if program was to continue doing other stuff
            # and we wanted the thread to exit

        if (st.st_size > 0) and (st.st_size > prevsize):
            num_bytes_to_read = st.st_size - prevsize
            f = open(filename, 'r')
            f.seek(prevsize)
            bytes = f.read(num_bytes_to_read)
            f.close()
            print bytes,
            sys.stdout.flush()
            send_message({"status": "building", "sequence": message_sequence, "body": bytes})
            message_sequence += 1
            prevsize = st.st_size


def setup():
    global manifest
    global working_dir
    global BBScorevars
    global dcf
    global packagebuilder_ssh_cmd, packagebuilder_rsync_cmd, packagebuilder_rsync_rsh_cmd, \
        packagebuilder_scp_cmd
    global callcount
    callcount = 1

    ## BBS-specific imports
    BBS_home = os.environ['BBS_HOME']
    sys.path.append(BBS_home)
    import BBScorevars
    sys.path.append(os.path.join(BBS_home, "test/python"))
    import dcf

    
    packagebuilder_ssh_cmd = BBScorevars.ssh_cmd.replace(os.environ["BBS_RSAKEY"], os.environ["PACKAGEBUILDER_RSAKEY"])
    packagebuilder_rsync_cmd = BBScorevars.rsync_cmd.replace(os.environ["BBS_RSAKEY"], os.environ["PACKAGEBUILDER_RSAKEY"])
    packagebuilder_rsync_rsh_cmd = BBScorevars.rsync_rsh_cmd.replace(os.environ["BBS_RSAKEY"], \
        os.environ["PACKAGEBUILDER_RSAKEY"])
    packagebuilder_scp_cmd = packagebuilder_ssh_cmd.replace("ssh", "scp", 1)
    
    if (platform.system() == "Windows"):
        packagebuilder_scp_cmd = "c:/cygwin/bin/scp.exe -qi %s -o StrictHostKeyChecking=no" % \
            os.environ["PACKAGEBUILDER_RSAKEY"]
        packagebuilder_ssh_cmd = "c:/cygwin/bin/ssh.exe -qi %s -o StrictHostKeyChecking=no" % \
            os.environ["PACKAGEBUILDER_RSAKEY"]


    print("argument is %s" % sys.argv[1])
    print("cwd is %s" % os.getcwd())
    manifest_fh = open(sys.argv[1], "r")
    manifest_json = manifest_fh.read()
    manifest_fh.close()
    print("manifest_json is %s" % manifest_json)
    manifest = json.loads(manifest_json)
    working_dir = os.path.split(sys.argv[1])[0]
    os.chdir(working_dir)

def setup_pika():
    global channel
    global builder_id
    
    connection = pika.AsyncoreConnection(pika.ConnectionParameters(
            host='merlot2.fhcrc.org'))
    channel = connection.channel()

    builder_id = os.getenv("BBS_NODE")

    from_web_exchange = channel.exchange_declare(exchange="from_web_exchange",type="fanout")
    from_worker_exchange = channel.exchange_declare(exchange="from_worker_exchange", type='fanout')

    from_web_queue = channel.queue_declare(exclusive=True)
    from_web_queue_name = from_web_queue.queue

    channel.queue_bind(exchange='from_web_exchange', queue=from_web_queue_name)
        

def svn_export():
    # Don't use BBS_SVN_CMD because it may not be defined on all nodes
    global package_name
    package_name = manifest['job_id'].split("_")[0]
    export_path = os.path.join(working_dir, package_name)
    svn_cmd = "svn --non-interactive --username %s --password %s export %s %s" % ( \
        os.getenv("SVN_USER"), os.getenv("SVN_PASS"), manifest['svn_url'], package_name)
    clean_svn_cmd = svn_cmd.replace(os.getenv("SVN_USER"),"xxx").replace(os.getenv("SVN_PASS"),"xxx")
    send_message({"status": "svn_cmd", "body": clean_svn_cmd})
    retcode = subprocess.call(svn_cmd, shell=True)
    send_message({"status": "svn_result", "result": retcode, "body": \
        "svn export completed with status %d" % retcode})
    
def build_package():
    global stop_thread
    global message_sequence
    global thread_is_done
    stop_thread = False
    thread_is_done = False
    message_sequence = 1



    outfile = "R.out"
    if (os.path.exists(outfile)):
        os.remove(outfile)
    pkg_type = BBScorevars.getNodeSpec(builder_id, "pkgType")
    if pkg_type == "source":
        flags = ""
    else:
        flags = "--binary"
        
        
    #flags += " --no-vignettes"  ## be sure to comment this line!!!!!!! (used for testing, to speed up builds)
    
    out_fh = open(outfile, "w")
    start_time = datetime.datetime.now()
    thread.start_new(tail,(outfile,))
    r_cmd = "%s CMD build %s %s" % (os.getenv("BBS_R_CMD"), flags, package_name)
    send_message({"status": "r_cmd", "body": r_cmd})
    retcode = subprocess.call(r_cmd, stdout=out_fh, stderr=subprocess.STDOUT, shell=True)
    stop_time = datetime.datetime.now()
    elapsed_time = str(stop_time - start_time)
    stop_thread = True # tell thread to stop
    out_fh.close()

    while thread_is_done == False: pass # wait till thread tells us to stop
    print "Done"


    send_message({"status": "build_complete", "result_code": retcode,
        "body": "Build completed with status %d" % retcode, "elapsed_time": elapsed_time})
    return (retcode)

def svn_info():
    #global manifest
    print "svn_url is %s" % manifest['svn_url']
    svn_info = subprocess.Popen(["svn", "info", manifest['svn_url']], \
        stdout=subprocess.PIPE).communicate()[0]
    dcf_records = dcf.DcfRecordParser(svn_info.rstrip().split("\n"))
    keys = ['Path', 'URL', 'Repository Root', 'Repository UUID', 'Revision', 'Node Kind',
        'Last Changed Author', 'Last Changed Rev', 'Last Changed Date']
    svn_hash = {}
    for key in keys:
        svn_hash[key] = dcf_records.getValue(key)
    svn_hash['status'] = "svn_info"
    svn_hash['body'] = "svn info"
    send_message(svn_hash)


## todo - get rid of ugly windows workarounds now that we know how
def propagate_package():
    global build_product
    global repos
    global pkg_type
    pkg_type = BBScorevars.getNodeSpec(builder_id, "pkgType")
    ext = BBScorevars.pkgType2FileExt[pkg_type]
    files = os.listdir(working_dir)
    build_product = filter(lambda x: x.endswith(ext), files)[0]
    
    if (platform.system() == "Darwin"):
        os_seg = "bin/macosx/leopard/contrib/%s" % manifest['r_version']
    elif (platform.system() == "Linux"):
        os_seg = "src/contrib"
    else:
        os_seg = "bin/windows/contrib/%s" % manifest['r_version']
    
    
    repos = "/loc/www/bioconductor-test.fhcrc.org/course-packages/%s" % os_seg
    
    
    url = repos.replace("/loc/www/bioconductor-test.fhcrc.org/","http://bioconductor.org/")
    url += "/" + build_product
    
    rawsize = os.path.getsize(build_product)
    kib = rawsize / float(1024)
    filesize = "%.2f" % kib
    
    files_to_delete = "%s/%s_*.%s" % (repos, package_name, ext)
    
    if (platform.system() == "Windows"):
        retcode = subprocess.call("c:/cygwin/bin/ssh.exe -qi e:/packagebuilder/.packagebuilder.private_key.rsa -o StrictHostKeyChecking=no biocadmin@merlot2 'rm -f /loc/www/bioconductor-test.fhcrc.org/course-packages/bin/windows/contrib/2.12/%s_*.zip'" % package_name)
    else:
        retcode = ssh("rm -f %s" % files_to_delete) 

    print("result of deleting files: %d" % retcode)
    send_message({"body": "Pruning older packages from repository", "status": "post_processing", "retcode": retcode})
    if retcode != 0:
        sys.exit("repos prune failed")

    if (platform.system() == "Windows"):
        chmod_retcode = subprocess.call("chmod a+r %s" % os.path.join(working_dir, package_name))
        print("chmod_retcode = %d" % chmod_retcode)
        send_message("chmod_retcode=%d" % chmod_retcode)
        command = "c:/cygwin/bin/scp.exe -qi e:/packagebuilder/.packagebuilder.private_key.rsa -o StrictHostKeyChecking=no  %s biocadmin@merlot2:/loc/www/bioconductor-test.fhcrc.org/course-packages/bin/windows/contrib/2.12/" % build_product
        print("command = %s" % command)
        retcode = subprocess.call(command)
    else:
        retcode = scp(build_product, repos)
    
    print("result of copying file: %d" % retcode) 
    send_message({"body": "Copied build file to repository", "status": "post_processing", "retcode": retcode,
        "build_product": build_product, "url": url, "filesize": filesize})
    if retcode != 0:
        sys.exit("copying file to repository failed")

def _call(command_str, shell):
    global callcount
    if (platform.system() == "Windows"):
        #args = shlex.split(command_str)
        #return(subprocess.call(args, shell=shell))
        stdout_fn = os.path.join(working_dir, "%dout.txt" % callcount)
        stderr_fn = os.path.join(working_dir, "%derr.txt" % callcount)
        
        stdout_fh = open(stdout_fn, "w")
        stderr_fh = open(stderr_fn, "w")
        
        callcount += 1
        # ignore shell arg
        #retcode = subprocess.call(command_str, shell=False, stdout=stdout_fh, stderr=stderr_fh)
        print("right before _call, command_str is")
        command_str = str(command_str)
        print("size = %d" % len(command_str))
        print(command_str)
        retcode = subprocess.call(command_str, shell=False, stdout=stdout_fh, stderr=stderr_fh)
        stdout_fh.close()
        stderr_fh.close()
        return(retcode)
    else:
        return(subprocess.call(command_str, shell=shell))

def ssh(command, user='biocadmin', host='merlot2'):
    command = "%s %s@%s '%s'" % (packagebuilder_ssh_cmd, user, host, command)
    print("ssh command: %s" % command)
    retcode = _call([command], shell=True) 
    return(retcode)

def scp(src, dest, srcLocal=True, user='biocadmin', host='merlot2'):
    if (srcLocal):
        chmod_cmd = "chmod a+r %s" % src
        chmod_retcode = _call([chmod_cmd], shell=True) #todo abort build if retcode != 0
        send_message({"status": "post_processing", "retcode": chmod_retcode, "body": \
            "Set read permissions on build product"})
        if chmod_retcode != 0:
            sys.exit("chmod failed")
        print("chmod retcode: %s" % chmod_retcode)
        send_message("chmod_retcode = %d" % chmod_retcode)
        command = "%s %s %s@%s:%s" % (packagebuilder_scp_cmd, src, user, host, dest)
    else:
        command = "%s %s@%s:%s %s" % (packagebuilder_scp_cmd, user, host, src, dest)
    print("scp command: %s" % command)
    retcode = _call([command], shell=True)
    
    
    return(retcode)



def update_packages_file():
    global repos
    global pkg_type
    if pkg_type == "mac.binary.leopard":
        pkg_type = "mac.binary"
    command = \
        "%s biocadmin@merlot2 'R -f /loc/www/bioconductor-test.fhcrc.org/course-packages/update-course-repo.R --args %s %s'" \
        % (packagebuilder_ssh_cmd, repos, pkg_type)
    print("update packages command: ")
    print(command)
    retcode = subprocess.call(command, shell=True) 
    print "retcode for update packages: %d" % retcode
    send_message({"status": "post_processing", "retcode": retcode, "body": "Updated packages list"})
    if retcode != 0:
        sys.exit("Updating packages failed")
    
    command = "%s biocadmin@merlot2 \"cd /home/biocadmin/bioc-test-web/bioconductor.org && rake deploy_production\"" % \
        packagebuilder_ssh_cmd
    print("sync command = ")
    print(command)
    retcode = subprocess.call(command, shell=True)
    send_message({"status": "post_processing", "retcode": retcode, "body": "Synced repository to website"})
    if retcode != 0:
        sys.exit("Sync to website failed")
    
    

def get_r_version():
    print("BBS_R_CMD == %s" % os.getenv("BBS_R_CMD"))
    r_version_raw = subprocess.Popen([os.getenv("BBS_R_CMD"),"--version"], stdout=subprocess.PIPE).communicate()[0]
    lines = r_version_raw.split("\n")
    r_version_line = lines[0]
    return r_version_line.replace("R version ", "")

def get_node_info():
    r_version = get_r_version()
    os = BBScorevars.getNodeSpec(builder_id, "OS")
    arch = BBScorevars.getNodeSpec(builder_id, "Arch")
    plat = BBScorevars.getNodeSpec(builder_id, "Platform")
    send_message({"status": "node_info", "r_version": r_version,
        "os": os, "arch": arch, "platform": plat, "body": "node_info"})
    
       

## Main namespace. execution starts here.
if __name__ == "__main__":
    if (len(sys.argv) < 2):
        sys.exit("builder.py started without manifest file and R version arguments, exiting...")

    print "Builder has been started"
    setup()
    setup_pika()
    get_node_info()
    svn_info()
    
    send_message("Builder has been started")
    is_build_required = is_build_required(manifest)
    if not (is_build_required):
        send_message({"status": "build_not_required",
            "body": "Build not required (versions identical in svn and repository)."})
        send_message({"status": "normal_end", "body": "Build process is ending normally."})
        sys.exit(0)

    svn_export()
    result = build_package()
    if (result == 0):
        propagate_package()
        if (is_build_required):
            update_packages_file()
        send_message({"status": "complete", "result": result, "body": "All build processes have finished successfully."})
    else:
        send_message({"status": "build_failed", "retcode": result, "body": "build failed"})
    