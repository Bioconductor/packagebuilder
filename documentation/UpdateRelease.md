Update After Release
====================
### Bioc-common-python (Deploy on all build nodes and staging)

Update BIOC_R_MAP in bioconductor/config.py file.

To initilize this change on all nodes and staging

1. git pull
2. initialize virtual environment
3. python setup.py install

### Packagebuilder (build nodes)

1. Update bioconductor.properties file for new version of BioC
2. Update \<machine\>.properties file (If new version of R)

(**Best Practice:** After these changes and the one below restart listeners on build nodes)

**NOTE:** Don't forget to go to old build nodes and kill the listeners and comment
out the crontab jobs

### spb_history (staging)

1. Update bioconductor.properties file for new version of BioC
2. Update \<machine\>.properties file (If new version of R)
3. Create the needed directory struture at
`loc/www/bioconductor-test.fhcrc.org/scratch-repos`
4. Update viewhistory/helper.py to account for new BioC and R versions

(**Best Practice:** After these changes and the one below restart spb on staging)

### Website Config File

1. Update the website config.yaml file `http://bioconductor.org/config.yaml`
There is a section for `Single Package Builder:` ; change the BioC and R
versions accordingly.