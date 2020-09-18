library(BiocCheck)

args <- commandArgs(TRUE)
if (args[2]){
    BiocCheck(args[1], `new-package`=TRUE, `quit-with-status`=TRUE,
              `build-output-file`="R.out")
}else{
    BiocCheck(args[1], `quit-with-status`=TRUE,
              `build-output-file`="R.out")

}
