
# run me like this:
# /path/to/R CMD BATCH -q --vanilla --no-save --no-restore '--args Depends="R (>= 2.10), utils" Imports="methods" Suggests="tools, tkWidgets, ALL"' /working_dir/../installPkgDeps.R /working_dir/installDeps.log

args <- (commandArgs(TRUE))
if (length(args) == 0) {
    print("No arguments supplied.") #todo - more useful usage message
    q("no")
}

#cmds = args[1:4] # modify if # of args changes

for (i in 1:length(cmds)) {
    eval(parse(text=cmds[i]))
}



cat(args, "\n")

if (!exists("Depends")) {
    print("'Depends' argument not present.")
    q("no")
}

