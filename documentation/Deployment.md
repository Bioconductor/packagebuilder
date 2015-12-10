Deployment
==========



Install : 
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
