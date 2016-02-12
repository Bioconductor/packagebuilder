# Moving Bioconductor Contributed Package Tracking to GitHub

## Overview

The plan is to move new/contributed package reviews to GitHub. The timeline for starting this is after the
release of Bioconductor 3.3, sometime in March/April 2016.

This plan will imply the following changes:


| What | Old Way | New Way |
|-------|-----|-------|
|  Package Source | Tarball posted to tracker | GitHub repository created by package author | 
| Tracking Software | Roundup issue tracker | GitHub issues | 
| Visibility | Private | Public |

## Workflow

* Package contributor creates a GitHub repository containing their package.
* Contributor opens new issue under Bioconductor/NewPackages. Issue name should be that of their
  package. Issue content should follow a standardized format and be machine-readable, the most
  important piece of info that needs to be in the issue is the URL to their github repository.
  I **don't** think we should have them fill out a [template](https://github.com/ropensci/onboarding/blob/master/CONTRIBUTING.md)
  like on ROpenSci, since that seems very old school, plus most of the questions asked
  in the template can be answered by SPB/BiocCheck.
* The creation of this issue will notify us and we can manually 'approve' the issue
  to be built by the SPB. Maybe later we will decide this step is not necessary but
  I want to guard against 1) malicious packages, 2) inappropriate use of SPB
  (people using it to test non-bioc pkgs) and 3) overloading our build resources.
  Once we have approved the issue, then our approval:
* ...will trigger the SPB to run on the github repos they have specified
  (or if the SPB can't determine that, it will post an issue saying so). The SPB will
  post to the issue with a link to the build report. It will also include instructions for
  setting up a webhook on the contributor's github repos which will notify us of new pushes.
  The contributor MUST do this, although I suppose we could poll for new commits once a 
  day if they fail to do so.
* At this point we can use all the features of github issues--assigning them to various
  members of the team (this can be done programmatically, maybe BiocContributions can
  be modified to do so) and assigning labels to the issue to indicate the status
  of the package in the review process. Finally, closing the issue indicates that the package
  has been fully (beyond pre-) accepted (or closed for some other reason, the reason should
  be indicated in the issue).
* As in the current tracker, once the package has been accepted, the canonical repo for it
  (as far as our build system is concerned) will be in OUR version control system, be it
  svn, or (eventually) git. The contributor can still use their original git repos for 
  development and use some mechanism to keep it in sync with our VCS. While we are
  using SVN, that mechanism is the current git mirrors; when we switch to using
  Git as our VCS, they would presumably add a new remote (ours) to their repos.

## Work that needs to be done to get there

* Document what contributor needs to do
* Write a small web app that listens for new issues in Bioconductor/NewPackagages and
  push hook messages and notifies the SPB.
* Modify SPB to be able to build from git repos, and to post reports to github issues 
 (should use GitHub API for this).



## Other considerations

* We should come up with a way to limit access to the spb. Do we want anyone who 
  adds an issue/web hook to be able to use the SPB or do we want to pre-approve them somehow?
  Should we be concerned about abuse of the builder?
* I am open to total reimplementation of SPB. Using Jenkins or Travis/AppVeyor (and
  something else maybe for Mac). I guess this depends to some extent on resolving
  the long-running stability/communication issues with the current SPB.
* What about experiment data packages? Can we leverage 
 [Github's support of Large File Storage](https://github.com/blog/1986-announcing-git-large-file-storage-lfs)
 for this?
* What about the legacy tracker? Do we want to keep it around? That implies keeping 
 several PB (!) of old tarballs around, which is possible thanks to hosting
 at FHCRC. But we probably can't continue that hosting long-term.
* If we don't remove the old tracker altogether, we should disable logins on it and 
  let visitors know that they should be using the new sytem.


## Web App Functionality

* Respond to new issues in Bioconductor/NewPackages, send to spb.
* With further updates, respond to GitHub web hooks when there is a push to a repository of a new package.
* (Possibly) poll known repos without webhooks (once a day?)
* Ignore hook payloads when package is closed/accepted (the first time we can post to 
  the issue telling author they can remove push webhook)


### Implementation ideas

* Ruby web app (rails or sinatra) using Octokit to communicate with github api
* Should have extensive unit tests (involves mocking github api)
* App may not need a database, seems like all the info we need is in github.
