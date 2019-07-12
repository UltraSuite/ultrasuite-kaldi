#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compute Estimated Tongue Activity (ETA) from ultrasound data.
Computation is done is parallel over multiple CPU cores (using multiprocessing lib).


input: Kaldi data directory
output: Estimated tongue activity
max_cores: maximum number of parallel jobs
by_speaker: estimate and save ETA by speaker identity

tad function:
    input (str) : filename
    output (str): filename,offset,fps,activity

Date: 2018
Author: M. Sam Ribeiro
"""

import os
import sys
import argparse
import numpy as np

from multiprocessing import Pool
from multiprocessing import cpu_count

from sklearn.preprocessing import MinMaxScaler

# limits number of threads available to numpy
os.environ['MKL_NUM_THREADS'] = '1'


def read_filelist(filename):
    ''' read wav.scp to find waveform paths '''
    filelist = []
    with open(filename) as fid:
        for line in fid.readlines():
            line = line.rstrip().split()
            file_id, wav_path = line[0], line[2]
            filelist.append((file_id, wav_path))
    return filelist


def filelist_by_speaker(filelist):
    ''' break filelist in smaller lists organized by speaker '''
    speaker_filelist = {}

    for f in filelist:
        # we assume that the first field of the file_id
        # is always the speaker
        speaker = f[0].split('-')[0]

        if speaker in speaker_filelist:
            speaker_filelist[speaker].append((f))
        else:
            speaker_filelist[speaker] = [f]

    return speaker_filelist


def write_to_file(data, filename):
    ''' write data to filename '''
    output = open(filename, 'w')
    for line in data:
        output.write(line+'\n')
    output.close()



def estimate_tongue_activity(input_file_item):
    ''' 
        Single pickable function to estimate tongue activity.
        To be used with multiprocessing.Pool.
        Assumes filename is .wav and that .ult and .param are in the same directory
        Cannot handle segments or other hyperparameter inputs
    '''

    file_id, filename = input_file_item

    # window over which to compute tongue activity
    # each frame is ~1000/120 msecs
    # default 20 frames is ~166 msecs
    window_size=20

    # scaler object for unity based normalization
    # use None for no normalization
    scaler_obj = MinMaxScaler()
    #scaler_obj = None

    # read ultrasound and parameters from files
    ult_f   = filename.replace('.wav', '.ult')
    prm_f = filename.replace('.wav', '.param')

    params = {}
    with open(prm_f) as param_id:
        for line in param_id:
            name, var = line.partition("=")[::2]
            params[name.strip()] = float(var)

    fid = open(ult_f, "r")
    ultrasound = np.fromfile(fid, dtype=np.uint8)
    fid.close()

    frame_size = int( params['NumVectors'] * params['PixPerVector'] )
    params['frame_size'] = frame_size

    n_frames =  int( ultrasound.size / frame_size )
    ultrasound = ultrasound.reshape((n_frames, frame_size))

    # get tongue activity from ultrasound
    activity = []
    total_frames, frame_size = ultrasound.shape

    if total_frames == 0:
        print('Warning: empty ultrasound for {0}'.format(file_id))
        return ','.join([file_id, str(0.0), str(0.0), str(0.0)])

    for i in range(window_size, total_frames-window_size):
        segment = ultrasound[i-window_size:i+window_size, :]
        std = np.std(segment, axis=0).reshape(-1, 1)
        dst = np.mean(std, axis=0)[0]
        activity.append(dst)

    if len(activity) == 0:
        print('Warning: no activity for {0}'.format(file_id))
        return ','.join([file_id, str(0.0), str(0.0), str(0.0)])

    # pad activity to account for window shift
    activity = [activity[0]]*window_size + activity + [activity[-1]]*window_size
    activity = np.array(activity).reshape(-1, 1)

    if scaler_obj:
        activity = scaler_obj.fit_transform(activity)

    act = activity

    # pad according to audio time offset
    time_offset = params['TimeInSecsOfFirstFrame']
    fps = params['FramesPerSec']

    missing_frames = int( time_offset * fps )
    pad = np.zeros((missing_frames, 1))
    act = np.concatenate([pad, act], axis=0)

    # output format
    activity = ' '.join([str(v) for v in act.reshape(-1,)])
    output = ','.join( [file_id, str(time_offset), str(fps), activity] )

    return output



def main(data_dir, output_dir, max_cores, by_speaker=False):

    # find wav.scp
    wav_scp = os.path.join(data_dir, 'wav.scp')
    if not os.path.isfile(wav_scp):
        print('Could not find wav.scp in data directory')
        sys.exit(1)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # read waveform list
    filelist = read_filelist(wav_scp)

    # break larger filelist by speaker
    # this will cause activity to be saved separately for each speaker
    # it is useful if using a large number of files
    if by_speaker:
        filelist = filelist_by_speaker(filelist)
    else:
        filelist = {'tad':filelist}

    # available cpu cores
    cpu_cores = cpu_count()

    for key in filelist:

        data = filelist[key]
        # use the minimum over maximum requested cores,
        # available cores, or number of files
        cores = min([max_cores, len(data), cpu_cores])
        print('Estimating tongue activity for {0}: {1} files over {2} cores'.format(key, len(data), cores))

        pool = Pool(processes=cores)
        tad_data = pool.map(estimate_tongue_activity, data)
        pool.close()

        output_filename = os.path.join(output_dir, key + '.tad')
        write_to_file(tad_data, output_filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('datadir',  type=str,  help='Kaldi data directory')
    parser.add_argument('outputdir',  type=str,  help='Output directory')
    parser.add_argument('--max-cores',  dest='max_cores', type=int,  help='Maximum number of CPU cores')
    parser.add_argument('--by-speaker', dest='by_speaker', action='store_true', help='Process data by speaker ID')
    parser.set_defaults(max_cores=20)
    parser.set_defaults(by_speaker=False)
    args = parser.parse_args()

    main(args.datadir, args.outputdir, args.max_cores, args.by_speaker)
