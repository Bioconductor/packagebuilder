
# run me like this:
# /path/to/R CMD BATCH -q --vanilla --no-save --no-restore --slave '--args Depends="R (>= 2.10), utils"; Imports="methods"; Suggests="tools, tkWidgets, ALL";' /working_dir/../installPkgDeps.R /working_dir/installDeps.log

args <- (commandArgs(TRUE))
if (length(args) == 0) {
    print("No arguments supplied.") #todo - more useful usage message
    q("no")
}

s <- paste(args, collapse=" ")
segs <- strsplit(s, ";", fixed=TRUE)

r <- paste(segs[[1]][1:length(segs[[1]])-1])


for (i in 1:length(r)) {
    eval(parse(text=r[i]))
}

if (!require(BiocInstaller)) 
    source("http://bioconductor.org/biocLite.R")


trim <- function (x) gsub("^\\s+|\\s+$", "", x)

installPkg <- function(pkg)
{
    lib <- file.path(Sys.getenv("PACKAGEBUILDER_HOME"), "Rlibs")
    if (!file.exists(lib))
        dir.create(lib)
    if (!getOption("pkgType") == "source")
        tryCatch(biocLite(pkg, lib=lib, suppressUpdates=TRUE),
            error=biocLite(pkg, type="source", lib=lib,
            suppressUpdates=TRUE))
    else
        biocLite(pkg, lib=lib, suppressUpdates=TRUE)
}

installDeps <- function(depStr)
{
    
    builtIn <- function(pkg)
    {
        pkg %in% c("R", "tools", "utils", "methods", "base", "graphics")
    }
    
    pkgs <- strsplit(depStr, ",", fixed=TRUE)[[1]]
    for (pkg in pkgs) {
        pkg <- trim(pkg)
        if (length(grep("(", pkg, fixed=TRUE))) {
            versionSpec <- gsub(".*\\((.*?)\\).*","\\1", pkg)
            segs <- strsplit(versionSpec, " ", fixed=TRUE)
            operator <- segs[[1]][1]
            version <- segs[[1]][2]
            segs <- strsplit(pkg, "(", fixed=TRUE)
            pkgName <- trim(segs[[1]][1])
            if (builtIn(pkgName)) next
            ip <- installed.packages()
            if (pkgName %in% ip) {
                installedVersion <- ip[pkgName, "Version"]
                if (!version >= installedVersion) {
                    message(paste(pkgName, "version", installedVersion,
                      "is too old, updating..."))
                    installPkg(pkgName)
                }
            }
        } else {
            message(paste("diag:", pkg, "\n"))
            if (builtIn(pkg)) next
            if (!pkg %in% installed.packages())
                installPkg(pkg)
        }
    }
}


if (exists("Depends")) installDeps(Depends)
if (exists("Imports")) installDeps(Imports)
if (exists("Suggests")) installDeps(Suggests)
if (exists("Enhances")) installDeps(Enhances)


