#!/usr/bin/env python3
# encoding: utf-8
'''
asap.formatOutput -- Apply an XSLT transformation on the XML output
to generate a more user-friendly output

asap.formatOutput

@author:     Darrin Lemmer

@copyright:  2015,2019 TGen North. All rights reserved.

@license:    ACADEMIC AND RESEARCH LICENSE -- see ../LICENSE

@contact:    dlemmer@tgen.org
'''
import os
import lxml.etree as ET
import glob
from ._formats import ASAPXMLOutputDirFmt


def distinct_values(context, values):
    return list(set(values))

# TODO: create a new dir format for single xml, create a transformer for it, maybe get rid of output combiner
def formatOutput(output_dir: str, asap_xml_artifact: ASAPXMLOutputDirFmt, stylesheet: str, text: bool) -> None:

    # TODO: figure out what this code does?
    ns = ET.FunctionNamespace("http://pathogen.tgen.org/ASAP/functions")
    ns['distinct-values'] = distinct_values

    # parser = ET.XMLParser(huge_tree=True)
    # dom = ET.parse(xml_file, parser=parser)
    path_name = glob.glob(os.path.join(asap_xml_artifact.path, '*'))[0]

    dom = ET.parse(path_name)
    xslt = ET.parse(stylesheet)
    transform = ET.XSLT(xslt)
    newdom = transform(dom)

    if text:
        with open(os.path.join(output_dir, "index.html"), "w") as fh:
            fh.write(_html_template % repr(newdom))
    else:
        # format_output_dir = os.path.join(output_dir, "formatted_output")
        # os.mkdir(format_output_dir)
        # print(os.path.join(format_output_dir, "toplevel.html"))
        with open(output_dir + "test.html", "wb") as o:
           print(ET.tostring(newdom, pretty_print=True,
                                        xml_declaration=True,
                                        encoding='UTF-8'))
           o.write(ET.tostring(newdom, pretty_print=True,
                                        xml_declaration=True,
                                        encoding='UTF-8'))
        print(os.path.join(output_dir, "index.html"))
        with open(os.path.join(output_dir, "index.html"), "w") as fh:
            fh.write(_html_template % repr("<a href=\""+ output_dir + "\">formatted output</a>"))

_html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alignment summary</title>
    <style>
        body {
            padding: 20px;
        }
        p.alignment {
            font-family: 'Courier New', Courier, monospace;
        }
    </style>
</head>
<body>
    <pre>
%s
    </pre>
</body>
</html>
"""