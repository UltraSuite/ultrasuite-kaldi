#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Convert HTK-style labels to Praat TextGrid.

Date: 2018
Author: M. Sam Ribeiro
"""

import os
import argparse
from praatio import tgio

def lab2tg(input_filename, output_filename, wav_duration, tiername=None):

    lab = []

    with open(input_filename, 'r') as fid:
        for line in fid.readlines():
            start, end, label = line.rstrip().split()
            start = float(start)/10000000.
            end   = float(end)/10000000.
            lab.append((start, end, label))

    if len(lab) <= 0:
        print('Unable to convert empty lab for {0}'.format(input_filename))
        return

    if not tiername:
        tiername = 'tier_1'

    tg = tgio.Textgrid()
    tier = tgio.IntervalTier(tiername, lab, 0, wav_duration)

    tg.addTier(tier)
    tg.save(output_filename)



def main(labdir, tgdir, dur_f):

    utt2dur = {}
    with open(dur_f, 'r') as fid:
        for line in fid.readlines():
            utt, dur = line.rstrip().split()
            utt2dur[utt] = float(dur)

    flist = os.listdir(labdir)
    print('lab2tg: Found {0} utterances to convert'.format( len(flist) ))

    if not os.path.exists(tgdir):
        os.makedirs(tgdir)

    for f in flist:
        lab_f = os.path.join(labdir, f)
        grid_f = os.path.join(tgdir, f.replace('.lab', '.TextGrid'))

        lab2tg(lab_f, grid_f, utt2dur[f.replace('.lab', '')])



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--labdir', type=str, required=True, help='input lab directory')
    parser.add_argument('-t', '--tgdir', type=str, required=True, help='output TextGrid directory')
    parser.add_argument('-d', '--dur', type=str, required=True, default='', help='utt2dur filename')
    args = parser.parse_args()

    main(args.labdir, args.tgdir, args.dur)
