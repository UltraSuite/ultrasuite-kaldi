#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prepare UXSSD/UPX data for decoding with Speaker Labelling model.

Date: 2018
Author: M. Sam Ribeiro
"""

import os
import sys
import argparse

from utils import write_data
from utils import get_duration


def main(corpus_dir, labels_dir, output_dir, sample_rate=16000, use_reference=False):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    datadir  = os.path.join(corpus_dir, 'core')
    wav_base = 'FILEID sox WAVPATH -r {0} -t .wav - |'.format(sample_rate)

    if use_reference:
        ref_dir = os.path.join(labels_dir, 'reference_labels', 'lab')
        reference_list = [f.replace('.lab', '') for f in os.listdir(ref_dir)]

    # utterances with issues, ignore these
    reject_list = ['02F-Therapy_07-004A', '20M-BL2-009A']

    speaker_utts = {}
    text, wav = [], []
    utt2spk, spk2utt = [], []
    utt2dur = []

    speakers = os.listdir(datadir)

    for speaker in speakers:
        sessions = os.listdir(os.path.join(datadir, speaker))

        for session in sessions:

            session_dir = os.path.join(datadir, speaker, session)
            flist = [f for f in os.listdir(session_dir) if f.endswith('.wav')]

            for f in flist:
                f = f.replace('.wav', '')
                fileid = '-'.join([speaker, session, f])

                if fileid in reject_list:
                    continue

                if use_reference:
                    if fileid not in reference_list:
                        continue

                # use prompt for text, although it will be ignored for decoding
                txt_f = os.path.join(session_dir, f+'.txt')
                with open(txt_f, 'r') as fid:
                    txt = fid.readline().rstrip()

                words = []
                for w in txt.split():
                    w = w.upper()
                    words.append(w)

                words = ' '.join([fileid] + words)
                text.append(words)

                # prepare wav.scp
                wavpath = os.path.join(session_dir, f+'.wav')
                file_wav = wav_base.replace('FILEID', fileid)
                file_wav = file_wav.replace('WAVPATH', wavpath)
                wav.append(file_wav)

                # prepare utt2dur
                dur = get_duration(wavpath)
                utt2dur.append('{0} {1}'.format(fileid, dur))

                # prepare utt2spk
                utt2spk.append('{0} {1}'.format(fileid, speaker))

                if speaker in speaker_utts:
                    speaker_utts[speaker].append(fileid)
                else:
                    speaker_utts[speaker] = [fileid]

    # prepare spk2utt
    for speaker in speaker_utts:
        spk_utts = '{0} {1}'.format(speaker, ' '.join(sorted(speaker_utts[speaker])))
        spk2utt.append(spk_utts)

    text_f    = os.path.join(output_dir, 'text')
    wav_f     = os.path.join(output_dir, 'wav.scp')
    utt2spk_f = os.path.join(output_dir, 'utt2spk')
    spk2utt_f = os.path.join(output_dir, 'spk2utt')
    utt2dur_f = os.path.join(output_dir, 'utt2dur')
    
    write_data(text, text_f)
    write_data(wav, wav_f)
    write_data(utt2spk, utt2spk_f)
    write_data(spk2utt, spk2utt_f)
    write_data(utt2dur, utt2dur_f)

    # validate data directory
    validate_cmd = './utils/validate_data_dir.sh --no-feats {0}'.format(output_dir)
    os.system(validate_cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('corpus_dir',  type=str,  help='path to UXSSD corpus')
    parser.add_argument('labels_dir',  type=str,  help='path to UXTD label directory')
    parser.add_argument('output_dir',  type=str,  help='path to output directory')
    parser.add_argument('--sr', dest='sample_rate', type=int, help='sample rate in Hz')
    parser.add_argument('--use_reference', dest='use_reference',  action='store_true', help='restrict to reference utterances')

    parser.set_defaults(sample_rate=16000)
    parser.set_defaults(use_reference=False)
    args = parser.parse_args()

    main(args.corpus_dir, args.labels_dir, args.output_dir, args.sample_rate, args.use_reference)
