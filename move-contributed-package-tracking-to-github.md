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
  Issues must be enabled.
* Contributor sets up a web hook to notify the single package builder of pushes to the repository.
* The first time the SPB receives a message from this web hook, it will create an issue
  in the repository with some standard name (like "Bioconductor Package Review") and post
  the build report there. All subsequent discussion (by humans as well as the SPB) will
  happen in this issue.

## Work that needs to be done to get there

* Document what contributor needs to do
* Write a small web app that listens for push hook messages and notifies the SPB.
  This app should also maybe provide a user-facing page that lists all repos
  that have the web hook (all repos that have communicated with it). This
  gives us a UI to packages that are being or have been tracked, a bit like
  the current tracker UI.
* Modify SPB to be able to build from git repos, and to post reports to github issues 
 (should use GitHub API for this).


### Unknowns

* how to mark package status? Maybe have a set of images (like badges) that we can link to 
 in the issue discussion that are glyphs of the various package statuses (sent-back, accepted, etc.).
* What happens when the package is accepted? For now we could just do things the exact same
  way we do them now (add the package to svn) except that the source will be a git repo
  and not a tarball. We might also want to link the repo to the Bioc git mirrors (or tell
  contributor how to do that) so contributor can continue developing in their original repo.
  Eventually everything will be done in git (no svn) but we are not sure exactly 
  how that transition will happen. It does sound like Bioc will have its own git server
  (or use a robust hosted one; AWS CodeCommit?) but that repos will be mirrored on GitHub.
  Getting a bit off topic, but we need to figure out how to link the contributor's
  github repos with bioc's non-github-hosted repos after their package is accepted.
  


## Other considerations

* We should come up with a way to limit access to the spb. Do we want anyone who 
  adds the web hook to be able to use the SPB or do we want to pre-approve them somehow?
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

* Respond to GitHub web hooks when there is a push to a repository of a new package.
* Display a list of all repos we know about
* Associate the repos with a reviewer 
* Provide reviewer with shields/shield code to udpate package status; display status
* Ignore hook payloads when package is closed/accepted (the first time we can post to 
  the issue telling author they can remove push webhook)

The app should have a page analagous to the 'main' page of the current tracker which displays 
a table containing the following columns:

* Package, containing a link to the issue which contains the review 'conversation'
* Status
* Reviewer / widget to assign reviewer
* Widget for reviewer to update status

### Implementation ideas

* Ruby web app (rails or sinatra) using Octokit to communicate with github api
* Should have extensive unit tests (involves mocking github api)

Database has one table with the following columns:

* Repos URL
* Package name
* Issue # which contains review conversation
* Reviewer
* Package status? Not sure if this should be in db as the info is available in 
  the github issue, storing it in DB as well is not DRY.
