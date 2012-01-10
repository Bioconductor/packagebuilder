
# run me like this:
# /path/to/R CMD BATCH -q --vanilla --no-save --no-restore --slave "--args Depends=@@R (>= 2.10), utils@@; Imports=@@methods@@; Suggests=@@tools, tkWidgets, ALL@@;" /working_dir/../installPkgDeps.R /working_dir/installDeps.log

args <- (commandArgs(TRUE))


args <- gsub("@@", "\"", args, fixed=TRUE)

if (length(args) == 0) {
    print("No arguments supplied.")
    q("no")
}

s <- paste(args, collapse=" ")

segs <- strsplit(s, ";", fixed=TRUE)

l <- length(segs[[1]])
n = length(segs[[1]]) #-1
if (l == 1) n <- 1

r <- paste(segs[[1]][1:n])


trim <- function (x) gsub("^\\s+|\\s+$", "", x)


for (i in 1:length(r)) { 
    eval(parse(text=trim(r[i])))
}

if (!require(BiocInstaller)) 
    source("http://bioconductor.org/biocLite.R")



installPkg <- function(pkg)
{
    if (pkg == "multicore" && .Platform$OS.type == "windows")
        return()
    #lib <- file.path(Sys.getenv("PACKAGEBUILDER_HOME"), "R-libs")
    if (!getOption("pkgType") == "source")
    {
        biocLite(pkg, suppressUpdates=TRUE)
        if (!pkg %in% rownames(installed.packages()))
		biocLite(pkg, suppressUpdates=TRUE, type="source")
    } else {
        biocLite(pkg, suppressUpdates=TRUE)
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
        pkg <- trim(pkg)
        if (length(grep("(", pkg, fixed=TRUE))) { ## is there a version spec?
            versionSpec <- gsub(".*\\((.*?)\\).*","\\1", pkg)
            segs <- strsplit(versionSpec, " ", fixed=TRUE)
            operator <- segs[[1]][1]
            version <- segs[[1]][2]
            segs <- strsplit(pkg, "(", fixed=TRUE)
            pkgName <- trim(segs[[1]][1])
            if (builtIn(pkgName)) next
            ip <- installed.packages()
            if (pkgName %in% rownames(ip)) {
                installedVersion <- ip[pkgName, "Version"]
                if (!version >= installedVersion) {
                    message(paste(pkgName, "version", installedVersion,
                      "is too old, updating..."))
                    installPkg(pkgName)
                }
            } else {
                installPkg(pkgName)
            }
        } else {
            if (builtIn(pkg)) next
            if (!pkg %in% rownames(installed.packages())
                installPkg(pkg)
        }
    }
}


if (exists("Depends")) installDeps(Depends)
if (exists("Imports")) installDeps(Imports)
if (exists("Suggests")) installDeps(Suggests)
if (exists("Enhances")) installDeps(Enhances)


