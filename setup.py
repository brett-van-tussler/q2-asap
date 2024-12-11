# ----------------------------------------------------------------------------
# Copyright (c) 2024, Nicole Sylvester.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import os
from pathlib import Path

from setuptools import find_packages, setup

import versioneer

PKG_FOLDER = Path(os.path.abspath(os.path.dirname(__file__)))
with open(PKG_FOLDER / "README.md") as f:
    long_description = f.read()

description = ("An ASAP QIIME 2 plugin")
setup(
    name="q2-asap",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license="Academic and Research License",
    packages=find_packages(),
    author="Nicole Sylvester and Brett Van-Tassel",
    author_email="bvan-tassel@tgen.org",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TGenNorth/q2-asap",
    entry_points={
        "qiime2.plugins": [
            "q2_asap=q2_asap.plugin_setup:plugin",
        ]
    },
    dependencies=[
        "q2-nasp2-types@git+https://github.com/TGenNorth/q2-nasp2-types"
        "#egg=bamUpdates",
        "q2-aligners@git+https://github.com/TGenNorth/q2-aligners"
        "#egg=samUpdates",
        "q2-trimmers@git+https://github.com/TGenNorth/q2-trimmers",
        "pysam"
    ],
    include_package_data=True,
    package_data={
        "q2_asap": ["citations.bib"],
        "q2_asap.tests": ["data/*"],
    },
    zip_safe=False,
)
