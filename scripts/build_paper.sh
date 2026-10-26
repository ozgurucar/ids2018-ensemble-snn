#!/bin/sh
# Builds paper/dist/: PDF (tectonic), Overleaf zip, and a Word version (pandoc).
set -e
cd "$(dirname "$0")/../paper"
mkdir -p dist
tectonic -X compile main.tex
cp main.pdf dist/ids2018-esnn-paper.pdf
rm -f dist/ids2018-esnn-overleaf.zip
zip -q dist/ids2018-esnn-overleaf.zip main.tex references.bib
${PANDOC:-pandoc} main.tex --citeproc --bibliography=references.bib -o dist/ids2018-esnn-paper.docx
echo "Built: $(ls dist)"
