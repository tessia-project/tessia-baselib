#!/usr/bin/python3
# Copyright 2016, 2017 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Entry point to setuptools, used for installing/packaging the library
"""

#
# IMPORTS
#
from fnmatch import fnmatch
from setuptools import find_packages, setup

import os
import re
import sys

#
# CONSTANTS AND DEFINITIONS
#
# metadata variables
AUTHOR = 'IBM'
CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: System :: Hardware :: Mainframes',
    'Topic :: System :: Installation/Setup',
    'Topic :: System :: Systems Administration',
]
DESCRIPTION = (
    'Abstraction layer for communication with IBM Z hypervisors/guests')
LICENSE = 'Apache 2.0'
with open('README.md', 'r') as desc_fd:
    LONG_DESCRIPTION = desc_fd.read()
LONG_DESC_TYPE = 'text/markdown'
KEYWORDS = 'communication ibmz guest hypervisor'
NAME = 'tessia-baselib'
URL = 'https://gitlab.com/tessia-project'

#
# CODE
#
def _find_data_files(dir_name, pkg_data=True):
    """
    List all (pkg or non pkg) data files

    Args:
        dir_name (str): directory to perform search
        pkg_data (bool): whether the files are package data

    Returns:
        list: data files
    """
    data_files = []
    for entry in os.walk(dir_name):
        for filename in entry[2]:
            # (non pkg) data file: use complete path
            if not pkg_data:
                data_files.append(os.path.join(entry[0], filename))
                continue

            # python file: skip it
            if fnmatch(filename, '*.py?') or filename.endswith('.py'):
                continue
            data_files.append(
                os.path.join(entry[0].split('/', 1)[1], filename))

    return data_files
# _find_data_files()

def _find_requirements():
    """
    List all installation requirements

    Returns:
        list: installation requirements
    """
    with open('requirements.txt', 'r') as req_fd:
        lines = req_fd.readlines()
    req_list = []
    for line in lines:
        # comment or empty line: skip it
        if not line.strip() or re.match('^ *#', line):
            continue

        # url format: need to extract requirement name
        if '://' in line:
            egg_index = line.find('#egg=')
            # no egg specifier present: requirement cannot be converted to
            # setuptools format
            if egg_index == -1:
                print('warning: excluding requirement {}'.format(line),
                      file=sys.stderr)
                continue
            line = line[egg_index+5:]
        req_list.append(line)

    return req_list
# _find_requirements()

# entry point to setup actions
setup(
    # metadata information
    author=AUTHOR,
    classifiers=CLASSIFIERS,
    description=DESCRIPTION,
    keywords=KEYWORDS,
    license=LICENSE,
    long_description=LONG_DESCRIPTION,
    long_description_content_type=LONG_DESC_TYPE,
    name=NAME,
    # installation information
    data_files=[('etc/tessia', _find_data_files('etc', False))],
    install_requires=_find_requirements(),
    package_data={'': _find_data_files('tessia')},
    packages=find_packages(exclude=['tests', 'tests.*']),
    setup_requires=['setuptools>=30.3.0'],
    url=URL,
    zip_safe=False,
)
