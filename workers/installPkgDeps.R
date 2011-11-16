
# run me like this:
# /path/to/R CMD BATCH -q --vanilla --no-save --no-restore --slave '--args Depends="R (>= 2.10), utils"; Imports="methods"; Suggests="tools, tkWidgets, ALL";' /working_dir/../installPkgDeps.R /working_dir/installDeps.log

args <- (commandArgs(TRUE))
if (length(args) == 0) {
    print("No arguments supplied.") #todo - more useful usage message
    q("no")
}

s <- paste(args, collapse=" ")
segs <- strsplit(s, ";", fixed=TRUE)



for (i in 1:length(args)) {
    eval(parse(text=args[i]))
}

fields <- c("Depends", "Imports", "Suggests", "Enhances")

for (field in fields) {
    installDeps(field)
}


cat(args, "\n")

if (!exists("Depends")) {
    print("'Depends' argument not present.")
    q("no")
}

