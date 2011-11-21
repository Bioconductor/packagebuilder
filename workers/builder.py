#!/usr/bin/env python


## Assume this script is started by a shell script which has read
## BBS variables and also changed to the correct directory.

import os
import sys
import json
import subprocess
import threading
import time
import datetime
import shlex
import platform
from stompy import Stomp


class Tailer(threading.Thread):
    def __init__(self, filename, status):
        threading.Thread.__init__(self)
        self.filename = filename
        self.status = status
        self.message_sequence = 1
        self._stop = threading.Event()
    def stop(self):
        self._stop.set()
    def stopped(self):
        return self._stop.isSet()
    def run(self):
        prevsize = 0
        while 1:
            time.sleep(0.2)
            print ("in tail loop (%s)" % self.status)
            #print ".",
            if not os.path.isfile(self.filename):
                continue
            st = os.stat(self.filename)
            if st.st_size == 0:
                continue
                
            
            if self.stopped():
                print ("stopped() == True (%s)" % self.status)
                num_bytes_to_read = st.st_size - prevsize
                f = open(self.filename, 'r')
                f.seek(prevsize)
                bytes = f.read(num_bytes_to_read)
                f.close()
                print bytes,
                sys.stdout.flush()
                send_message({"status": self.status, "sequence": self.message_sequence, "body": bytes})
                prevsize = st.st_size
                print "Thread says I'm done %s" % self.status
                break # not needed here but might be needed if program was to continue doing other stuff
                # and we wanted the thread to exit
            
            if (st.st_size > 0):
                print("st.st_size = %d, prevsize = %s" % (st.st_size, prevsize))
            if (st.st_size > 0) and (st.st_size > prevsize):
                num_bytes_to_read = st.st_size - prevsize
                f = open(self.filename, 'r')
                f.seek(prevsize)
                bytes = f.read(num_bytes_to_read)
                f.close()
                print bytes,
                sys.stdout.flush()
                send_message({"status": self.status, "sequence": self.message_sequence, "body": bytes})
                self.message_sequence += 1
                prevsize = st.st_size



def send_message(msg, status=None):
    merged_dict = {}
    merged_dict['builder_id'] = builder_id
    merged_dict['client_id'] = manifest['client_id']
    merged_dict['job_id'] = manifest['job_id']
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
    this_frame = stomp.send({'destination': "/queue/builderevents",
      'body': json_str,
      'persistent': 'true'})
    print("Receipt: %s" % this_frame.headers.get('receipt-id'))


def send_dcf_info(dcf_file):
    send_message({"status": "dcf_info", "package_name": dcf_file.getValue("Package"),
        "maintainer": dcf_file.getValue("Maintainer"), "version": dcf_file.getValue("Version")})

def is_build_required(manifest):
    if ("force" in manifest.keys()):
        if (manifest['force'] == True):
            return(True)
    
    global package_name
    package_name = manifest['job_id'].split("_")[0]
    if (is_svn_package()):
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

        
        svn_version = dcf_file.getValue("Version")
    else:
        tmp = manifest["svn_url"].split("/")
        pkgname = tmp[len(tmp)-1].replace(".tar.gz", "")
        svn_version = pkgname.split("_")[1]
            
    
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
    if (manifest['repository'] == 'course'):
        base_repo_url = "http://bioconductor.org/course-packages"
    elif (manifest['repository'] == 'scratch'):
        base_repo_url = "http://bioconductor.org/scratch-repos/%s" % manifest['r_version']
    
    repository_url = "%s/%s/PACKAGES" % (base_repo_url, cran_repo_map[pkg_type])
    # What if there is no file at this url?
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




def setup():
    global manifest
    global working_dir
    global BBScorevars
    global dcf
    global packagebuilder_ssh_cmd, packagebuilder_rsync_cmd, packagebuilder_rsync_rsh_cmd, \
        packagebuilder_scp_cmd
    global callcount
    global builder_id
    
    builder_id = os.getenv("BBS_NODE")
    
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
    print("working dir is %s" % working_dir)


def setup_stomp():
    global stomp
    try:
        stomp = Stomp("merlot2.fhcrc.org", 61613)
        # optional connect keyword args "username" and "password" like so:
        # stomp.connect(username="user", password="pass")
        stomp.connect()
    except:
        print("Cannot connect")
        raise
    

        


