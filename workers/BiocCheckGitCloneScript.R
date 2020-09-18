library(BiocCheck)

args <- commandArgs(TRUE)
BiocCheckGitClone(args, `quit-with-status`=TRUE)
