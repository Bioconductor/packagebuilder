Results
=======

##### Running `latex-test.bat` manually, before Dan's restart

```
* checking for file 'SPBTestLatex/DESCRIPTION' ... OK
* preparing 'SPBTestLatex':
* checking DESCRIPTION meta-information ... OK
* installing the package to build vignettes
* creating vignettes ...Warning: running command '"E:/packagebuilder/R/bin/x64/Rscript" --vanilla --default-packages= -e "tools::buildVignettes(dir = '.', tangle = TRUE)"' had status 1
 ERROR

Unfortunately, the package framed could not be installed.Please check the log file:
C:/Users/pkgbuild/AppData/Local/MiKTeX/2.9/miktex/log/KPSEWH~1.log
Warning: running command 'kpsewhich framed.sty' had status 1
Warning: running command '"C:\MiKTeX2.9\miktex\bin\texify.exe" --quiet --pdf "SPBTestLatex.tex" --max-iterations=20 -I "E:/packagebuilder/R/share/texmf/tex/latex" -I "E:/packagebuilder/R/share/texmf/bibtex/bst"' had status 1
Error: running 'texi2dvi' on 'SPBTestLatex.tex' failed

LaTeX errors:
! LaTeX Error: File `framed.sty' not found.

Type X to quit or <RETURN> to proceed,
or enter new name. (Default extension: sty)

Execution halted

```


##### Running `latex-test.bat` manually, after Dan's restart
TODO: We should capture the changes that were made before this restart.  However, I've yet to ask Dan what changes prompted the restart.  This was around ~11:45am (Eastern) on 2015-Dec-21.

```
* checking for file 'SPBTestLatex/DESCRIPTION' ... OK
* preparing 'SPBTestLatex':
* checking DESCRIPTION meta-information ... OK
* installing the package to build vignettes
* creating vignettes ...Warning: running command '"E:/packagebuilder/R/bin/x64/Rscript" --vanilla --default-packages= -e "tools::buildVignettes(dir = '.', tangle = TRUE)"' had status 1
 ERROR

Sorry, but C:\MiKTeX2.9\miktex\bin\KPSEWH~1.EXE did not succeed.

You may want to visit the MiKTeX project page, if you need help.
Warning: running command 'kpsewhich framed.sty' had status 1
Warning in test_latex_pkg("framed", system.file("misc", "framed.sty", package = "knitr")) :
  unable to find LaTeX package 'framed'; will use a copy from knitr
Warning: running command '"C:\MiKTeX2.9\miktex\bin\texify.exe" --quiet --pdf "SPBTestLatex.tex" --max-iterations=20 -I "E:/packagebuilder/R/share/texmf/tex/latex" -I "E:/packagebuilder/R/share/texmf/bibtex/bst"' had status 1
Error in find_vignette_product(name, by = "texi2pdf", engine = engine) : 
  Failed to locate the 'texi2pdf' output file (by engine 'knitr::knitr') for vignette with name 'SPBTestLatex'. The following files exist in directory '.': 'SPBTestLatex.Rnw', 'SPBTestLatex.tex', 'framed.sty'
Calls: <Anonymous> -> find_vignette_product
Execution halted

```

##### Running `latex-test.bat` manually, after Dan's modified permissions.
Specifically, Dan gave "_Full Control_" of the directory `C:\Users\dtenenba\AppData\Local\Programs\MiKTeX 2.9\` directory to the `pkgbuild` user.
```
* checking for file 'SPBTestLatex/DESCRIPTION' ... OK
* preparing 'SPBTestLatex':
* checking DESCRIPTION meta-information ... OK
* installing the package to build vignettes
* creating vignettes ... OK
* checking for LF line-endings in source and make files
* checking for empty or unneeded directories
* building 'SPBTestLatex_0.99.3.tar.gz'
```