def svn_export():
    # Don't use BBS_SVN_CMD because it may not be defined on all nodes
    global package_name
    package_name = manifest['job_id'].split("_")[0]
    export_path = os.path.join(working_dir, package_name)
    svn_cmd = "svn --non-interactive --username %s --password %s export %s %s" % ( \
        os.getenv("SVN_USER"), os.getenv("SVN_PASS"), manifest['svn_url'], package_name)
    clean_svn_cmd = svn_cmd.replace(os.getenv("SVN_USER"),"xxx").replace(os.getenv("SVN_PASS"),"xxx")
    send_message({"status": "svn_cmd", "body": clean_svn_cmd})
    send_message({"status": "post_processing", "retcode": 0, "body": "starting svn export"})
    retcode = subprocess.call(svn_cmd, shell=True)
    send_message({"status": "post_processing", "retcode": retcode, "body": "finished svn export"})
    send_message({"status": "svn_result", "result": retcode, "body": \
        "svn export completed with status %d" % retcode})
    if (not retcode == 0):
        sys.exit("svn export failed")

def extract_tarball():
    global package_name
    package_name = manifest['job_id'].split("_")[0]
    # first, log in to the tracker and get a cookie
    cmd = """curl -s --cookie-jar cookies.txt -d\
 '__login_name=%s&__login_password=%s\
&__came_from=http://tracker.fhcrc.org/roundup/bioc_submit/\
&@action=login' \
http://tracker.fhcrc.org/roundup/bioc_submit/""" % \
    (os.getenv("TRACKER_LOGIN"), os.getenv("TRACKER_PASSWORD"))
    
    retcode = subprocess.call(cmd, shell=True)
    send_message({"status": "post_processing", "retcode": retcode, "body": \
      "curl to log into tracker returned status %d" % retcode})
    if (not retcode == 0):
        sys.exit("curl to get cookie failed")
    
    retcode = subprocess.call("curl -O -s --cookie cookies.txt %s" % \
        manifest['svn_url'], shell=True)
    send_message({"status": "post_processing", "retcode": retcode, "body": \
        "curl of tarball completed with status %d" % retcode})
    if (not retcode == 0):
        sys.exit("curl of tarball failed")
    
    
    tmp = manifest['svn_url'].split("/")
    tarball = tmp[len(tmp)-1]
    package_name = tarball.split("_")[0]
    
    os.rename(tarball, "%s.orig" % tarball)
    
    retcode = subprocess.call("tar -zxf %s.orig" % tarball, shell=True)
    send_message({"status": "post_processing", "retcode": retcode, "body": \
        "untar of tarball completed with status %d" % retcode})
    if (not retcode == 0):
        sys.exit("untar of tarball failed")
    
    f = open("%s/DESCRIPTION" % package_name)
    description = f.read()
    f.close()
    dcf_file = dcf.DcfRecordParser(description.rstrip().split("\n"))
    send_dcf_info(dcf_file)
    


def install_pkg_deps():
    f = open("%s/%s/DESCRIPTION" % (working_dir, package_name))
    description = f.read()
    f.close()
    desc = dcf.DcfRecordParser(description.rstrip().split("\n"))
    fields = ("Depends", "Imports", "Suggests", "Enhances")
    args = ""
    for field in fields:
        try:
            args += '%s="%s" ' % (field, desc.getValue(field))
        except KeyError:
            pass
    r_script = "%s/../../installPkgDeps.R" % working_dir
    log = "%s/installDeps.log" % working_dir
    cmd = "%s CMD BATCH -q --vanilla --no-save --no-restore --slave'--args %s'\
      %s %s" % (os.getenv("BBS_R_CMD"), args.strip(), r_script, log)
    send_message({"body": "Installing dependencies...", "status": "preprocessing", "retcode": 0})
    retcode = subprocess.call(cmd, shell=True)
    send_message({"body": "Result of installing dependencies: %d" % retcode,
      "status": "post_processing", "retcode": retcode})
    return retcode


