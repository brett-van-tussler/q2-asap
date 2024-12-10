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
from typing import Optional
from ._formats import ASAPXMLOutputDirFmt


def distinct_values(context, values):
    return list(set(values))

def list_non_html_files_recursively():
    non_html_files = []
    
    # Walk through the directory tree
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            if not file.endswith('.html'):
                full_path = os.path.join(root, file)
                # Calculate the relative path
                relative_path = os.path.relpath(full_path, os.getcwd())
                non_html_files.append(relative_path)
    
    return non_html_files

def formatOutput(output_dir: str, asap_xml_artifact: ASAPXMLOutputDirFmt, stylesheet: str, text: Optional[bool] = False) -> None:

    ns = ET.FunctionNamespace("http://pathogen.tgen.org/ASAP/functions")
    ns['distinct-values'] = distinct_values

    path_name = glob.glob(os.path.join(asap_xml_artifact.path, '*'))[0]

    dom = ET.parse(path_name)
    run_name = dom.getroot().attrib.get("run_name")
    xslt = ET.parse(stylesheet)
    transform = ET.XSLT(xslt)

    current_dir = os.getcwd()
    os.chdir(output_dir)
    os.mkdir(run_name)
    newdom = transform(dom)
    os.chdir(current_dir)
    

    if text:
        with open(os.path.join(output_dir, "index.html"), "w") as fh:
            fh.write(_html_template % repr(newdom))
    else:
        with open(os.path.join(output_dir, run_name + ".html"), "wb") as o:
           o.write(ET.tostring(newdom, pretty_print=True,
                                        xml_declaration=True,
                                        encoding='UTF-8'))
        with open(os.path.join(output_dir, "index.html"), "w") as fh:
            format_output_link = "<a href=\"{}.html\">formatted output</a>".format(run_name)
            os.chdir(output_dir)
            files = list_non_html_files_recursively()
            os.chdir(current_dir)
            file_links = ""
            for file in files:  
                file_links += "<br><a href=\"{0}\">{0}</a>".format(file)
            fh.write(_html_template % (format_output_link + file_links))


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
