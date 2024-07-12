#TODO: config file for bbduk/fastp/trimmer params
#TODO: bamprocessor, outputCombiner
def analyzeAmplicons_pipeline(ctx, sequences, ref_sequence, config_file_path):

    #TODO: long string of params in json file that we will use as trimmer/aligner_params 
    config = open(config_file_path)
    data = json.load(config)

    trimmer = data['ASAP_parameters']['trimmer']['name']
    trimmer_action = ctx.get_action('trimmers', trimmer)

    aligner_index = data['ASAP_parameters']['aligner']['index']
    aligner_index_action = ctx.get_action('aligners', aligner_index)
    
    aligner = data['ASAP_parameters']['aligner']['name']
    aligner_action = ctx.get_action('aligners', aligner)
    
    # initialize results
    results = []

    trimmer_results = trimmer_action(sequences)
    # results.append(trimmer_results)

    aligner_index_result, = aligner_index_action(ref_sequence)
    # results.append(aligner_index_result)
    
    aligner_result, = aligner_action(sequences = sequences, reference_index = aligner_index_result)
    results.append(aligner_result)

    return tuple(results)