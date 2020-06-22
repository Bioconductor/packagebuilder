Update After Release
====================

### Website Config File

1. Update the website config.yaml file `http://bioconductor.org/config.yaml`
There is a section for `Single Package Builder:` ; change the BioC and R
versions accordingly.

**Note:** We used to do this last but the code in the single package builder uses the config file to determine the version of R packages to download. This has to be updated before testing builds on the nodes or all packages will be redownloaded in individual R-libs directory

### Bioc-common-python (Deploy on all build nodes and staging)

Update BIOC_R_MAP in bioconductor/config.py file and push to github~ don't forget to push!

To initilize this change on all nodes and staging

1. git pull
2. initialize virtual environment
3. pip3 install --upgrade -r ./PIP-DEPENDENCIES--bioc-common-python.txt
4. python3 setup.py install
5. cd ../packagebuilder
6. pip3 install --upgrade -r ./PIP-DEPENDENCIES--packagebuilder.txt

**Note:** Use `pip` and `python` instead of `pip3` and `python3` on the
Windows builder.

### Packagebuilder (build nodes)

1. Update bioconductor.properties file for new version of BioC
2. Update \<machine\>.properties file (If new version of R)

(**Best Practice:** After these changes and the one below restart listeners on build nodes)

**NOTE:** Don't forget to go to old build nodes and kill the listeners and comment
out the crontab jobs

### spb_history (staging)

1. Update staging.properties file for new builder nodes 
2. Update bioconductor.properties file for new version of BioC
3. Update \<machine\>.properties file (If new version of R)
4. Create the needed directory struture at
`/loc/www/bioconductor-test.fhcrc.org/scratch-repos`
5. Update
`/loc/www/bioconductor-test.fhcrc.org/scratch-repos/<BiocVersion>/update-repo.R`
for new mac binary (if necessary)
6. Update viewhistory/helper.py to account for new BioC and R versions

(**Best Practice:** After these changes and the one below restart spb on staging)

