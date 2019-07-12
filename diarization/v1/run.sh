#!/bin/bash
# speaker labelling for UltraSuite version 1.0
# this basic recipe uses MFCCs, F0 and Estimated Tongue Activity (ETA)
# initial speaker labels are inferred from UXTD transcriptions
# 
# This implements something similar to Ribeiro et al (2019)
# Ultrasound tongue imaging for diarization and alignment of child speech therapy sessions
# https://arxiv.org/pdf/1907.00818.pdf


# most arguments are taken from this config file
# edit this to control the flow of the recipe
[ -f config.sh ] && . ./config.sh

[ -f path.sh ] && . ./path.sh
[ -f cmd.sh ] && . ./cmd.sh
. utils/parse_options.sh


# Stage 0: Prepare Kaldi data directories
if [ $stage_start -le 0 ]; then

    # prepare training data directories
    python ./local/data/train-uxtd.py ${UXTD_CORE} ${LABEL_DIR}/uxtd \
        ${DATA_DIR}/train --sr 16000  || exit 1

    # prepare reference data directories for evaluation
    python ./local/data/decode-uxtd.py ${UXTD_CORE} ${LABEL_DIR}/uxtd \
        ${DATA_DIR}/decode/uxtd_reference --sr 16000 --use_reference  || exit 1
    python ./local/data/decode-uxssd-upx.py ${UXSSD_CORE} ${LABEL_DIR}/uxssd\
        ${DATA_DIR}/decode/uxssd_reference --sr 16000 --use_reference  || exit 1
    echo ${nj_ref} > ${DATA_DIR}/decode/uxtd_reference/nj
    echo ${nj_ref} > ${DATA_DIR}/decode/uxssd_reference/nj

    # prepare full data directories for decoding
    python ./local/data/decode-uxtd.py ${UXTD_CORE} ${LABEL_DIR}/uxtd \
        ${DATA_DIR}/decode/uxtd --sr 16000 || exit 1
    python ./local/data/decode-uxssd-upx.py ${UXSSD_CORE} ${LABEL_DIR}/uxssd \
        ${DATA_DIR}/decode/uxssd --sr 16000 || exit 1
    python ./local/data/decode-uxssd-upx.py ${UPX_CORE} ${LABEL_DIR}/upx \
        ${DATA_DIR}/decode/upx --sr 16000  || exit 1

    echo ${nj_uxtd} > ${DATA_DIR}/decode/uxtd/nj
    echo ${nj_uxssd} > ${DATA_DIR}/decode/uxssd/nj
    echo ${nj_upx} > ${DATA_DIR}/decode/upx/nj


    if [ $stage_end -eq 0 ]; then
        exit 0
    fi
fi