def check_package():
    outfile = "Rcheck.out"
    if (os.path.exists(outfile)):
        os.remove(outfile)
    
    out_fh = open(outfile, "w")
    start_time = datetime.datetime.now()
    message_sequence = 1
    
    
    pkgname = manifest['job_id'].split("_")[0]
    files = os.listdir(os.getcwd())
    for file in files:
        if pkgname in file and ".tar.gz" in file:
            tarball = file
            break
    cmd = "%s CMD check --no-vignettes --timings %s" % (os.getenv('BBS_R_CMD'),
      tarball)
    background = Tailer(outfile, "checking")
    background.start()
    pope = subprocess.Popen(cmd, stdout=out_fh, stderr=subprocess.STDOUT, shell=True)
    pid = pope.pid
    
    retcode = pope.wait()
    
    stop_time = datetime.datetime.now()
    elapsed_time = str(stop_time - start_time)
    out_fh.close()
    background.stop()

    background.join()
    
    
    # check for warnings
    out_fh = open(outfile)
    warnings = False
    for line in out_fh:
        if line.rstrip().endswith("WARNING"):
            warnings = True
            break
    out_fh.close()
    
    send_message({"status": "check_complete", "result_code": retcode, "warnings": warnings,
        "body": "Check completed with status %d" % retcode, "elapsed_time": elapsed_time})
        
    
    return (retcode)


