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
stopifnot(length(.libPaths()) == 3L)    # 1: R-libs              (pkg-specific)
                                        # 2: packagebuilder/library (bootstrap)
                                        # 3: R_HOME/library         (read-only)
pkg_libdir <- .libPaths()[1]
bootstrap_libdir <- .libPaths()[2]

##
## validate pacakgebuilder/library (bootstrap library)
##

bootstrap_pkgs <- c(
    "graph", "biocViews", "knitr", "knitrBootstrap",
    "devtools", "codetools", "httr", "curl", "optparse")

if (length(dir(bootstrap_libdir)) == 0L) { # first-time installation
    ## BiocInstaller
    repos <- paste0("https://bioconductor.org/packages/",
                    Sys.getenv("BBS_BIOC_VERSION"),
                    "/bioc")
    install.packages("BiocInstaller", repos=repos, lib=bootstrap_libdir)
    ## other packages
    BiocInstaller::biocLite(bootstrap_pkgs, lib=bootstrap_libdir)
} else {
    update.packages(repos=BiocInstaller::biocinstallRepos(),
                    lib.loc=bootstrap_libdir, ask=FALSE)
}

opaths <- .libPaths()
.libPaths(bootstrap_libdir) # FIXME: source() & devtools don't obey lib=
devtools::install_github("Bioconductor/BiocCheck", lib=bootstrap_libdir)
.libPaths(opaths)

bootstrap_pkgs <- c(bootstrap_pkgs, "BiocCheck")
validateInstallation(bootstrap_pkgs, bootstrap_libdir, "bootstrap_pkgs")

##
## repository and options setup
##

repos <- c(BiocInstaller::biocinstallRepos(),
           sprintf("http://bioconductor.org/scratch-repos/%s",
                   as.character(BiocInstaller::biocVersion())))
options(install.packages.compile.from.source="always")

##
## dependencies
##

ip <- installed.packages()
blacklist <- c("R", bootstrap_pkgs, rownames(ip),
               if (.Platform$OS.type == "windows") "multicore")
all_deps <- deps <- sub(" *\\((.*?)\\)", "", deps)  # strip version

## install missing dependencies
deps <- deps[!deps %in% blacklist]
if (getOption("pkgType") != "source")
    ## try to install binaries...
    BiocInstaller::biocLite(deps, lib.loc=pkg_libdir, dependencies=TRUE)
deps <- deps[!deps %in% rownames(installed.packages())]
if (length(deps))
    ## source (e.g., linux) or failed binary installations
    BiocInstaller::biocLite(deps, lib.loc=pkg_libdir, dependencies=TRUE,
                            type="source")

validateInstallation(all_deps, pkg_libdir, "pkg_deps")

## update previously installed dependencies

update.packages(all_deps, lib.loc=pkg_libdir)

sessionInfo()
