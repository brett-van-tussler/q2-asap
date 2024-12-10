from pathlib import Path

import psutil
import qiime2
from parsl.addresses import address_by_hostname
from parsl.channels import LocalChannel
from parsl.config import Config
from parsl.executors import HighThroughputExecutor
from parsl.executors.threads import ThreadPoolExecutor
from parsl.launchers import SrunLauncher
from parsl.providers import LocalProvider
from qiime2 import Cache
from qiime2.plugins import ASAP
from qiime2.sdk.parallel_config import ParallelConfig

config = Config(
    executors=[
        ThreadPoolExecutor(label="default", max_threads=max(
            psutil.cpu_count() - 0, 1)),
        HighThroughputExecutor(label="htex", max_workers=max(
            psutil.cpu_count() - 1, 1), provider=LocalProvider()),
    ],
    # AdHoc Clusters should not be setup with scaling strategy.
    strategy=None,
)


def run_analyzeAmplicons_pipeline(sequences, ref_sequence, trimmer, aligner,
                                  aligner_index, run_name, config_fp, output_directory):
    cache = Cache()
    with cache:
        with ParallelConfig(parallel_config=config):
            futures = ASAP.analyzeAmplicons_pipeline.parallel(sequences, ref_sequence, trimmer, aligner,
                                                              aligner_index, run_name, config_fp)
            result = futures._result()
            if output_directory.exists():
                for f in output_directory.glob("*"):
                    if f:
                        f.unlink()
                # output_directory.rmdir()
            # print(type(result))
            result.output.save(output_directory)
