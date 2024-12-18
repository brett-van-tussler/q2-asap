from q2_types.per_sample_sequences import CasavaOneEightSingleLanePerSampleDirFmt

def analyzeAmplicons_pipeline(ctx, sequences, ref_sequence, trimmer, aligner,
                              aligner_index, run_name, config_fp):
    
    trimmer_action = ctx.get_action('trimmers', trimmer)
    aligner_index_action = ctx.get_action('aligners', aligner_index)
    aligner_action = ctx.get_action('aligners', aligner)
    output_combiner_action = ctx.get_action('ASAP', 'outputCombiner')
    bam_processor_action = ctx.get_action('ASAP', 'bamProcessor')
    sequence_to_pairs = ctx.get_action('aligners', 'sequence_to_pairs')
    trimmed_collection_combiner = ctx.get_action('ASAP', 'trimmedCollectionCombiner')
    aligned_collection_combiner = ctx.get_action('ASAP', 'alignedCollectionCombiner')
    xml_collection_combiner = ctx.get_action('ASAP', 'xmlCollectionCombiner')

    sequence_collection, = sequence_to_pairs(sequences=sequences)

    # initialize results
    results = []
    trimmer_result_dict = dict()
    aligner_result_dict = dict()
    bam_processor_result_dict = dict()

    aligner_index_result, = aligner_index_action(ref_sequence)

    for sample_id, seq in sequence_collection.items():

        trimmer_result = trimmer_action(seq).output
        trimmer_result_dict[sample_id + "_trimmed"] = trimmer_result

        # using the comma, doesn't work, we have to add '.output_bam'
        aligner_result = aligner_action(seq, aligner_index_result).output_bam
        aligner_result_dict[sample_id + "_aligned"] = aligner_result

        bam_processor_result = bam_processor_action(alignment_map=aligner_result,
                                                    config_file_path=config_fp).xml_output_artifact
        bam_processor_result_dict[sample_id + "_xml"] = bam_processor_result

    trimmed_results_combined = trimmed_collection_combiner(trimmer_result_dict).trimmed_output_artifact
    aligned_results_combined = aligned_collection_combiner(aligner_result_dict).aligned_output_artifact
    xml_results_combined = xml_collection_combiner(bam_processor_result_dict).xml_output_artifact
    
    #TODO: this needs to work on the collection generated from the for loop above, so we will convert the collection to single artifact then run this combine.
    output_combiner_result = output_combiner_action(xml_dir=xml_results_combined, run_name=run_name).xml_output

    results.append(trimmed_results_combined)
    results.append(aligner_index_result)
    results.append(aligned_results_combined)
    results.append(xml_results_combined)
    results.append(output_combiner_result)

    return tuple(results)

