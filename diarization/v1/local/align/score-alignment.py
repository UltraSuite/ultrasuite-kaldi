#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Score diarization/speaker-labelling alignments in terms of seconds using pyannote.

Outputs: score.seconds, report.seconds

score.seconds
    primary metrics relevant for the task. These are
        precision, recall, f1
        identification error rate (IER)
        diarization error rate (DER) and respective terms

report.seconds
    table with primary metrics at the utterance-level, sorted by DER.


Date: 2018
Author: M. Sam Ribeiro
"""

import os, sys
import argparse

from pyannote.core import Annotation, Segment
from pyannote.metrics.identification import IdentificationErrorRate,\
    IdentificationPrecision, IdentificationRecall
from pyannote.metrics.diarization import DiarizationErrorRate



def read_annotation(filename, annotation_type=None, skip_tokens=[]):
    ''' read HTK label into pyannote Annotation '''
    annotation = Annotation(uri=annotation_type)

    if os.path.isfile(filename):
        with open(filename) as fid:
            for line in fid.readlines():
                start, end, label = line.rstrip().split()

                # convert to seconds
                start = int(start) / 10000000.
                end   = int(end) / 10000000.
                label = label.upper()
                if label not in skip_tokens:
                    annotation[Segment(start, end)] = label

    return annotation



def main(reference_dir, hypothesis_dir, output_dir):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    flist = os.listdir(reference_dir)
    total_references = len(flist)
    total_hypotheses = len(os.listdir(hypothesis_dir))

    if total_references == 0: # no references available
        score_f = os.path.join(output_dir, 'score.seconds')
        score = open(score_f, 'w')
        score.write('No references available.\n')
        score.write('references {0}\n'.format(total_references))
        score.write('hypotheses {0}\n'.format(total_hypotheses))
        sys.exit(0)

    collar = 0.1 # collar in seconds

    der_eval = DiarizationErrorRate(collar=collar)
    ier_eval = IdentificationErrorRate(collar=collar)
    prec_eval    = IdentificationPrecision(collar=collar)
    rec_eval     = IdentificationRecall(collar=collar)

    skip_tokens = ['OVERLAP', 'SPN']
    skip_tokens_child = ['OVERLAP', 'SPN', 'SLT']

    missing_hypotheses = 0
    missing_hypotheses_seconds = 0
    utt_scores = []

    for f in flist:
        ref_f = os.path.join(reference_dir, f)
        hyp_f = os.path.join(hypothesis_dir, f)

        reference       = read_annotation(ref_f, \
            annotation_type='reference', skip_tokens=skip_tokens)
        reference_child = read_annotation(ref_f, \
            annotation_type='reference', skip_tokens=skip_tokens_child)

        if not os.path.isfile(hyp_f):
            missing_hypotheses += 1
            missed_sum = sum([i.end-i.start for i in reference.itersegments()])
            missing_hypotheses_seconds += missed_sum

        # read_annotation can handle non-existing files
        hypothesis       = read_annotation(hyp_f, \
            annotation_type='hypothesis', skip_tokens=skip_tokens)
        hypothesis_child = read_annotation(hyp_f, \
            annotation_type='hypothesis', skip_tokens=skip_tokens_child)

        # find global min and max
        time_ref = [[i.start, i.end] for i in reference.itersegments()]
        time_hyp = [[i.start, i.end] for i in hypothesis.itersegments()]
        min_f = min([i for i, e in time_hyp] + [i for i, e in time_ref])
        max_f = max([e for i, e in time_hyp] + [e for i, e in time_ref])

        # evaluate DER
        der = der_eval(reference, hypothesis, \
            uem=Segment(min_f, max_f), detailed=True)

        # find global min and max
        time_ref = [[i.start, i.end] for i in reference_child.itersegments()]
        time_hyp = [[i.start, i.end] for i in hypothesis_child.itersegments()]
        min_f = min([i for i, e in time_hyp] + [i for i, e in time_ref])
        max_f = max([e for i, e in time_hyp] + [e for i, e in time_ref])

        # evaluate IER
        ier = ier_eval(reference_child, hypothesis_child, \
            uem=Segment(min_f, max_f), detailed=True)
        prec = prec_eval(reference_child, hypothesis_child, \
            uem=Segment(min_f, max_f))
        rec  = rec_eval(reference_child, hypothesis_child, \
            uem=Segment(min_f, max_f))
        f1 = 0 if prec == 0 or rec == 0 else 2*(prec*rec) / (prec + rec)

        ref_labs = ' '.join(reference.labels())
        hyp_labs = ' '.join(hypothesis.labels())

        ref_labs = ' '.join([label for _, _, label in reference.itertracks(yield_label=True)])
        hyp_labs = ' '.join([label for _, _, label in hypothesis.itertracks(yield_label=True)])

        if not hyp_labs: hyp_labs = 'no_alignment'
        utt_scores.append( [f, prec, rec, f1, der, ier, ref_labs, hyp_labs] )

    # global scores
    ier       = abs(ier_eval)
    der       = abs(der_eval)
    precision = abs(prec_eval)
    recall    = abs(rec_eval)
    f1 = 0 if precision == 0 or recall == 0 else 2*(precision*recall) / (precision + recall)

    # keys to intermediate metrics
    keys = ['correct', 'missed detection', 'false alarm', \
        'confusion', 'total', 'diarization error rate']
    aggregate = {k:0 for k in keys}

    ## global correct, missed, false alarm, confusion
    for item in utt_scores:
        der_errors = item[4]
        for key in keys:
            aggregate[key] += der_errors[key]
        ier_errors = item[5]
        item_ier = ier_errors['identification error rate']
        aggregate['der'] = item_ier

    if aggregate['total'] == 0: aggregate['total'] = 1
    # write global scores to file
    score_f = os.path.join(output_dir, 'score.seconds')
    score = open(score_f, 'w')

    score.write('precision {0:.3f}\n'.format(precision))
    score.write('recall {0:.3f}\n'.format(recall))
    score.write('f1 score {0:.3f}\n\n'.format(f1))

    score.write('IER {0:.3f}\n\n'.format(ier))

    score.write('DER {0:.3f}\n'.format(der))
    score.write('  missed {0:.3f}\n'.format(aggregate['missed detection'] / aggregate['total']))
    score.write('  false alarm {0:.3f}\n'.format(aggregate['false alarm'] / aggregate['total']))
    score.write('  confusion {0:.3f}\n'.format(aggregate['confusion'] / aggregate['total']))
    score.write('  correct {0:.3f}\n'.format(aggregate['correct'] / aggregate['total']))
    score.write('\n')

    score.write('total files {0}\n'.format(total_references))
    score.write('alignment failures\n')
    score.write('  total utterances: {0}\n'.format(missing_hypotheses))
    score.write('  total seconds in failed utterances: {0}\n\n'.format(missing_hypotheses_seconds))

    score.write('precision details\n')
    for i in prec_eval[:]:
        score.write('  {0} {1}\n'.format( i, prec_eval[:][i] ))

    score.write('\n')
    score.write('recall details\n')
    for i in rec_eval[:]:
        score.write('  {0} {1}\n'.format( i, rec_eval[:][i] ))

    score.close()

    # write detailed scores to file sorted by DER
    # columns: filename, precision, recall, f1, reference_words, hypothesis_words
    report_f = os.path.join(output_dir, 'report.seconds')
    report = open(report_f, 'w')

    header = [
        'filename',
        'precision', 'recall', 'f1',
        'correct', 'missed', 'false_alarm', 'confusion', 'total' , 'der', 'ier',
        'reference_words', 'hypothesis_words'
        ]
    report.write('\t'.join(header)+'\n')

    for item in sorted(utt_scores, key=lambda x: x[4]['diarization error rate']):
        data = []
        # filename
        data.append(item[0])
        # precision, recall, f1
        for i in range(1, 3+1):
            data.append( '{0:.3f}'.format(item[i]) )

        # DER related scores
        errors = item[4]
        for key in keys:
            value = '{0:.3f}'.format(errors[key])
            data.append(value)

        # IER score
        ier = item[5]['identification error rate']
        data.append( '{0:.3f}'.format(ier) )

        data.append(item[-2])
        data.append(item[-1])

        report.write('\t'.join(data)+'\n')
    report.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--ref', type=str, required=True, help='reference directory')
    parser.add_argument('--hyp', type=str, required=True, help='hypothesis directory')
    parser.add_argument('--out', type=str, required=True, help='output directory')
    args = parser.parse_args()

    main(args.ref, args.hyp, args.out)
