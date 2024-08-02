from pathlib import Path

import pandas as pd
from qiime2.util import duplicate
from q2_types.per_sample_sequences import CasavaOneEightSingleLanePerSampleDirFmt, SingleLanePerSamplePairedEndFastqDirFmt
import os

def sequence_to_pairs(
    sequences: CasavaOneEightSingleLanePerSampleDirFmt,
) -> dict[str, CasavaOneEightSingleLanePerSampleDirFmt]:
    output = dict()

    #sequences_dir_fmt = sequences.view(CasavaOneEightSingleLanePerSampleDirFmt)
    sequences = sequences.view(sequences.format)
    seq_df = sequences.manifest.view(pd.DataFrame).reset_index()
    # seq_df = seq_df.pivot(index='sample-id', columns='direction', values='filename').reset_index()
    # seq_df[['forward', 'reverse']] = seq_df[['forward', 'reverse']].applymap(os.path.basename)

    paired_reads = seq_df.values.tolist()
    print(paired_reads)
    for sample_name, f, r in paired_reads:
        paired_dir = CasavaOneEightSingleLanePerSampleDirFmt()
        forward_path = paired_dir.path.joinpath(Path(f).name)
        reverse_path = paired_dir.path.joinpath(Path(r).name)

        duplicate(src=f, dst=str(forward_path))
        duplicate(src=r, dst=str(reverse_path))

        output[sample_name] = paired_dir
    print(output)
    return output

def analyzeAmplicons_pipeline(ctx, sequences, ref_sequence, trimmer, aligner,
                              aligner_index, run_name, config_fp):

    trimmer_action = ctx.get_action('trimmers', trimmer)
    aligner_index_action = ctx.get_action('aligners', aligner_index)
    aligner_action = ctx.get_action('aligners', aligner)
    output_combiner_action = ctx.get_action('ASAP', 'outputCombiner')
    bam_processor_action = ctx.get_action('ASAP', 'bamProcessor')
    sequence_to_pairs = ctx.get_action('aligners', 'sequence_to_pairs')

    print(sequences)
    sequence_collection = sequence_to_pairs(sequences=sequences)

    # initialize results
    results = []
    trimmer_results_dict = dict()
    aligner_index_dict = dict()
    aligner_result_dict = dict()
    bam_processor_result_dict = dict()

    for sample_id, seq in sequence_collection.items():

        trimmer_results, = trimmer_action(seq)
        trimmer_results_dict[sample_id] = trimmer_results

        aligner_index_result, = aligner_index_action(ref_sequence)
        aligner_index_dict[sample_id] = aligner_index_result

        aligner_result, = aligner_action(seq, aligner_index_result)
        aligner_result_dict[sample_id] = aligner_result

        bam_processor_result, = bam_processor_action(alignment_map=aligner_result,
                                                    config_file_path=config_fp)
        bam_processor_result_dict[sample_id] = bam_processor_result
    
    #TODO: this needs to work on the collection generated from the for loop above, so we will convert the collection to single artifact then run this combine.
    output_combiner_result, = output_combiner_action(xml_dir=bam_processor_result, run_name=run_name)

    results.append(trimmer_results_dict)
    results.append(aligner_index_dict)
    results.append(aligner_result_dict)
    results.append(bam_processor_result_dict)
    results.append(output_combiner_result)

    return tuple(results)

