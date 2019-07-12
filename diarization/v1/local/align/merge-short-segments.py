#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix small segments in SLT/Child alignment.

Corrections are:
    1) Labels separated by short silences are merged (see MAX_SIL)
    2) Short labels are removed and replaced with silence (see MIN_LEN)

Date: 2018
Author: M. Sam Ribeiro
"""

import os, sys
import argparse


def write(data, filename):
    output = open(filename, 'w')
    for line in data:
        output.write(line + '\n')
    output.close()


def correct_alignment(input_f, output_f):

    # these functions convert seconds to HTK-seconds
    to_htkseconds = lambda x : int(float(x)*10000000.)
    to_seconds    = lambda x : float(int(x)/10000000.)

    MAX_SIL = 0.2   # merge labels if silence between them is shorter than this (secs)
    MIN_LEN = 0.1  # remove labels if they are shorter than this (secs)

    with open(input_f, 'r') as fid:
        lines = fid.readlines()

    data = []
    previous = (0.0, 0.0, None)

    # first pass handles short silences
    for line in lines:
        start, end, label = line.rstrip().split()

        start = to_seconds(start)
        end = to_seconds(end)

        pstart, pend, plabel = previous
        item = (start, end, label)

        append = True
        if (start - pend) <= MAX_SIL:
            if not plabel:
                item = (pstart, end, label)

            elif label == plabel:
                item = (pstart, end, label)
                data[-1] = item
                append = False

        if append: data.append(item)
        previous = item

    # second pass to remove very short segments
    data = [(s, e, l) for s,e,l in data if (e-s)>= MIN_LEN]

    # convert to text
    data = [' '.join((str(to_htkseconds(s)), str(to_htkseconds(e)), l)) for s, e, l in data]

    if len(data) <= 0:
        print('merge-short-segments.py - empty label after correction {0}'.format(input_f))

    # write to output file (even if empty)
    write(data, output_f)


def main(input_dir, output_dir):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filelist = [f for f in os.listdir(input_dir) if f.endswith('.lab')]

    for f in filelist:
        in_f  = os.path.join(input_dir, f)
        out_f = os.path.join(output_dir, f)

        correct_alignment(in_f, out_f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--indir', type=str, required=True, help='input directory')
    parser.add_argument('--outdir', type=str, required=True, help='output directory')
    args = parser.parse_args()

    main(args.indir, args.outdir)
