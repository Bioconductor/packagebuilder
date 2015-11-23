Deployment
==========

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
