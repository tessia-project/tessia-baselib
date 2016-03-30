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

#
# IMPORTS
#
from setuptools import Command
from setuptools import setup

import os
import subprocess

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class bdist_mkdocs(Command):
    """Implement the command to build the project's documentation
    """

    # Brief (40-50 characters) description of the command
    description = "build project's documentation using mkdocs"

    # List of option tuples: long name, short name (None if no short
    # name), and help string.
    user_options = [
        (
            'input-dir',
            'i',
            'Folder containing mkdocs.yml file (defaults to doc/)',
        ),
        (
            'output-dir',
            'o',
            'Folder to store generated files (defaults to html/)'
        ),
    ]

    def initialize_options(self):
        self.cur_dir = os.path.dirname(os.path.abspath(__file__))
        self.input_dir = None
        self.output_dir = None
    # initialize_options()

    def finalize_options(self):
        """Validate options before perform the actual action

        Returns:
            None

        Raises:
            Exception: if input dir does not exist
        """
        # input dir not specified: default to doc in current folder
        if self.input_dir is None:
            self.input_dir = '{}/doc'.format(self.cur_dir)
        # use path defined by user, in case of an absolute path join will take
        # care of using it
        else:
            self.input_dir = os.path.join(self.cur_dir, self.input_dir)

        # output dir not specified: default to current folder
        if self.output_dir is None:
            self.output_dir = self.cur_dir
        # use path defined by user, in case of an absolute path join will take
        # care of using it
        else:
            self.output_dir = os.path.join(self.cur_dir, self.output_dir)
        # add html suffix to the path
        self.output_dir = os.path.join(self.output_dir, 'html')

        # make sure source path exists
        if not os.path.exists(self.input_dir):
            raise Exception(
                'Input directory {} does not exist'.format(self.input_dir))

    # finalize_options()

    def run(self):
        """Execute mkdocs in order to build the documentation in html format

        Returns:
            None

        Raises:
            RuntimeError: in case mkdocs command fails
        """
        cmd = 'cd {} && mkdocs build -c -d {}'.format(self.input_dir,
                                                         self.output_dir)
        print(cmd)
        subprocess.call(cmd, shell=True)
    # run()

# bdist_mkdocs

# entry point to setup actions
setup(
    setup_requires=['setuptools>=17.1.1'],
    install_requires=open('requirements.txt', 'r').read(),
    cmdclass={'bdist_mkdocs': bdist_mkdocs},
)
