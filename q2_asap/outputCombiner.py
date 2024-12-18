'''
asap.outputCombiner -- Combine multiple sample-level XML output files
into one run-level XML output

asap.outputCombiner

@author:     Darrin Lemmer

@copyright:  2015,2019 TGen North. All rights reserved.

@license:    ACADEMIC AND RESEARCH LICENSE -- see ../LICENSE

@contact:    dlemmer@tgen.org
'''
import os
from xml.etree import ElementTree
from xml.dom import minidom
from ._formats import ASAPXMLOutputDirFmt
from pathlib import Path
from qiime2.util import duplicate
from q2_nasp2_types.alignment import BAMSortedAndIndexedDirFmt
from q2_types.per_sample_sequences import (
    CasavaOneEightSingleLanePerSampleDirFmt)


def outputCombiner(run_name: str,
                   xml_dir: ASAPXMLOutputDirFmt) -> ASAPXMLOutputDirFmt:

    out_file = run_name + "_analysis.xml"

    # combine xmls
    root_node = ElementTree.Element("analysis", {'run_name': run_name})
    sorted_files = sorted(os.listdir(xml_dir.path))

    for file in sorted_files:
        sample_tree = ElementTree.parse(os.path.join(xml_dir.path, file))
        sample_node = sample_tree.getroot()
        root_node.append(sample_node)

    combined_xmls = minidom.parseString(ElementTree.tostring(root_node))

    output_dir = ASAPXMLOutputDirFmt()
    output = open(Path(output_dir.path) / Path(out_file), 'w')
    output.write('\n'.join([line for line in combined_xmls.toprettyxml
                            (indent=' ' * 2).split('\n') if line.strip()]))
    output.close()

    return output_dir
# TODO: clean up between test runs(test is trying to duplicate same file)


def xmlCollectionCombiner(
        xml_collection:
        ASAPXMLOutputDirFmt
) -> ASAPXMLOutputDirFmt:

    # print(xml_collection)

    xml_output_artifact = ASAPXMLOutputDirFmt()

    for key, artifact in xml_collection.items():
        artifact_dp = artifact.path
        # Move all files from value_fp to target_dir
        for filename in os.listdir(artifact_dp):
            source_file = os.path.join(artifact_dp, filename)
            target_file = os.path.join(xml_output_artifact.path, filename)

            duplicate(source_file, target_file)

    return xml_output_artifact


def alignedCollectionCombiner(
        aligned_collection:
        BAMSortedAndIndexedDirFmt
) -> BAMSortedAndIndexedDirFmt:
    # TODO: when printing collection, we get
    # an error 'print(aligned_collection)'
    # send traceback code

    aligned_output_artifact = BAMSortedAndIndexedDirFmt()

    for key, artifact in aligned_collection.items():
        artifact_dp = artifact.path
        # Move all files from value_fp to target_dir
        for filename in os.listdir(artifact_dp):
            source_file = os.path.join(artifact_dp, filename)
            target_file = os.path.join(aligned_output_artifact.path, filename)

            duplicate(source_file, target_file)

    return aligned_output_artifact

# TODO: confirm this works for single and paired-end


def trimmedCollectionCombiner(
        trimmed_collection:
        CasavaOneEightSingleLanePerSampleDirFmt
) -> CasavaOneEightSingleLanePerSampleDirFmt:

    # with open("trimmed_type_pipeline.txt", "w") as fh:
    #     fh.write(" ".join(
    #       [str(type(i)) for i in trimmed_collection.values()]))
    #     fh.write("\n")
    #     fh.write(str(type(trimmed_collection)))
    # print(type(trimmed_collection))
    # print(trimmed_collection)

    trimmed_output_artifact = CasavaOneEightSingleLanePerSampleDirFmt()

    for key, artifact in trimmed_collection.items():
        print("Artifact")
        # print(artifact.view(CasavaOneEightSingleLanePerSampleDirFmt).path)
        # artifact_dp = artifact.view(
        # CasavaOneEightSingleLanePerSampleDirFmt).path
        # # Move all files from value_fp to target_dir
        # for filename in os.listdir(artifact_dp):
        print(artifact)
        for filename in os.listdir(artifact.path):
            file_path = Path(artifact.path) / Path(filename)
            target_file = os.path.join(trimmed_output_artifact.path, filename)

            duplicate(file_path, target_file)

    return trimmed_output_artifact
