import subprocess
from pathlib import Path
import json
import xmltodict
from q2_asap._formats import ASAPJSONOutputDirFmt, ASAPXMLOutputDirFmt
from .plugin_setup import plugin

@plugin.register_transformer
def _1(data: ASAPXMLOutputDirFmt) -> ASAPJSONOutputDirFmt:
    json_output = ASAPJSONOutputDirFmt()

    xml_files = data.path.glob("*.xml")
    for xml in xml_files:
        json_output_path = Path(json_output.path).joinpath(xml.name.replace("xml", "json"))
        with open(xml, 'r') as xml_file:
            xml_content = xml_file.read()

        # Convert XML to dictionary
        xml_dict = xmltodict.parse(xml_content)

        # Convert dictionary to JSON
        json_content = json.dumps(xml_dict, indent=4)

        # Save the JSON to a file
        with open(json_output_path, 'w') as json_file:
            json_file.write(json_content)

    return json_output

@plugin.register_transformer
def _2(data: ASAPJSONOutputDirFmt) -> ASAPXMLOutputDirFmt:
    xml_output = ASAPXMLOutputDirFmt()

    json_files = data.path.glob("*.json")
    for json in json_files:
        xml_output_path = Path(xml_output.path).joinpath(json.name.replace("json", "xml"))
        with open(json, 'r') as json_file:
            json_content = json.load(json_file)

        # Convert JSON to dictionary
        xml_content = xmltodict.unparse(json_content, pretty=True)

        # Save the XML to a file
        with open(xml_output_path, 'w') as xml_file:
            xml_file.write(xml_content)

    return xml_output

