Deployment
==========



## Linux Install : 
```
git clone https://github.com/Bioconductor/packagebuilder.git
cd packagebuilder
```
**STOP** At this point, you need to determine if it's a new
or previously used build server.  If new (or simply a new install 
on the same server), you'll need to create a virtual environment.
To create a virtual environment, see : 

After you've activated the virtual environment, install the dependencies:
```
pip install --upgrade -r ./PIP-DEPENDENCIES*
```

Adjust bioconductor.properties (set environment to "production")

Crontab for biocadmin on `staging.bioconductor.org` : 
```
@reboot /home/biocadmin/spb_history/run-archiver.sh
@reboot /home/biocadmin/spb_history/run-django.sh
@reboot /home/biocadmin/spb_history/run-track_build_completion.sh
```
## Windows Install : 
RDP to moscato2 as pkgbuild
Open a Windows command prompt (cmd.exe)
#### If upgrading a previous installation
cd E:\packagebuilder
#### If upgrading a previous installation
cd E:\
git clone https://github.com/Bioconductor/packagebuilder.git
#### Once you have a copy
cd packagebuilder

RDP to moscato2 as Administrator (needed to change services)
Open cygwin
**Determine if service has been previously installed**
If it's already been installed, you'll see some output like this: 
```
$ cygrunsrv -Q "BioC Single Package Builder"
Service             : BioC Single Package Builder
Current State       : Stopped
Command             : /cygdrive/c/Python27/python e:/packagebuilder/server.py
```

You'll now see the service listed in Windows Services UI, when logged in
as the Administrator


The node and spb_history web applications are deployed on
staging.bioconductor.org
(see the 'single package builder' section of
biocadmin@staging.bioconductor.org's crontab
to see how they are started).

On the build machines, the listeners run as the user 'pkgbuild'
(which has the same password as the 'biocbuild' user).

On Mac and Linux, the listeners are started as follows:

    cd ~/packagebuilder
    nohup python server.py > server.log 2>&1 &

On Windows, the listener is configured as a service (called
BioC Single Package Builder) which can be restarted under
Control Panel:Services.
