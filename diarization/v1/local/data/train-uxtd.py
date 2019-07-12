#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prepare UXTD data for training/testing Speaker Labelling models.

Date: 2018
Author: M. Sam Ribeiro
"""

import os, sys
import fileinput
import argparse

from utils import write_data
from utils import get_duration
from utils import read_speaker_map

def main(corpus_dir, labels_dir, output_dir, sample_rate=16000, use_reference=False):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    datadir  = os.path.join(corpus_dir, 'core')
    transdir = os.path.join(labels_dir, 'transcriptions')
    speaker_map_filename = os.path.join(corpus_dir, 'doc', 'speakers')
    speaker_map = read_speaker_map(speaker_map_filename)
    wav_base = 'FILEID sox WAVPATH -r {0} -t .wav - |'.format(sample_rate)

    # skip utterances of types D (articulatory), E (non-speech), and F (other)
    skip_tasks = ('D', 'E', 'F')

    for subset in speaker_map:
        print('Processing {0} data'.format(subset))
        subset_outdir  = os.path.join(output_dir, subset)

        if not os.path.exists(subset_outdir):
            os.makedirs(subset_outdir)

        speaker_utts = {}
        text, wav = [], []
        utt2spk, spk2utt = [], []
        utt2dur = []

        for speaker in speaker_map[subset]:

            speaker_dir = os.path.join(datadir, speaker)
            flist = [f for f in os.listdir(speaker_dir) if f.endswith('.wav')]

            for f in flist:
                f = f.replace('.wav', '')
                if f.endswith(skip_tasks):
                    continue

                # read transcription and convert to SLT/CHILD tokens
                fileid = '-'.join([speaker, f])
                txt_f = os.path.join(transdir, fileid+'.txt')
                with open(txt_f, 'r') as fid:
                    txt = fid.readline().rstrip()

                words = []
                for w in txt.split():
                    w = w.upper()
                    w = 'SLT' if 'SLT' in w else 'CHILD'
                    words.append(w)

                words = ' '.join([fileid] + words)
                text.append(words)

                # prepare wav.scp
                wavpath = os.path.join(speaker_dir, f+'.wav')
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

        text_f    = os.path.join(subset_outdir, 'text')
        wav_f     = os.path.join(subset_outdir, 'wav.scp')
        utt2spk_f = os.path.join(subset_outdir, 'utt2spk')
        spk2utt_f = os.path.join(subset_outdir, 'spk2utt')
        utt2dur_f = os.path.join(subset_outdir, 'utt2dur')

        write_data(text, text_f)
        write_data(wav, wav_f)
        write_data(utt2spk, utt2spk_f)
        write_data(spk2utt, spk2utt_f)
        write_data(utt2dur, utt2dur_f)

        # validate data directory
        validate_cmd = './utils/validate_data_dir.sh --no-feats {0}'.format(subset_outdir)
        os.system(validate_cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('corpus_dir',  type=str,  help='path to UXTD corpus')
    parser.add_argument('labels_dir',  type=str,  help='path to UXTD label directory')
    parser.add_argument('output_dir',  type=str,  help='path to output directory')
    parser.add_argument('--sr', dest='sample_rate', type=int, help='sample rate in Hz')
    parser.add_argument('--use_reference', dest='use_reference',  action='store_true', help='restrict to reference utterances')
    
    parser.set_defaults(sample_rate=16000)
    parser.set_defaults(use_reference=False)
    args = parser.parse_args()

    if args.use_reference:
        print('use_reference not applicable to training data. Ignoring...')

    main(args.corpus_dir, args.labels_dir, args.output_dir, args.sample_rate, use_reference=False)

