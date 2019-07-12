#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Assistive functions for data preparation.

Date: 2018
Author: M. Sam Ribeiro
"""

import fileinput
import subprocess

def write_data(data, filename):
    ''' write data to filename '''
    data = sorted(list(set(data)))
    output = open(filename, 'w')
    for line in data:
        output.write(line + '\n')
    output.close()


def get_duration(filename):
    ''' get duration of waveform via Edinburgh Speech Tools's ch_wave '''
    cmd = 'ch_wave {0} -info'.format(filename)
    p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    out, err = p.communicate()
    out = out.decode("utf-8").split('\n')
    return float(out[0].split()[1])


def read_speaker_map(filename):
    ''' read UXTD speaker info '''
    speakers = {}

    for line in fileinput.input(filename):
        if fileinput.isfirstline(): continue

        items = line.rstrip().split()
        spkid, subset = items[1], items[-1]

        if subset in speakers:
            speakers[subset].append(spkid)
        else:
            speakers[subset] = [spkid]

    return speakers
