
# run me like this:
# /path/to/R CMD BATCH -q --vanilla --no-save --no-restore --slave "--args Depends=@@R (>= 2.10), utils@@; Imports=@@methods@@; Suggests=@@tools, tkWidgets, ALL@@;" /working_dir/../installPkgDeps.R /working_dir/installDeps.log

options(useFancyQuotes=FALSE)

## 
## extract package dependencies of any sort from command-line arguments
## 

dependenciesFromArgs <- function(args) {
    if (length(args) == 0) {
        print("No arguments supplied.")
        quit("no")
    }
    pattern <- "^(Depends|Imports|Suggests|Enhances|LinkingTo) *= *"
    s <- paste(args, collapse=" ")
    segs <- strsplit(s, "; *")[[1]]
    segs = sub(pattern, "", segs[grepl(pattern, segs)])
    unlist(strsplit(gsub("@@ *", "", segs), ", *"))
}
args <- commandArgs(TRUE)
print("args are:")
print(args)

deps <- dependenciesFromArgs(args)
print("deps are:")
print(deps)


##
## R version and repository setup
## 

if (!require(BiocInstaller))
    source("https://bioconductor.org/biocLite.R")
major <- R.Version()$major
minor <- sub("\\..*", "", R.Version()$minor)
r_ver <- sprintf("%s.%s", major, minor)

repos <- c(biocinstallRepos(),
           sprintf("http://bioconductor.org/scratch-repos/%s",
                   as.character(BiocInstaller::biocVersion())))
newrepos <- getOption("repos")
newrepos["CRAN"] <- "http://cran.fhcrc.org"
options(repos=newrepos, install.packages.compile.from.source="always")

##
## bootstrap installation
## 

home <- path.expand("~")

bootstrap_libdir <- if (Sys.info()['sysname'] == "Darwin") {
    sprintf("~/Library/R/%s/library", r_ver)
} else if (.Platform$OS.type == "windows") {
    pkgbuilderHome <- Sys.getenv("PACKAGEBUILDER_HOME")
    pkgbuilderHome <- gsub("\\", "/", pkgbuilderHome, fixed=TRUE)
    file.path(pkgbuilderHome, "R", "library")
} else {                                # linux 
    file.path(home, 'R', sprintf("%s-library", R.version$platform), r_ver)
}

## bootstrap dependencies
bootstrap_pkgs <- c("graph", "biocViews", "knitr", "knitrBootstrap",
    "devtools", "codetools", "httr", "curl")

ap <- available.packages(contrib.url(biocinstallRepos()[c("CRAN", "BioCsoft")]))
ip <- installed.packages(lib.loc = bootstrap_libdir,
    fields=c("Version","Priority"))

need <- bootstrap_pkgs[!bootstrap_pkgs %in% rownames(ip)]
have <- setdiff(bootstrap_pkgs, need)
idx <-
    package_version(ip[have, "Version"]) < package_version(ap[have, "Version"])
need <- c(have[idx], need)
if (length(need))
    install.packages(need, bootstrap_libdir, repos=biocinstallRepos())
library(BiocInstaller)
biocLite("Bioconductor/BiocCheck", lib=bootstrap_libdir)

## FIXME: validate post-condition

## 
## update installed packages
## 

old.libPaths <- .libPaths()
.libPaths(c(.libPaths(), bootstrap_libdir))

update.packages(repos=biocinstallRepos(), lib.loc=bootstrap_libdir,
    instlib=bootstrap_libdir, ask=FALSE)

.libPaths(old.libPaths)

##
## install dependencies
##

deps <- sub(" *\\((.*?)\\)", "", deps)  # strip version
dp <- as.data.frame(ip)
blacklist <- c(bootstrap_pkgs,
               rownames(ip)[dp$Priority %in% "base"],
               if (.Platform$OS.type == "windows") "multicore")
deps <- deps[!deps %in% blacklist]

withWarnings <- function(expr) {
    myWarnings <- NULL
    wHandler <- function(w) {
        myWarnings <<- c(myWarnings, list(w))
        invokeRestart("muffleWarning")
    }
    val <- withCallingHandlers(expr, warning = wHandler)
    list(value = val, warnings = myWarnings)
} 


installPkg <- function(pkg)
{
    if (pkg == "multicore" && .Platform$OS.type == "windows")
        return()

    #lib <- file.path(Sys.getenv("PACKAGEBUILDER_HOME"), "R-libs")

    if (!getOption("pkgType") == "source")
    {
        vnw <- withWarnings(install.packages(pkg, repos=repos))$warnings
        res <- unlist(lapply(vnw$warnings, function(x) x$message))
        if (!pkg %in% rownames(installed.packages()))
            install.packages(pkg, type="source", repos=repos)
        if(!is.null(res))
        {
            res <- res[grep("not available", res)]
            if (!length(res))
                return()
            pkgs <- strsplit(res, "'")[[1]]
            pkgs <- pkgs[grep(" ", pkgs, invert=TRUE)]
            install.packages(pkgs, type="source", repos=repos)
        }
    } else {
        install.packages(pkg, repos=repos, lib=lib)
    }
}

installDeps <- function(depStr)
{
    
    builtIn <- function(pkg)
    {
        pkg %in% c("R", "tools", "utils", "methods", "base", "graphics")
    }
    
    pkgs <- strsplit(depStr, ",", fixed=TRUE)[[1]]
    for (pkg in pkgs) {
        pkg <- trimws(pkg)
        if (length(grep("(", pkg, fixed=TRUE))) { ## is there a version spec?
            versionSpec <- gsub(".*\\((.*?)\\).*","\\1", pkg)
            segs <- strsplit(versionSpec, " ", fixed=TRUE)
            operator <- segs[[1]][1]
            requiredVersion <- segs[[1]][2]
            segs <- strsplit(pkg, "(", fixed=TRUE)
            pkgName <- trimws(segs[[1]][1])
            if (builtIn(pkgName)) next
            ip <- installed.packages()
            if (pkgName %in% rownames(ip)) {
                installedVersion <- ip[pkgName, "Version"]
                if (numeric_version(requiredVersion) > 
                  numeric_version(installedVersion)) {
                    message(paste(pkgName, "version", installedVersion,
                      "is too old, updating..."))
                    installPkg(pkgName)
                }
            } else {
                installPkg(pkgName)
            }
        } else {
            if (builtIn(pkg)) next
            if (!pkg %in% rownames(installed.packages()))
                installPkg(pkg)
        }
    }
}

installDeps(deps)

if (.Platform$OS.type == "windows")
    biocLite("lattice", type="source")
