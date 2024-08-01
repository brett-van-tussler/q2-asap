# ----------------------------------------------------------------------------
# Copyright (c) 2024, Nicole Sylvester.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from qiime2.plugin import Citations, Plugin, Str, TypeMap, Choices, Bool
from q2_asap import __version__
from q2_types.per_sample_sequences import (PairedEndSequencesWithQuality,
                                           SequencesWithQuality)
from q2_types.sample_data import SampleData
from q2_types.per_sample_sequences._type import AlignmentMap
from ._formats import ASAPXMLOutputDirFmt, ASAPHTMLOutputDirFmt
from ._types import ASAPXML, ASAPHTML
from q2_nasp2_types.index import BWAIndex
from q2_nasp2_types.alignment import BAMSortedAndIndexed, SAM
from q2_types.feature_data import FeatureData, Sequence
from q2_types.bowtie2 import Bowtie2Index
from q2_asap.analyzeAmplicons_pipeline import analyzeAmplicons_pipeline
from q2_asap.outputCombiner import outputCombiner
from q2_asap.bamProcessor import bamProcessor
from q2_asap.formatOutput import formatOutput

citations = Citations.load("citations.bib", package="q2_asap")

plugin = Plugin(
    name="ASAP",
    version=__version__,
    website="https://example.com",
    package="q2_asap",
    description="Copyright 2015 TGen North. All rights reserved. \
Available for academic and research use only under a license from \
The Translational Genomics Research Institute (TGen) \
that is free for non-commercial use. Distributed on an 'AS IS' basis \
without warranties or conditions of any kind, either express or implied.",

    short_description="ASAP plugin",
    # Please retain the plugin-level citation of 'Caporaso-Bolyen-2024'
    # as attribution of the use of this template, in addition to any citations
    # you add.
    citations=[citations['Caporaso-Bolyen-2024'], citations['ASAP']]
)

plugin.register_formats(ASAPHTMLOutputDirFmt, ASAPXMLOutputDirFmt)
plugin.register_semantic_type_to_format(
    ASAPHTML, artifact_format=ASAPHTMLOutputDirFmt,
)
plugin.register_semantic_type_to_format(
    ASAPXML, artifact_format=ASAPXMLOutputDirFmt,
)

# maps input types to output types
aligner_type, sequences, trimmer_out, index_out = TypeMap({
    (Str % Choices(['bwa_mem_single']), SampleData[SequencesWithQuality]):
        (SampleData[SequencesWithQuality], BWAIndex),
    (Str % Choices(['bwa_mem_paired']),
        SampleData[PairedEndSequencesWithQuality]):
        (SampleData[PairedEndSequencesWithQuality], BWAIndex),
    (Str % Choices(['bowtie2']),
        SampleData[PairedEndSequencesWithQuality]):
        (SampleData[PairedEndSequencesWithQuality], Bowtie2Index),
})

# register analyzeAmplicon pipeline
plugin.pipelines.register_function(
    function=analyzeAmplicons_pipeline,
    inputs={
        'sequences': sequences,
        'ref_sequence': FeatureData[Sequence]
    },
    parameters={
                'trimmer': Str,
                'aligner_index': Str,
                'aligner': aligner_type,
                'run_name': Str,
                'config_fp': Str
               },
    outputs=[
        ('trimmer_results', trimmer_out),
        ('aligner_index_result', index_out),
        ('aligner_result', SampleData[AlignmentMap]),
        ('bam_processor_result', ASAPXML),
        ('output_combiner_result', ASAPXML)
    ],
    input_descriptions={
        'sequences': 'The sequences to be analyzed',
        'ref_sequence': 'The reference sequence used to build bwa index'
    },
    parameter_descriptions={'trimmer': 'The trimmer to use',
                            'aligner_index': 'The aligner index to use',
                            'aligner': 'Type of aligner to use',
                            'run_name': 'The name of the pipeline run',
                            'config_fp': 'The path to the config file'
                            },
    output_descriptions={
        'trimmer_results': 'The result after completing trimming',
        'aligner_index_result': 'The resulting aligner index',
        'aligner_result': 'The result of aligning reads \
with specified aligner',
        'bam_processor_result': 'The result of bam processing',
        'output_combiner_result': 'The resulting combined xml'
    },
    name='Analyze Amplicons Pipeline',
    description=("A pipeline to run analyze amplicons"),
    citations=[citations['ASAP']]
)

plugin.methods.register_function(
    function=outputCombiner,
    inputs={'xml_dir': ASAPXML},
    parameters={'run_name': Str},
    outputs=[
             ('output_dir', ASAPXML),
             ],
    input_descriptions={'xml_dir': 'The file directory that holds xml files'},
    parameter_descriptions={'run_name': 'The name of ASAP run'},
    output_descriptions={'output_dir': 'The output file name of the \
combined xml'},
    name='outputCombiner',
    description=(""),
    citations=[citations['ASAP']]
)

plugin.methods.register_function(
    function=bamProcessor,
    inputs={'alignment_map' : SampleData[AlignmentMap] |
            SampleData[SAM] | SampleData[BAMSortedAndIndexed]},
    parameters={'config_file_path': Str},
    outputs=[
             ('xml_output_dir', ASAPXML),
             ],
    input_descriptions={'alignment_map': 'The resulting files \
after running aligner'},
    parameter_descriptions={'config_file_path': 'The config file \
that holds other params'},
    output_descriptions={'xml_output_dir': 'The xml artifact'},
    name='bamProcessor',
    description=(""),
    citations=[citations['ASAP']]
)

plugin.visualizers.register_function(
    function=formatOutput,
    inputs={'asap_xml_artifact' :  ASAPXML},
    parameters={
                'stylesheet': Str, 
                'text': Bool
                },
    input_descriptions={'asap_xml_artifact': 'The combined xml file to style'},
    parameter_descriptions={'stylesheet': 'The xslt stylesheet',
                            'text': 'Output as text bool. If you select text, the output will be stored directly into the qiime index.html file.'},
    name='formatOutput',
    description=("Input your own designed XSLT transform or use a pre-made one. Non html files generated will be linked in the index.html for download"),
    citations=[citations['ASAP']]
)
