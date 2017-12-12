
myArgs <- commandArgs(trailingOnly = TRUE)

require(dplyr)
require(biocViews)

is_dataExp <-
    function(description_paths)
{
    db <- tools:::.read_description(file.path(description_paths, "DESCRIPTION"))

    biocViews <- strsplit(unname(db["biocViews"]), "[[:space:],]+")

    biocViews <- tibble(
        package = rep(unname(db["Package"]), lengths(biocViews)),
        term = unlist(biocViews, use.names=FALSE)
    )


    currViews <- biocViews::getCurrentbiocViews()
    currViews <- tibble(
        term = unlist(currViews, use.names=FALSE),
        type = rep(
            tolower(sub("ExperimentData", "data-experiment", names(currViews))),
            lengths(currViews)
        )
    )
    tbl <- left_join(biocViews, currViews) %>% select(type) %>% unique
    "data-experiment" %in% tbl
}

result <- is_dataExp(myArgs)

cat(result)


#x = subprocess.check_output("/home/lori/bin/R-devel/bin/Rscript --vanilla --no-save --no-restore /home/lori/a/singlePackageBuilder/packagebuilder/workers/isData.R /home/lori/pkgReview/mCSEA", shell=True)
