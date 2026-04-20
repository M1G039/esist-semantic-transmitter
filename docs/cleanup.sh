#!/usr/bin/bash 

# Run this script to clean up the artifacts from TeX file compilations

echo "[*] Cleaning up the TeX Artifacts..."
echo
sleep 1 
rm -rf *.aux *.log *.out *.toc *.vrb *.nav *.fls *.fdb_latexmk *.bbl *.blg *.pyg *.snm *.synctex.gz _minted* build svg-inkscape
sleep 1
echo
echo "[INFO] Cleanup completed!"
