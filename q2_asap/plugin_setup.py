# ----------------------------------------------------------------------------
# Copyright (c) 2024, Nicole Sylvester.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from qiime2.plugin import Citations, Plugin, SemanticType, Str, Int, Float
citations = Citations.load("citations.bib", package="q2_asap")
from q2_asap import __version__

from q2_asap.analyzeAmplicons import analyzeAmplicons
from q2_types.per_sample_sequences import PairedEndSequencesWithQuality, SequencesWithQuality
from q2_types.sample_data import SampleData

from q2_types.per_sample_sequences._type import AlignmentMap
from ._formats import ASAPXMLFormat, ASAPHTMLFormat, ASAPXMLOutputDirFmt, ASAPHTMLOutputDirFmt
from ._types import ASAPXML, ASAPHTML
from q2_nasp2_types.index import BWAIndex
from q2_nasp2_types.alignment import BAM
from q2_types.feature_data import FeatureData


plugin = Plugin(
    name="ASAP",
    version=__version__,
    website="https://example.com",
    package="q2_asap",
    description="A qiime2 ASAP plugin",
    short_description="ASAP plugin",
    # Please retain the plugin-level citation of 'Caporaso-Bolyen-2024'
    # as attribution of the use of this template, in addition to any citations
    # you add.
    citations=[citations['Caporaso-Bolyen-2024']]
)


plugin.methods.register_function(
    function=analyzeAmplicons,
    inputs={'sequences': SampleData[PairedEndSequencesWithQuality]},
    parameters={'name': Str,
                'depth': Int,
                'breadth': Float,
                'min_base_qual': Int,
                'consensus_proportion': Float,
                'fill_gaps': Str,
                'aligner': Str,
                'aligner_args': Str
                },
    outputs=[
             ('output_bams', FeatureData[BAM]),
             ('bwa_index', BWAIndex),
             ('asap_xmls', ASAPXML)
             ],
    input_descriptions={'sequences': 'The amplicon sequences to be analyzed'},
    parameter_descriptions={
                'name': 'Str',
                'depth': 'Int',
                'breadth': 'Float',
                'min_base_qual': 'Int',
                'consensus_proportion': 'Float',
                'fill_gaps': 'Str',
                'aligner': 'Str',
                'aligner_args': 'Str'},
    output_descriptions={
        'output_bams': 'SampleData[AlignmentMap]',
        'bwa_index': 'BWAIndex',
        'asap_xmls': 'ASAPXMLOutputDirFmt'
        },
    name='analyzeAmplicons',
    description=(""),
    citations=[]
)

plugin.register_formats( ASAPHTMLOutputDirFmt, ASAPXMLOutputDirFmt)
# plugin.register_semantic_types(ASAPHTMLOutputs)
plugin.register_semantic_type_to_format(
    ASAPHTML, artifact_format = ASAPHTMLOutputDirFmt, 
)
# plugin.register_semantic_types(ASAPXMLOutputs)
plugin.register_semantic_type_to_format(
    ASAPXML, artifact_format = ASAPXMLOutputDirFmt, 
)


