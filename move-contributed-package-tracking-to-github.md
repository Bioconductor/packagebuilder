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
* Contributor adds **bioc-sync** user as a collaborator. 
* Contributor sets up a web hook to notify the single package builder of pushes to the repository.
* The first time the SPB receives a message from this web hook, it will create an issue
  in the repository with some standard name (like "Bioconductor Package Review") and post
  the build report there. All subsequent discussion (by humans as well as the SPB) will
  happen in this issue.

### Unknowns - 

* how to mark package status? Maybe have a set of images (like badges) that we can link to 
 in the issue discussion that are glyphs of the various package statuses (sent-back, accepted, etc.).
* What happens when the package is accepted? For now we could just do things the exact same
  way we do them now (add the package to svn) except that the source will be a git repo
  and not a tarball. We might also want to link the repo to the Bioc git mirrors (or tell
  contributor how to do that) so contributor can continue developing in their original repo.
  Eventually everything will be done in git (no svn) but we are not sure exactly 
  how that transition will happen. It does sound like Bioc will have its own git server
  (or use a robust hosted one; AWS CodeCommit?) but that repos will be mirrored on GitHub.
  



