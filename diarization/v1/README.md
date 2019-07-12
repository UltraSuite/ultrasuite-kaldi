## Recipe for speaker diarization of the UltraSuite repository using Estimated Tongue Activity

This recipe trains models for the diarization of child speech therapy sessions, as described by [1]. It is essentially a supervised model that learns to recognize speech that is assigned to child, therapist, or silence/noise.

This method uses the transcriptions of the UXTD dataset of the [UltraSuite Repository](https://ultrasuite.github.io), which contain tags denoting whether a word is spoken by the therapist or the child. We allow HMMs for child, therapist, and optional silence and noise. Turn-taking sequences are derived from the transcription and there is no initial alignment with respect to the features. The HMM-GMMs use a combination of 20 MFCCs, 3 f0 features, and Estimated Tongue Activity (ETA).



#### Requirements

This is a Kaldi recipe, so you'll need to have [Kaldi](<https://github.com/kaldi-asr/kaldi>) installed to use it.

Please make sure the following Python libraries and their dependencies are available.

- [praatio](<https://github.com/timmahrt/praatIO>)
- [pyannote.metrics](<https://github.com/pyannote/pyannote-metrics>)
- [kaldi-io-for-python](<https://github.com/vesis84/kaldi-io-for-python>)



#### Getting started

Once all dependencies are installed, you'll need to edit `path.sh`. Please replace `<PATH-TO-KALDI-ROOT>` with the path to your Kaldi installation. You can also add any other libraries to your `PYTHONPATH` here.

The recipe directory assumes the standard Kaldi scripts are available in the current directory. E.g.:
`ln -s ${KALDI_ROOT}/egs/wsj/s5/steps steps`
`ln -s ${KALDI_ROOT}/egs/wsj/s5/utils utils`

The recipe's global variables are edited in the `config.sh` file. You need to point the variable `ULTRASUITE` to the location where you store the UltraSuite Repository.



#### Recipe

After all variables are edited, you can run the recipe by running `run.sh` The recipe goes according to the following stages:

0. Prepare Kaldi data directories
1. Extract MFCC, F0, and ETA features
2. Prepare lang and LM Kaldi directories
3. Train HMM-GMM
4. Decode and score reference alignments
5. Decode UltraSuite data

Each stage can be controlled separately by setting `stage_start` and `stage_end`in the global configuration file `config.sh`.



#### Citation

Further details and results can be found in the paper. If you use this recipe or its outputs, or improve upon this work, please cite [1].

[1] Ribeiro, M. S., Eshky, A., Richmond, K. & Renals, S., (2019). 
[Ultrasound tongue imaging for diarization and alignment of child speech therapy sessions](https://arxiv.org/abs/1907.00818).
Proceedings of INTERSPEECH. Graz, Austria.