# Stage 1: Extract MFCC, F0, and ETA features
if [ $stage_start -le 1 ]; then

    #  make ETA, MFCC, F0 features and merge - training data
    for subset in train; do
        nj=${nj_train}

        # Estimate Tongue Acticity (ETA)
        python ./local/data/make_tongue_activity.py ${DATA_DIR}/train/${subset} \
             ${DATA_DIR}/train/${subset}/data_tad --by-speaker --max-cores ${nj}

        # MFCCs and F0
        steps/make_mfcc_pitch.sh --nj $nj \
            --mfcc-config ${mfcc_conf} --pitch-config ${pitch_conf} \
            --paste_length_tolerance 2 \
            ${DATA_DIR}/train/${subset} \
            ${DATA_DIR}/train/${subset}/log \
            ${DATA_DIR}/train/${subset}/data_mfccs || exit 1

        # Merge and validate directory
        python ./local/data/append_tongue_activity.py \
            ${DATA_DIR}/train/${subset}/data_mfccs \
            ${DATA_DIR}/train/${subset}/data_tad \
            ${DATA_DIR}/train/${subset}/data  || exit 1

        mv ${DATA_DIR}/train/${subset}/feats.scp ${DATA_DIR}/train/${subset}/feats.mfcc.scp
        cat ${DATA_DIR}/train/${subset}/data/*.scp > ${DATA_DIR}/train/${subset}/feats.scp

        steps/compute_cmvn_stats.sh ${DATA_DIR}/train/${subset} || exit 1
        utils/fix_data_dir.sh ${DATA_DIR}/train/${subset}  || exit 1
    done

    # make ETA, MFCC, F0 features and merge - decoding data
    for subset in uxtd_reference uxssd_reference uxtd uxssd upx; do
        nj=$(cat ${DATA_DIR}/decode/${subset}/nj)

        # Estimate Tongue Acticity (ETA)
        python ./local/data/make_tongue_activity.py ${DATA_DIR}/decode/${subset} \
            ${DATA_DIR}/decode/${subset}/data_tad --by-speaker --max-cores ${nj}

        # MFCCs and F0
        steps/make_mfcc_pitch.sh --nj $nj \
            --mfcc-config ${mfcc_conf} --pitch-config ${pitch_conf} \
            --paste_length_tolerance 2 \
            ${DATA_DIR}/decode/${subset} \
            ${DATA_DIR}/decode/${subset}/log \
            ${DATA_DIR}/decode/${subset}/data_mfccs || exit 1

        # Merge and validate directory
        python ./local/data/append_tongue_activity.py \
            ${DATA_DIR}/decode/${subset}/data_mfccs \
            ${DATA_DIR}/decode/${subset}/data_tad  \
            ${DATA_DIR}/decode/${subset}/data || exit 1

        mv ${DATA_DIR}/decode/${subset}/feats.scp ${DATA_DIR}/decode/${subset}/feats.mfcc.scp
        cat ${DATA_DIR}/decode/${subset}/data/*.scp > ${DATA_DIR}/decode/${subset}/feats.scp

        steps/compute_cmvn_stats.sh ${DATA_DIR}/decode/${subset} || exit 1
        utils/fix_data_dir.sh ${DATA_DIR}/decode/${subset}
    done

    if [ $stage_end -eq 1 ]; then
        exit 0
    fi
fi


# Stage 2: Prepare Lang and LM Kaldi directories
if [ $stage_start -le 2 ]; then
    # language directory
    utils/prepare_lang.sh --position-dependent-phones false --sil-prob 0.5 \
        ./local/lang/dict "<unk>" ${DATA_DIR}/lang/tmp ${DATA_DIR}/lang || exit 1
    cp ./local/lang/topo ${DATA_DIR}/lang/topo # replace default topology with 4-state Ergodic HMM
    utils/validate_lang.pl ${DATA_DIR}/lang

    # language model
    utils/format_lm.sh ${DATA_DIR}/lang ./local/lm/lm.arpa.gz \
        ./local/lang/dict/lexicon.txt ${DATA_DIR}/lang_lm || exit 1

    if [ $stage_end -eq 2 ]; then
        exit 0
    fi
fi


# Stage 3: Train HMM-GMM
if [ $stage_start -le 3 ]; then

    steps/train_mono.sh --nj $nj_train --cmd "$train_cmd" --totgauss 1000 \
        ${DATA_DIR}/train/train ${DATA_DIR}/lang ${EXP_DIR} || exit 1

    if [ $stage_end -eq 3 ]; then
        exit 0
    fi
fi


# Stage 4: Decode and score reference alignments
if [ $stage_start -le 4 ]; then

    # Make graph, if needed
    utils/mkgraph.sh ${DATA_DIR}/lang_lm ${EXP_DIR} ${EXP_DIR}/graph || exit 1

    for subset in uxtd uxssd; do
        nj=$(cat ${DATA_DIR}/decode/${subset}_reference/nj)

        # Decode reference utterances
        steps/decode.sh --acwt 0.083333 --skip-scoring true --nj $nj \
            --model ${EXP_DIR}/final.mdl --cmd "$decode_cmd" \
             ${EXP_DIR}/graph ${DATA_DIR}/decode/${subset}_reference ${EXP_DIR}/decode/${subset}_reference || exit 1

        # convert decoder alignment to labels and TextGrids
        # requires Python's praatio to convert labs to TextGrids
        ./local/align/decode-to-labs.sh ./${EXP_DIR} \
            ./${EXP_DIR}/decode/${subset}_reference ./${EXP_DIR}/graph ${DATA_DIR}/decode/${subset}_reference || exit 1

        # scores decoded labels against reference
        # requires Python's pyannote.metrics
        python ./local/score/score-alignment.py \
            --ref ${LABEL_DIR}/${subset}/reference_labels/speaker_labels/lab \
            --hyp ${EXP_DIR}/decode/${subset}_reference/lab \
            --out ${EXP_DIR}/decode/${subset}_reference/score # scores will be written to this directory!
    done

    if [ $stage_end -eq 4 ]; then
        exit 0
    fi
fi


# Stage 5: Decode UltraSuite data
if [ $stage_start -le 5 ]; then

    # Make graph, if needed
    utils/mkgraph.sh ${DATA_DIR}/lang_lm ${EXP_DIR} ${EXP_DIR}/graph || exit 1

    for subset in uxtd uxssd upx; do
        nj=$(cat ${DATA_DIR}/decode/${subset}/nj)

        # Decode all utterances
        steps/decode.sh --acwt 0.083333 --skip-scoring true --nj $nj \
            --model ${EXP_DIR}/final.mdl --cmd "$decode_cmd" \
             ${EXP_DIR}/graph ${DATA_DIR}/decode/${subset} \
             ${EXP_DIR}/decode/${subset} || exit 1

        # convert decoder alignment to labels and TextGrids
        # requires Python's praatio to convert labs to TextGrids
        ./local/align/decode-to-labs.sh ./${EXP_DIR} \
            ./${EXP_DIR}/decode/${subset} ./${EXP_DIR}/graph ${DATA_DIR}/decode/${subset} || exit 1
    done

    if [ $stage_end -eq 5 ]; then
        exit 0
    fi
fi
