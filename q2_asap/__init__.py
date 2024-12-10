# flake8: noqa
# ----------------------------------------------------------------------------
# Copyright (c) 2024, Nicole Sylvester.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from ._formats import (ASAPXMLOutputDirFmt, ASAPXMLFormat, ASAPHTMLOutputDirFmt,
                       ASAPHTMLFormat, ASAPJSONOutputDirFmt, ASAPJSONFormat)
from . import _version
import importlib
from ._version import get_versions

__version__ = get_versions()["version"]
del get_versions

__version__ = _version.get_versions()['version']


__all__ = [
    'ASAPXMLOutputDirFmt', 'ASAPXMLFormat',
    'ASAPHTMLOutputDirFmt', 'ASAPHTMLFormat',
    'ASAPJSONOutputDirFmt', 'ASAPJSONFormat',
]

importlib.import_module('q2_asap._transformers')