def build_package(source_build): # todo - refactor to allow either source or binary builds
    global pkg_type

    pkg_type = BBScorevars.getNodeSpec(builder_id, "pkgType")

    buildmsg = None
    if (source_build):
        buildmsg = "building"
    else:
        buildmsg = "buildingbin"
    print("in build_package, source_build is %s and buildmsg is %s." % (source_build, buildmsg))
    
    if ((not source_build) and (pkgType == "source")):
        send_message({"status": buildmsg, "body": "skipped"})
        return
        
    global message_sequence
    global warnings
    message_sequence = 1


    
    outfile = "R.out"
    if (os.path.exists(outfile)):
        os.remove(outfile)
    flags = "--keep-empty-dirs --no-resave-data"
        
    
    flags += " --no-vignettes"  ## be sure to comment this line!!!!!!! (used for testing, to speed up builds)
    
    out_fh = open(outfile, "w")
    start_time = datetime.datetime.now()
    buildmsg = None
    print("starting build tailer with message %s." % buildmsg)
    background = Tailer(outfile, buildmsg)
    background.start()
    
    if (source_build):
        r_cmd = "%s CMD build %s %s" % (os.getenv("BBS_R_CMD"), flags, package_name)
    else:
        #if builder_id == "cyclonus":
            #libdir = "C:/Users/pkgbuild/Documents/R/win-library/2.14"
        #else:
            #libdir = "libdir"
            #os.mkdir("libdir")
        #r_cmd = "%s CMD INSTALL --build --library=%s %s" % (os.getenv("BBS_R_CMD"),
        #  libdir, package_name)
        
        # todo, if mac, run build_universal script
        r_cmd = "%s CMD INSTALL --build %s" % (os.getenv("BBS_R_CMD"),
          package_name)
    status = None
    if (source_build):
        status = "r_cmd"
    else:
        status = "r_buildbin_cmd"
    send_message({"status": status, "body": r_cmd})
    print("before build, working dir is %s" % working_dir)
    retcode = subprocess.call(r_cmd, stdout=out_fh, stderr=subprocess.STDOUT, shell=True)
    stop_time = datetime.datetime.now()
    elapsed_time = str(stop_time - start_time)
    background.stop()
    out_fh.close()
    
    background.join()
    print "Done"
    
    # check for warnings
    out_fh = open(outfile)
    warnings = False
    for line in out_fh:
        if line.lower().startswith("warning:"):
            warnings = True
            break
    out_fh.close()
    
    send_message({"status": "build_complete", "result_code": retcode, "warnings": warnings,
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
    global url
    pkg_type = BBScorevars.getNodeSpec(builder_id, "pkgType")
    ext = BBScorevars.pkgType2FileExt[pkg_type]
    files = os.listdir(working_dir)
    build_product = filter(lambda x: x.endswith(ext), files)[0]
    
    
    # now install the package
    r_cmd = "%s CMD INSTALL %s" % (os.getenv("BBS_R_CMD"), build_product)
    
    send_message({"body": "Installing package", "status": "post_processing", "retcode": 0})
    
    retcode = subprocess.call(r_cmd, shell=True)
    
    send_message({"body": "Installed package", "status": "post_processing", "retcode": retcode})
    
    if retcode != 0:
        sys.exit("package install failed")
    
    
    if (platform.system() == "Darwin"):
        os_seg = "bin/macosx/leopard/contrib/%s" % manifest['r_version']
    elif (platform.system() == "Linux"):
        os_seg = "src/contrib"
    else:
        os_seg = "bin/windows/contrib/%s" % manifest['r_version']
    
    if (manifest['repository'] == 'course'):
        repos = "/loc/www/bioconductor-test.fhcrc.org/course-packages/%s" % os_seg
        url = repos.replace("/loc/www/bioconductor-test.fhcrc.org/","http://bioconductor.org/")
    elif (manifest['repository'] == 'scratch'):
        repos = '/loc/www/bioconductor-test.fhcrc.org/scratch-repos/%s/%s' % (manifest['r_version'], os_seg)
        url = repos.replace("/loc/www/bioconductor-test.fhcrc.org/scratch-repos/","http://bioconductor-test.org/scratch-repos/")
    
    
    
    url += "/" + build_product
    
    rawsize = os.path.getsize(build_product)
    kib = rawsize / float(1024)
    filesize = "%.2f" % kib
    
    files_to_delete = "%s/%s_*.%s" % (repos, package_name, ext)
    
    if (platform.system() == "Windows"):
        retcode = subprocess.call("c:/cygwin/bin/ssh.exe -qi c:/packagebuilder/.packagebuilder.private_key.rsa -o StrictHostKeyChecking=no biocadmin@merlot2.fhcrc.org 'rm -f %s/%s_*.zip'" % (repos, package_name))
    else:
        retcode = ssh("rm -f %s" % files_to_delete)
    
    print("result of deleting files: %d" % retcode)
    send_message({"body": "Pruning older packages from repository", "status": "post_processing", "retcode": retcode})
    if retcode != 0:
        sys.exit("repos prune failed")
    
    if (platform.system() == "Windows"):
        print("platform.system() == 'Windows', running chmod commands...")
        chmod_retcode = subprocess.call("chmod a+r %s" % os.path.join(working_dir, package_name))
        print("chmod_retcode = %d" % chmod_retcode)
        send_message("chmod_retcode=%d" % chmod_retcode)
        command = "c:/cygwin/bin/scp.exe -qi c:/packagebuilder/.packagebuilder.private_key.rsa -o StrictHostKeyChecking=no %s biocadmin@merlot2.fhcrc.org:%s/" % (build_product, repos)
        print("command = %s" % command)
        retcode = subprocess.call(command)
        remote_chmod_retcode = subprocess.call("c:/cygwin/bin/ssh.exe -qi c:/packagebuilder/.packagebuilder.private_key.rsa -o StrictHostKeyChecking=no biocadmin@merlot2.fhcrc.org 'chmod a+r %s/%s_*.zip'" % (repos, package_name))
        print("remote_chmod_retcode = %s" % remote_chmod_retcode)
    else:
        print("chmod code not run, because platform.system() == %s" % platform.system())
        retcode = scp(build_product, repos)
    
    print("result of copying file: %d" % retcode)
    send_message({"body": "Copied build file to repository", "status": "post_processing", "retcode": retcode,
        "build_product": build_product, "filesize": filesize})
    if retcode != 0:
        sys.exit("copying file to repository failed")

## todo - get rid of ugly workarounds
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

def ssh(command, user='biocadmin', host='merlot2.fhcrc.org'):
    command = "%s %s@%s '%s'" % (packagebuilder_ssh_cmd, user, host, command)
    print("ssh command: %s" % command)
    retcode = _call([command], shell=True)
    return(retcode)

def scp(src, dest, srcLocal=True, user='biocadmin', host='merlot2.fhcrc.org'):
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
    
    if (manifest['repository'] == 'course'):
        script_loc = "/loc/www/bioconductor-test.fhcrc.org/course-packages"
    elif (manifest['repository'] == 'scratch'):
        script_loc = "/loc/www/bioconductor-test.fhcrc.org/scratch-repos/%s" % manifest['r_version']
    
    if pkg_type == "mac.binary.leopard":
        pkg_type = "mac.binary"
    command = \
        "%s biocadmin@merlot2.fhcrc.org 'R -f %s/update-repo.R --args %s %s'" \
        % (packagebuilder_ssh_cmd, script_loc, repos, pkg_type)
    print("update packages command: ")
    print(command)
    retcode = subprocess.call(command, shell=True)
    print "retcode for update packages: %d" % retcode
    send_message({"status": "post_processing", "retcode": retcode, "body": "Updated packages list"})
    if retcode != 0:
        sys.exit("Updating packages failed")
    if (manifest['repository'] == 'course' or manifest['repository'] == 'scratch'):
        command = "%s biocadmin@merlot2.fhcrc.org \"cd /home/biocadmin/bioc-test-web/bioconductor.org && rake deploy_production\"" % \
            packagebuilder_ssh_cmd
        print("sync command = ")
        print(command)
        retcode = subprocess.call(command, shell=True)
        send_message({"status": "post_processing", "retcode": retcode, "body": "Synced repository to website",
            "build_product": build_product, "url": url})
        if retcode != 0:
            sys.exit("Sync to website failed")


def get_r_version():
    print("BBS_R_CMD == %s" % os.getenv("BBS_R_CMD"))
    r_version_raw, stderr = subprocess.Popen([os.getenv("BBS_R_CMD"),"--version"], stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT).communicate()
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


def is_valid_url():
    if (manifest['svn_url'].lower().startswith("https://hedgehog.fhcrc.org")):
        svn_url = True
    elif (manifest['svn_url'].lower().find("tracker.fhcrc.org") > -1): # todo, ensure .tar.gz end
        svn_url = False
    else:
        return False
    
    if svn_url:
        description_url = manifest['svn_url'].rstrip("/") + "/DESCRIPTION"
        description = subprocess.Popen(["curl", "-k", "-s",
            "--user", "%s:%s" % (os.getenv("SVN_USER"), os.getenv("SVN_PASS")),
            description_url], stdout=subprocess.PIPE).communicate()[0]
        if (len(description) == 0  or description.lower().find("404 not found") > -1):
            return False
        return True
    return True

def is_svn_package():
    if (manifest['svn_url'].lower().startswith("https://hedgehog.fhcrc.org")):
        return True
    return False



## Main namespace. execution starts here.
if __name__ == "__main__":
    if (len(sys.argv) < 2):
        sys.exit("builder.py started without manifest file and R version arguments, exiting...")
    
    print "Builder has been started"
    setup()
    setup_stomp()
    
    send_message("Builder has been started")
    
    
    if not is_valid_url():
        send_message({"status": "invalid_url", "body": "Invalid SVN url."})
        sys.exit(0)

    
    get_node_info()
    if is_svn_package():
        svn_info()
    
    
    is_build_required = is_build_required(manifest)
    if not (is_build_required):
        pkg_type = 'svn' if (is_svn_package()) else 'tarball'
        send_message({"status": "build_not_required",
            "body": "Build not required (versions identical in %s and repository)."\
            % pkg_type})
        send_message({"status": "normal_end", "body": "Build process is ending normally."})
        sys.exit(0)
    
    if (is_svn_package()):
        svn_export()
    else:
        extract_tarball()
    
    result = install_pkg_deps()
    if (result != 0):
        sys.exit(0)
    
    result = build_package(True)
    if (result == 0):
        check_result = check_package()
        if check_result == 0:
            buildbin_result = build_package(False)
            if buildbin_result == 0:
                propagate_package()
        if (is_build_required):
            update_packages_file()
        if warnings: # todo separate build / check / build bin warnings
            body = "Build completed with warnings."
        else:
            body = "Build was successful."
        # todo - rethink completion
        send_message({"status": "complete", "result": result, "body": body, "warnings": warnings})
    else:
        send_message({"status": "build_failed", "retcode": result, "body": "build failed"})
    
    