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
##stopifnot(length(.libPaths()) == 2L)
                                # 1: R-libs              (pkg-specific)
                                # 2: R_HOME/library         (read-only)
                                # 3. R_HOME/site-library    (read-only)
pkg_libdir <- .libPaths()[1]
R_libdir <- .libPaths()[-1]


#
# Try to install (but will it cause issues with daily builder)
# but check R_libdir to see if exist first
# shouldn't cause issues with daily builder as +w only to owner
#

# install yaml to read config.yaml
install.packages("yaml", repos="https://cran.rstudio.com", lib=pkg_libdir)
config <- yaml::read_yaml("https://bioconductor.org/config.yaml")
bioc_ver <- config$single_package_builder$bioc_version
##bioc_ver = "3.14"

## load BiocManager
install.packages("BiocManager", repos="https://cran.rstudio.com",
                 lib=pkg_libdir)
if (BiocManager::version() != bioc_ver)
    BiocManager::install(version=bioc_ver, ask=FALSE, force=TRUE)

##
## check that needed packages to run SPB are installed
##

print("Checking needed SPB packages are installed")
SPB_pkgs <- c(
   "graph", "biocViews", "knitr", "knitrBootstrap",
   "devtools", "codetools", "httr", "curl", "optparse",
   "GenomicFeatures", "ShortRead", "VariantAnnotation",
   "dplyr", "biocViews", "BiocCheck")
pkgs_already <- dir(R_libdir)
needed_pkgs<- SPB_pkgs[!SPB_pkgs %in% pkgs_already]

if(length(needed_pkgs) != 0L){

    pkgs_already2 <- dir(pkg_libdir)
    needed_pkgs2<- needed_pkgs[!needed_pkgs  %in% pkgs_already2]
    ## install other needed packages in pkg_libdir
    ## pkgbuild doesn't have write access to R_libdir
    if(length(needed_pkgs2) != 0L)
        BiocManager::install(needed_pkgs2, lib=pkg_libdir)
    validateInstallation(needed_pkgs, pkg_libdir, "SPB_pkgs")
    
    # if some were found in R_lib check validInstall
    found_pkgs <- SPB_pkgs[SPB_pkgs %in% pkgs_already]
    if (length(found_pkgs) != 0L)
        validateInstallation(found_pkgs, R_libdir, "SPB_pkgs2")
} else {
    validateInstallation(SPB_pkgs, R_libdir, "SPB_pkgs")
}

opaths <- .libPaths()
.libPaths(pkg_libdir)
## This is not always ideal. Change back to using what is on the daily builder
#BiocManager::install("Bioconductor/BiocCheck", lib=pkg_libdir, force=TRUE)
if(!("remotes" %in% pkgs_already)){
    pkgs_already2 <- dir(pkg_libdir)
    if(!("remotes" %in% pkgs_already2)){
        BiocManager::install("remotes", lib=pkg_libdir)
    }
}
remotes::install_git("https://git.bioconductor.org/packages/BiocCheck", lib=pkg_libdir)
.libPaths(opaths)
#validateInstallation("BiocCheck", pkg_libdir, "BiocCheck")

##
## repository and options setup
##

options(install.packages.compile.from.source="always")

##
## dependencies
##

ip <- installed.packages()
blacklist <- c("R", rownames(ip),
               if (.Platform$OS.type == "windows") "multicore")
deps <- sub(" *\\((.*?)\\)", "", deps)  # strip version

## install missing dependencies
print("Installing Dependencies:")
pkg_deps <- deps <- deps[!deps %in% blacklist]
if (getOption("pkgType") != "source")
    ## try to install binaries...
    BiocManager::install(deps, lib.loc=pkg_libdir,
                            dependencies=TRUE)
deps <- deps[!deps %in% rownames(installed.packages())]
if (length(deps))
    ## source (e.g., linux) or failed binary installations
    BiocManager::install(deps, lib.loc=pkg_libdir,
                            dependencies=TRUE,
                            type="source")

validateInstallation(pkg_deps, pkg_libdir, "pkg_deps")

print("Checking Package Updates:")
## update pkg_libdir
tryCatch(update.packages(lib.loc=pkg_libdir, ask=FALSE,
                         repos=BiocManager::repositories()),
          error=function(e) conditionMessage(e))

print("SessionInfo:")
sessionInfo()
