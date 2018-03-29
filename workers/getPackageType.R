library(biocViews)

args <- commandArgs(TRUE)
vl = guessPackageType(args)
cat(vl)

