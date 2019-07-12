#!/bin/bash
# speaker labelling for UltraSuite version 1.0

# Global configuration file

# Control start and end stages here
# The recipe goes according to the following steps:
#   Stage 0: Prepare Kaldi data directories
#   Stage 1: Extract MFCC, F0, and ETA features
#   Stage 2: Prepare Lang and LM Kaldi directories
#   Stage 3: Train HMM-GMM
#   Stage 4: Decode and score reference alignments
#   Stage 5: Decode UltraSuite data
stage_start=0
stage_end=5

# number of jobs per data set
# nj should not be more than the number of speakers
nj_train=20
nj_uxtd=20
nj_uxssd=8
nj_upx=20
nj_ref=5

# global paths for UltraSuite repository
ULTRASUITE="<PATH-TO-ULTRASUITE>"

UXTD_CORE=${ULTRASUITE}/core-uxtd
UXSSD_CORE=${ULTRASUITE}/core-uxssd
UPX_CORE=${ULTRASUITE}/core-upx
LABEL_DIR=${ULTRASUITE}/labels-uxtd-uxssd-upx

# paths for current experiment
DATA_DIR=./data/tmp
EXP_DIR=./exp/tmp

# config for acoustic feature extraction
mfcc_conf=conf/mfcc.conf
pitch_conf=conf/pitch.conf
