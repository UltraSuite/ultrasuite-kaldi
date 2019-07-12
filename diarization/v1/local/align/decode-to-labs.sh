#!/bin/bash

# Converts decoder alignment to labels and TextGrids
# Usage: decode-to-labs.sh <MODDIR> <DECODEDIR> <GRAPHDIR>

MODDIR=$1       # model directory, e.g. './exp/mono0a'
DECODEDIR=$2    # decoding directory, e.g. './exp/mono0a/decode_test'
GRAPHDIR=$3     # graph directory, e.g. './exp/mono0a/graph'
DATADIR=$4      # data directory with utt2dur

# we use this here by default, although
# we should get it from the decoding dir
lmwt=12

# convert lattice to ctm
for LAT in ${DECODEDIR}/lat.*.gz; do
    lattice-1best --lm-scale=${lmwt} "ark:zcat ${LAT} |" ark:- | \
        lattice-align-words-lexicon ${GRAPHDIR}/phones/align_lexicon.int ${MODDIR}/final.mdl ark:- ark:- | \
        nbest-to-ctm ark:- - |
        ./utils/int2sym.pl -f 5 ${GRAPHDIR}/words.txt > ${LAT%.gz}.ctm
done

[ -e ${DECODEDIR}/lat.ctm ] && rm ${DECODEDIR}/lat.ctm
cat ${DECODEDIR}/*.ctm > ${DECODEDIR}/lat.ctm

# convert CTM to HTK lab
python ./local/align/ctm-to-lab.py \
    -ctm ${DECODEDIR}/lat.ctm \
    -labdir ${DECODEDIR}/lab_pre

# fix short segments and silences
python ./local/align/merge-short-segments.py \
  --indir ${DECODEDIR}/lab_pre \
  --outdir ${DECODEDIR}/lab

# convert labs to TextGrid
# this step requires praatio
# comment this out if you do not need TextGrids
python ./local/align/lab2tg.py \
  --labdir ${DECODEDIR}/lab \
  --tgdir ${DECODEDIR}/TG \
  --dur ${DATADIR}/utt2dur
