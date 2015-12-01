NodeJS Web App Component
========================
**DEPRECATED**

Previously, we had deployed a web app (the code in the 'node' directory) written in
NodeJS as an additional SPB component.  Currently, it is disabled, but it was once
accessible at http://staging.bioconductor.org:4000 .

This application provided the following features :

1. A third option to kick off a build (in addition to the tracker and `rerun_build.py`)
2. A WebSocket approach to displaying messages once a build has begun (rather than
  requiring a user to refresh http://staging.bioconductor.org:8000/job/<id>
