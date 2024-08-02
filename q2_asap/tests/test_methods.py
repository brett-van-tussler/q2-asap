# ----------------------------------------------------------------------------
# Copyright (c) 2024, Nicole Sylvester.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from qiime2.plugin.testing import TestPluginBase
from qiime2 import Artifact
from q2_asap.outputCombiner import outputCombiner
from q2_asap._formats import ASAPXMLOutputDirFmt
from q2_asap.bamProcessor import bamProcessor
from q2_nasp2_types.alignment import BAMSortedAndIndexedDirFmt
from q2_types.per_sample_sequences import PairedEndSequencesWithQuality
from q2_types.sample_data import SampleData
from q2_types.per_sample_sequences import SingleLanePerSamplePairedEndFastqDirFmt

class TestAnalyzeAmpliconPipeline(TestPluginBase):
    package = 'q2_asap.tests'

    def test_analyzeAmplicon_pipeline(self):
        # access the pipeline as QIIME 2 sees it,
        # for correct assignment of `ctx` variable
        analyzeAmplicons_pipeline = self.plugin.pipelines[
            'analyzeAmplicons_pipeline']

        # import artifact for reference sequence
        ref_sequence_art = Artifact.import_data(
            'FeatureData[Sequence]', 'q2_asap/tests/data/wuhan_sequence.fasta')

        # load in sequences (paired-end-demux.qza)
        sequences_artifact = Artifact.load(
            'q2_asap/tests/data/paired-end-demux-modified.qza')
        

        print("TYPE" + str(type(sequences_artifact)))

        config_file_path = 'q2_asap/tests/data/SARS2_variant_detection.json'

        results = analyzeAmplicons_pipeline(sequences=sequences_artifact,
                                            ref_sequence=ref_sequence_art,
                                            trimmer="bbduk_paired",
                                            aligner="bwa_mem_paired",
                                            aligner_index="bwa_index",
                                            run_name="Test",
                                            config_fp=config_file_path)

        self.assertTrue(len(results) == 5)


class TestOutputCombiner(TestPluginBase):
    package = 'q2_asap.tests'

    def test_output_combiner(self):
        xml_art = Artifact.load('q2_asap/tests/data/asap_xmls.qza')
        run_name = "TestRun"
        result = outputCombiner(run_name=run_name,
                                xml_dir=xml_art.view(ASAPXMLOutputDirFmt))
        assert result is not None


class TestBamProcessor(TestPluginBase):
    package = 'q2_asap.tests'

    def test_bam_processor(self):

        config_fp = 'q2_asap/tests/data/SARS2_variant_detection.json'

        # import alignment map artifact data
        am_artifact = Artifact.import_data('SampleData[BAMSortedAndIndexed]',
                                           'q2_asap/tests/data/bwamem_copy')
        result = bamProcessor(
            alignment_map=am_artifact.view(BAMSortedAndIndexedDirFmt),
            config_file_path=config_fp)

        assert result is not None
