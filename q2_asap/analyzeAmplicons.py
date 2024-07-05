from q2_types.per_sample_sequences import CasavaOneEightSingleLanePerSampleDirFmt
from q2_nasp2_types.alignment import (BAMSortedAndIndexedDirFmt)
from q2_nasp2_types.index import BWAIndexDirFmt
from ._formats import ASAPXMLOutputDirFmt
from pathlib import Path
import shutil
import os
from typing import Optional
import tempfile
import subprocess
import re
import time

# function to check if a job with the given job ID is still running.
# returns true if the job is still running, false otherwise.
def is_job_running(job_id):
    try:
        result = subprocess.run(['squeue', '--job', str(job_id)], capture_output=True, text=True)
        return str(job_id) in result.stdout
    except Exception as e:
        print(f"Error checking job status: {e}")
        return False

# function to pause the script until the job with the given job ID is completed
# checks if the job is still running every check interval
def wait_for_job_completion(job_id, check_interval=10):
    while is_job_running(job_id):
        print(f"Job {job_id} is still running. Checking again in {check_interval} seconds...")
        time.sleep(check_interval)
    
    print(f"Job {job_id} has completed.")


# function that runs ASAP analyze amplicons using specified parameters. Sets up and executes command within a conda environment
# waits for job to complete, then organizes output files into designated output directories
def analyzeAmplicons(sequences: CasavaOneEightSingleLanePerSampleDirFmt, name: str=None, depth: int=10, breadth: float=0.9,
                        min_base_qual: int=20, consensus_proportion: float=0.8, fill_gaps: str="n", aligner: str="bwa", aligner_args: str='"-k 51 -L 20"'
          ) -> (
            BAMSortedAndIndexedDirFmt, 
          BWAIndexDirFmt,
          ASAPXMLOutputDirFmt):
    
    # create a temp directory to hold asap output
    #temp_dir = tempfile.mkdtemp()
    temp_dir = name

    # create output directories for each file type
    output_dir_bam = BAMSortedAndIndexedDirFmt()
    output_dir_bwa = BWAIndexDirFmt()
    output_dir_xml = ASAPXMLOutputDirFmt()

    # create analyzeAmplicons command
    command = f'analyzeAmplicons -r {sequences} -n {name} -o {temp_dir}/asap_output -d {depth} -b {breadth} -j /scratch/nsylvester/SARS2_variant_detection.json \
    --min_base_qual {min_base_qual} --consensus-proportion {consensus_proportion} --fill-gaps {fill_gaps} -a {aligner} --aligner-args {aligner_args}'

    # combine conda environment and command TODO: fix conda environment
    shell_script= f"""
    conda run -p /home/dlemmer/.conda/envs/asap {command}
    """

    # call asap command
    result = subprocess.run(['bash', '-c', shell_script], capture_output=True, text=True)
    # capture stdout
    output = result.stdout

    # find the job ID in the stdout
    job_id_match = re.findall('(?<=final job id is: )\d+', output)[0]

    # wait for the job to complete
    wait_for_job_completion(job_id_match)
    asap_output_dir = os.path.join(temp_dir, "asap_output")
    
    # move output into artifact directories by looping through files, getting the file path
    # and moving the file to correct directory 
    for file_name in os.listdir(asap_output_dir):
        file_path = os.path.join(asap_output_dir, file_name)
        if re.search(r'\.(amb|ann|bwt|pac|sa|fasta)$', file_name):
            shutil.move(file_path, Path(output_dir_bwa.path) / file_name)
        elif re.search(r'\.xml$', file_name):
                shutil.move(file_path, Path(output_dir_xml.path) / file_name)

    # move bam files
    for file_name in os.listdir(os.path.join(asap_output_dir, "bwamem")):
        file_path = os.path.join(asap_output_dir, "bwamem", file_name)
        shutil.move(file_path, Path(output_dir_bam.path) / file_name)

    #  remove temp directory
    # shutil.rmtree(temp_dir)

    return (output_dir_bam, output_dir_bwa, output_dir_xml) 