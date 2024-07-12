# ----------------------------------------------------------------------------
# Copyright (c) 2024, Nicole Sylvester.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import pandas as pd

from qiime2.plugin.testing import TestPluginBase
from qiime2.plugin.util import transform
from qiime2 import Artifact

# from q2_asap.analyzeAmplicons_pipeline import analyzeAmplicons_pipeline

class TestAnalyzeAmpliconPipeline(TestPluginBase):
    package = 'q2_asap.tests'

    def test_analyzeAmplicon_pipeline(self):
        # access the pipeline as QIIME 2 sees it,
        # for correct assignment of `ctx` variable
        analyzeAmplicons_pipeline = self.plugin.pipelines['analyzeAmplicons_pipeline']

        #import artifact for reference sequence
        ref_sequence_artifact = Artifact.import_data('FeatureData[Sequence]', '/home/nsylvester/scratch/q2-asap/q2_asap/tests/data/wuhan_sequence.fasta')

        # get sequences (paired-end-demux.qza)
        sequences_artifact = Artifact.load('q2_asap/tests/data/paired-end-demux.qza')

        # run the pipeline
        results = analyzeAmplicons_pipeline(sequences = sequences_artifact, ref_sequence = ref_sequence_artifact)

        # assert output
        self.assertTrue(len(results) > 0)
