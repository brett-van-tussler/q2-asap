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
    citations=[citations['Caporaso-Bolyen-2024'], citations['ASAP']]
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
                'name': 'Name of ASAP run',
                'depth': 'minimum read depth required to consider a position covered. [default: 100]',
                'breadth': 'minimum breadth of coverage required to consider an amplicon as present. [default: 0.8]',
                'min_base_qual': 'what is the minimum base quality score (BQS) to use a position (Phred scale, i.e. 10=90, 20=99, 30=99.9 accuracy',
                'consensus_proportion': 'minimum proportion required to call at base at that position, else 'N'. [default: 0.8]',
                'fill_gaps': 'fill no coverage gaps in the consensus sequence [default: False], optional parameter is the character to use for filling [defaut: n]',
                'aligner': 'aligner to use for read mapping, supports bowtie2, novoalign, and bwa. [default: bowtie2]',
                'aligner_args': "additional arguments to pass to the aligner, enclosed in ''."},
    output_descriptions={
        'output_bams': 'directory of bam files',
        'bwa_index': 'directory of files that hold BWA indices used to align sequencing reads to the reference genome',
        'asap_xmls': 'directory of XML files with complete details for each assay against each sample. \
                        These details include number of reads aligning to each target, any SNPs found above a user-defined threshold, \
                        and the nucleotide distribution at each of these SNP positions. For ROI assays, the output includes the sequence \
                        distribution at each of the regions of interest -- both the DNA sequences and translated into amino acid sequences.'
        },
    name='analyzeAmplicons',
    description=(""),
    citations=[citations['ASAP']]
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


