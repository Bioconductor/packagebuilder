## run me like this:
## /path/to/R CMD BATCH -q --vanilla --no-save --no-restore --slave \
##     "--args Depends=@@R (>= 2.10), utils@@; Imports=@@methods@@; Suggests=@@tools, tkWidgets, ALL@@;" \
##     /working_dir/../installPkgDeps.R /working_dir/installDeps.log

options(useFancyQuotes=FALSE)

##
## extract package dependencies of any sort from command-line arguments
##

dependenciesFromArgs <- function(args) {
    if (length(args) == 0) {
        print("No arguments supplied.")
        quit("no")
    }
    if (args[1] == "--args")
        args <- args[2:length(args)]
    pattern <- "^(Depends|Imports|Suggests|Enhances|LinkingTo) *= *"
    s <- paste(args, collapse=" ")
    segs <- strsplit(s, "; *")[[1]]
    segs = sub(pattern, "", segs[grepl(pattern, segs)])
    unlist(strsplit(gsub("@@ *", "", segs), ", *"))
}

validateInstallation <- function(pkgs, lib.loc, label) {
    installed <- installed.packages(lib.loc)
    if (!all(pkgs %in% rownames(installed))) {
        missing <- setdiff(pkgs, rownames(installed))
        stop("'", label, "' missing packages: ", paste(missing, collapse=", "))
    }
    TRUE
}


args <- commandArgs(TRUE)
print("args are:")
print(args)

deps <- dependenciesFromArgs(args)
print("deps are:")
print(deps)

print(.libPaths())
stopifnot(length(.libPaths()) == 2L)
                                # 1: R-libs              (pkg-specific)
                                # 2: R_HOME/library         (read-only)
pkg_libdir <- .libPaths()[1]
R_libdir <- .libPaths()[2]


#
# Try to install (but will it cause issues with daily builder)
# but check R_libdir to see if exist first
# shouldn't cause issues with daily builder as +w only to owner
#

## load BiocInstaller
repos <- paste0("https://bioconductor.org/packages/",
                Sys.getenv("BBS_BIOC_VERSION"),
                "/bioc")
install.packages("BiocInstaller", repos=repos, lib=pkg_libdir)


##
## check that needed packages to run SPB are installed
##

SPB_pkgs <- c(
   "graph", "biocViews", "knitr", "knitrBootstrap",
   "devtools", "codetools", "httr", "curl", "optparse",
   "GenomicFeatures", "ShortRead", "VariantAnnotation")
pkgs_already <- dir(R_libdir)
needed_pkgs<- SPB_pkgs[!SPB_pkgs %in% pkgs_already]

if(length(needed_pkgs) != 0L){
    ## install other needed packages
    BiocInstaller::biocLite(needed_pkgs, lib=R_libdir)
} else {
    tryCatch(update.packages(repos=BiocInstaller::biocinstallRepos(),
                             lib.loc=R_libdir, ask=FALSE),
             error=function(e) conditionMessage(e))
}

opaths <- .libPaths()
.libPaths(pkg_libdir) # FIXME: source() & devtools don't obey lib=
devtools::install_github("Bioconductor/BiocCheck", lib=pkg_libdir)
.libPaths(opaths)

validateInstallation(SPB_pkgs, R_libdir, "SPB_pkgs")
validateInstallation("BiocCheck", pkg_libdir, "BiocCheck")


##
## repository and options setup
##

siteRepos <- sprintf(
    "http://bioconductor.org/scratch-repos/%s",
    as.character(BiocInstaller::biocVersion()))
options(install.packages.compile.from.source="always")

##
## dependencies
##

ip <- installed.packages()
blacklist <- c("R", rownames(ip),
               if (.Platform$OS.type == "windows") "multicore")
deps <- sub(" *\\((.*?)\\)", "", deps)  # strip version

## install missing dependencies
pkg_deps <- deps <- deps[!deps %in% blacklist]
if (getOption("pkgType") != "source")
    ## try to install binaries...
    BiocInstaller::biocLite(deps, lib.loc=pkg_libdir,
                            siteRepos=siteRepos, dependencies=TRUE)
deps <- deps[!deps %in% rownames(installed.packages())]
if (length(deps))
    ## source (e.g., linux) or failed binary installations
    BiocInstaller::biocLite(deps, lib.loc=pkg_libdir,
                            siteRepos=siteRepos, dependencies=TRUE,
                            type="source")

validateInstallation(pkg_deps, pkg_libdir, "pkg_deps")

## update pkg_libdir
tryCatch(update.packages(lib.loc=pkg_libdir, ask=FALSE,
                         repos=BiocInstaller::biocinstallRepos(siteRepos)),
         error=function(e) conditionMessage(e))

sessionInfo()
