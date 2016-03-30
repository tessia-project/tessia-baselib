<!--
Copyright 2016, 2017 IBM Corp.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->
# Build system

The build system is based on python [setuptools]() and [pbr](http://docs.openstack.org/developer/pbr/). In order to build and install, one would simply do: `python3 setup.py`

The build files are organized as follows:

- **setup.py:** the entry point file which is executed to start the build process
- **setup.cfg:** configuration file in ini style format, it's used by pbr from within setup.py to determine how to build the package (see [pbr](http://docs.openstack.org/developer/pbr) for details)
- **requirements.txt:** contains all the packages required by the tool

