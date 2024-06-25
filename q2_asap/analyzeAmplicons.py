from q2_types.per_sample_sequences import CasavaOneEightSingleLanePerSampleDirFmt
from q2_types.per_sample_sequences import (BAMDirFmt)
from q2_nasp2_types.index import BWAIndexDirFmt
from ._formats import ASAPXMLOutputDirFmt, ASAPHTMLOutputDirFmt
from pathlib import Path
import shutil
import os

def analyzeAmplicons(sequences: CasavaOneEightSingleLanePerSampleDirFmt,
          ) -> (
            BAMDirFmt, 
          BWAIndexDirFmt,
          ASAPXMLOutputDirFmt, 
          ASAPHTMLOutputDirFmt ):
    
    print(sequences.manifest)
    sample = sequences.manifest.iloc[0]

    # create output directory
    output_dir_bam = BAMDirFmt()
    output_dir_bwa = BWAIndexDirFmt()
    output_dir_xml = ASAPXMLOutputDirFmt()
    output_dir_html = ASAPHTMLOutputDirFmt()


    command = 'analyzeAmplicons -r /TGenNextGen/TGN-"+ run_id + "/*SARS-CoV2 -n Tiled_" + run_id + " -o Tiled_" + run_id + "\
     -d 10 -b 0.9 -j /labs/COVIDseq/ASAP_results/SARS2_variant_detection.json --min_base_qual 20 --consensus-proportion 0.8 --fill-gaps n -a bwa --aligner-args "-k 51 -L 20"'

    # call asap command
    #result = subprocess.run(, check=True, capture_output=True, text=True)
    print(command)
    print(Path(output_dir_html.path) / 'test.html')
    with open(Path(output_dir_html.path) / 'test.html', 'w') as o:
        o.write("<html><div><p>HAJKS</p></div></html>")

    destination_path= Path(output_dir_bam.path) / 'test.bam'
    source_path = '/scratch/nsylvester/SARS2_TG1379649_S280-bwamem.bam'
    shutil.copyfile(source_path, destination_path)

    destination_path= Path(output_dir_bwa.path) 
    source_path = '/scratch/nsylvester/bwa_index_example/*'
    os.system(f'cp {source_path} {destination_path}')

    print(Path(output_dir_xml.path) / 'test.xml')
    with open(Path(output_dir_xml.path) / 'test.xml', 'w') as o:
        o.write("<html><div><p>HAJKS</p></div></html>")

    return (output_dir_bam, output_dir_bwa, output_dir_xml, output_dir_html) 