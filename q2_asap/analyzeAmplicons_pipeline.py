def analyzeAmplicons_pipeline(ctx, sequences, ref_sequence, trimmer, aligner,
                              aligner_index, run_name, config_fp):

    trimmer_action = ctx.get_action('trimmers', trimmer)
    aligner_index_action = ctx.get_action('aligners', aligner_index)
    aligner_action = ctx.get_action('aligners', aligner)
    output_combiner_action = ctx.get_action('ASAP', 'outputCombiner')
    bam_processor_action = ctx.get_action('ASAP', 'bamProcessor')

    # initialize results
    results = []

    trimmer_results, = trimmer_action(sequences)
    results.append(trimmer_results)

    aligner_index_result, = aligner_index_action(ref_sequence)
    results.append(aligner_index_result)

    aligner_result, = aligner_action(sequences, aligner_index_result)
    results.append(aligner_result)

    bam_processor_result, = bam_processor_action(alignment_map=aligner_result,
                                                 config_file_path=config_fp)
    results.append(bam_processor_result)
    
    #TODO: is this in pipeline?
    output_combiner_result, = output_combiner_action(xml_dir=bam_processor_result, run_name=run_name)
    results.append(output_combiner_result)

    return tuple(results)
