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


def outputCombiner(run_name: str,
                   xml_dir: ASAPXMLOutputDirFmt) -> ASAPXMLOutputDirFmt:

    out_file = run_name+"_analysis.xml"

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
                            (indent=' '*2).split('\n') if line.strip()]))
    output.close()

    return output_dir
