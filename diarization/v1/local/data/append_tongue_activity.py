#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Append tongue activity to Kaldi's acoustic features.

Date: 2018
Author: M. Sam Ribeiro
"""

import os, sys
import argparse

import kaldi_io
import numpy as np


def downsample(data, n=4):
    ''' downsample array by dropping every n-th sample '''
    return [v for i,v in enumerate(data) if i%(n+1)]


def upsample(data, n=4):
    ''' upsample array by repeating every n-th sample '''
    upsampled = []
    for i, v in enumerate(data):
        upsampled.append(v)
        if i%(n+1)==0: upsampled.append(v)
    return upsampled


def read_tongue_activity(directory):
    ''' read tongue activity from directory 
        returns dictionary where keys are file_ids and values
        are tuples of [offset, fps, tongue_activity_array]
    '''
    data = {}

    for f in os.listdir(directory):
        filename = os.path.join(directory, f)

        with open(filename) as fid:
            for line in fid.readlines():
                file_id, offset, fps, eta = line.split(',')
                eta = [float(v) for v in eta.split()]
                offset = float(offset)
                fps = float(fps)

                if file_id in data:
                    print('Warning: unexpected repeated file id {0}'.format(file_id))

                data[file_id] = [offset, fps, eta]
    return data




def main(in_feats_dir, eta_dir, out_feats_dir):

    print('Appending estimated tongue activity to features in {0}'.format(in_feats_dir))

    if not os.path.exists(out_feats_dir):
        os.makedirs(out_feats_dir)

    # read estimated tongue activity
    eta_data = read_tongue_activity(eta_dir)

    # get scp filelist
    scp_list = sorted([f for f in os.listdir(in_feats_dir) if f.endswith('.scp')])
    print('Found {0} scp feature files to process'.format(len(scp_list)))

    for scp in scp_list:
        in_scp_filename  = os.path.join(in_feats_dir, scp)
        upsampled, downsampled = 0, 0

        scp_data = kaldi_io.read_mat_scp(in_scp_filename)
        eta_scp_data = {}

        for key, mat in scp_data:

            if key not in eta_data:
                print('Warning: could not find ETA data for {0}'.format(key))
                continue

            eta = eta_data[key][2]
            eta_size = len(eta)
            mfcc_size = mat.shape[0]

            # ETA is normally at a higher sampling rate, so we need to downsample
            if eta_size > mfcc_size:
                downsampling_attempts = 0
                while abs(eta_size-mfcc_size) > 0 and downsampling_attempts < 5:
                    n = int( eta_size / (eta_size-mfcc_size) )
                    eta = downsample(eta, n=n)
                    eta_size = len(eta)
                    downsampling_attempts += 1
                downsampled += 1

            # but in some cases, this might not happen, so we upsample
            else:
                upsampling_attempts = 0
                while abs(mfcc_size-eta_size) > 0 and upsampling_attempts < 5:
                    n = int( mfcc_size / (mfcc_size-eta_size) )
                    eta = upsample(eta, n=n)
                    eta_size = len(eta)
                    upsampling_attempts += 1
                upsampled += 1

            if abs(eta_size-mfcc_size) > 0:
                size = min(eta_size, mfcc_size)
                eta = eta[:size]
                mat = mat[:size]

            eta = np.array(eta).reshape(-1, 1)
            mat = np.concatenate([mat, eta], axis=1)

            eta_scp_data[key] = mat

        print('{0} -- upsampled {1}, downsampled {2}'.format(scp, upsampled, downsampled))
        out_scp_filename = os.path.join(out_feats_dir, scp) 
        tmp_ark_filename = os.path.join(out_feats_dir, scp.replace('.scp', '.tmp.ark'))
        out_ark_filename = os.path.join(out_feats_dir, scp.replace('.scp', '.ark'))

        out_scp_data = ((key,mat) for key,mat in eta_scp_data.items())

        with open(tmp_ark_filename,'wb') as fid:
            for key, mat in out_scp_data: 
                kaldi_io.write_mat(fid, mat, key=key)

        cmd = 'copy-feats --compress=true ark:{0} ark,scp:{1},{2}'\
            .format(tmp_ark_filename, out_ark_filename, out_scp_filename)
        os.system(cmd)
        os.remove(tmp_ark_filename)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir',  type=str, help='input Kaldi feature directory')
    parser.add_argument('eta_dir',    type=str, help='input directory with estimated tongue activity')
    parser.add_argument('output_dir', type=str, help='output feature directory')
    args = parser.parse_args()

    main(args.input_dir, args.eta_dir, args.output_dir)
