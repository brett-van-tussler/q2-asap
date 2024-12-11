# ----------------------------------------------------------------------------
# Copyright (c) 2024, Nicole Sylvester.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import os
from qiime2.plugin.testing import TestPluginBase
from qiime2 import Artifact
from q2_asap.outputCombiner import (
    outputCombiner, xmlCollectionCombiner,
    alignedCollectionCombiner, trimmedCollectionCombiner)
from q2_asap._formats import ASAPXMLOutputDirFmt, ASAPJSONOutputDirFmt
from q2_asap.bamProcessor import bamProcessor
from q2_nasp2_types.alignment import BAMSortedAndIndexedDirFmt


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

        # load in sequences
        # sequences_artifact = Artifact.import_data(
        # 'SampleData[PairedEndSequencesWithQuality]',
        # 'q2_asap/tests/data/paired-end-demux-modified')
        sequences_artifact = Artifact.load(
            'q2_asap/tests/data/paired-end-demux.qza')

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

    def test_xml_collection_combiner(self):
        xml_art_1 = Artifact.load(
            'q2_asap/tests/data/asap_parallel_output/bam_processor_result/'
            'SARS2_1424866_xml.qza')
        xml_art_2 = Artifact.load(
            'q2_asap/tests/data/asap_parallel_output/bam_processor_result/'
            'SARS2_1425430_xml.qza')
        xml_dict = {"art_1": xml_art_1.view(
            xml_art_1.format), "art_2": xml_art_2.view(xml_art_2.format)}
        result = xmlCollectionCombiner(
            xml_collection=xml_dict)
        assert result

    def test_aligned_collection_combiner(self):
        aligned_art_1 = Artifact.load(
            'q2_asap/tests/data/asap_parallel_output/aligner_result/'
            'SARS2_1424866_aligned.qza')
        aligned_art_2 = Artifact.load(
            'q2_asap/tests/data/asap_parallel_output/aligner_result/'
            'SARS2_1425430_aligned.qza')
        aligned_dict = {
            "art_1": aligned_art_1.view(aligned_art_1.format),
            "art_2": aligned_art_2.view(aligned_art_2.format)
        }
        result = alignedCollectionCombiner(
            aligned_collection=aligned_dict)
        assert result

    def test_trimmed_collection_combiner(self):
        from q2_types.per_sample_sequences import (
            CasavaOneEightSingleLanePerSampleDirFmt
        )

        trimmed_art_1 = Artifact.load(
            'q2_asap/tests/data/asap_parallel_output/trimmer_results/'
            'SARS2_1424866_trimmed.qza')
        trimmed_art_2 = Artifact.load(
            'q2_asap/tests/data/asap_parallel_output/trimmer_results/'
            'SARS2_1425430_trimmed.qza'
        )

        trimmed_dict = {"art_1": trimmed_art_1.view(
            CasavaOneEightSingleLanePerSampleDirFmt),
            "art_2": trimmed_art_2.view(CasavaOneEightSingleLanePerSampleDirFmt)
        }

        result = trimmedCollectionCombiner(
            trimmed_collection=trimmed_dict)

        assert result


class TestBamProcessor(TestPluginBase):
    package = 'q2_asap.tests'

    def test_bam_processor(self):

        config_fp = 'q2_asap/tests/data/SARS2_variant_detection.json'

        # import alignment map artifact data
        bam_artifact = Artifact.import_data('SampleData[BAMSortedAndIndexed]',
                                            'q2_asap/tests/data/bwamem_copy')
        result = bamProcessor(
            alignment_map=bam_artifact.view(BAMSortedAndIndexedDirFmt),
            config_file_path=config_fp)

        assert result is not None


class XMLJSONTransformer(TestPluginBase):
    package = 'q2_asap.tests'

    def test_xml_to_json(self):
        in_ = Artifact.load(self.get_data_path(
            'asap_parallel_output/output_combiner_result.qza'
        )).view(ASAPXMLOutputDirFmt)

        tx = self.get_transformer(ASAPXMLOutputDirFmt, ASAPJSONOutputDirFmt)

        observed = tx(in_)

        # get file names in the observed directory
        observed_dir = str(observed)
        observed_files = sorted([f for f in os.listdir(
            observed_dir) if os.path.isfile(os.path.join(observed_dir, f))])

        assert all(file.endswith('.json') for file in observed_files)

    # def test_json_to_xml(self):
    #     #TODO: get some json output to test this

    #     in_ = (
    #         Artifact
    #         .load(self.get_data_path('asap_parallel_output/output_combiner_result.qza'))
    #         .view(ASAPJSONOutputDirFmt)
    #     )
    #     tx = self.get_transformer(ASAPJSONOutputDirFmt, ASAPXMLOutputDirFmt)

    #     observed = tx(in_)

    #     # get file names in the observed directory
    #     observed_dir = str(observed)
    #     observed_files = sorted([
    #          f for f in os.listdir(observed_dir)
    #          if os.path.isfile(os.path.join(observed_dir, f))
    #      ])

    #     assert all(file.endswith('.xml') for file in observed_files)
