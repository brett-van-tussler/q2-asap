# ----------------------------------------------------------------------------
# Copyright (c) 2024, Nicole Sylvester.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from setuptools import find_packages, setup

import versioneer

description = ("A template QIIME 2 plugin.")

setup(
    name="q2-asap",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license="BSD-3-Clause",
    packages=find_packages(),
    author="Nicole Sylvester",
    author_email="nsylvester@tgen.org",
    description=description,
    url="https://example.com",
    entry_points={
        "qiime2.plugins": [
            "q2_asap="
            "q2_asap"
            ".plugin_setup:plugin"]
    },
    package_data={
        "q2_asap": ["citations.bib"],
        "q2_asap.tests": ["data/*"],
    },
    zip_safe=False,
)
