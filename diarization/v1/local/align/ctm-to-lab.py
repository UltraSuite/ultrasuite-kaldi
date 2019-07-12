#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Convert Kaldi ctm alignment to human-readable lab format.

ctm format: http://www1.icsi.berkeley.edu/Speech/docs/sctk-1.2/infmts.htm
HTK lab format: https://labrosa.ee.columbia.edu/doc/HTKBook21/node82.html

Date: 2017
Author: M. Sam Ribeiro
"""

import os
import fileinput
import logging
import argparse


def convert_ctm(ctm_data, lab_filename, table=None):
    ''' convert ctm to lab for single utterance '''
    output = open(lab_filename, 'w')

    for item in ctm_data:
        start, dur, phone = item
        start = float(start)
        end   = start + float(dur)

        # convert to HTK-seconds
        start *= 10000000.
        end   *= 10000000.

        if table:
            phone = table[int(phone)]
            if '_' in phone:
                phone = phone.split('_')
                phone = phone[0]

        line = ' '.join((str(int(start)), str(int(end)), phone))
        output.write(line + '\n')
    output.close()


def read_phones(filename):
    ''' read phone conversion table from file '''
    table = {}
    for line in fileinput.input(filename):
        phn, pid = line.split()
        table[int(pid)] = phn
    return table


def main(ctm_fname, out_directory, lang_dir):

    # parse ctm file and break into utterances
    utterances = {}
    for line in fileinput.input(ctm_fname):
        utt, channel, start, dur, phone = line.split()

        if utt in utterances:
            utterances[utt].append((start, dur, phone))
        else:
            utterances[utt] = [(start, dur, phone)]

    fileinput.input()

    logging.info('Found {0} utterances to convert'.format( len(utterances.keys()) ))

    # read phone table, if available
    phone_table = None
    if lang_dir:
        phone_f = os.path.join(lang_dir, 'phones.txt')
        if os.path.isfile(phone_f):
            phone_table = read_phones(phone_f)
        else:
            logging.warning('Phone table not found in lang directory. Not converting phones.')

    # create output directory
    if not os.path.exists(out_directory):
        os.makedirs(out_directory)

    # parse each utterance individually
    for utt in utterances.keys():
        lab = os.path.join(out_directory, utt+'.lab')
        convert_ctm(utterances[utt], lab, phone_table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-ctm', required=True, type=str,  help='ctm file to convert')
    parser.add_argument('-labdir', required=True, type=str,  help='output directory for lab files')
    parser.add_argument('-langdir', required=False, default=None,  help='Kaldi lang directory for phone conversion')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)-15s %(levelname)s: %(message)s',  datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)

    main(args.ctm, args.labdir, args.langdir)
