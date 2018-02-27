<!--
Copyright 2017 IBM Corp.

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
# How to install

You will need python >= 3.5, begin by installing the necessary dependencies:

```
# the dependencies might vary depending on your distro
$ apt-get update && apt-get install \
    python3-pip \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    s3270
$ pip3 install -U pip setuptools
```

Install the library using pip:

```
$ git clone https://gitlab.com/tessia-project/tessia-baselib.git
$ cd tessia-baselib && pip3 install -U .
```

You can test the installation with:

```
$ python3 -i -c "from tessia.baselib.hypervisors import Hypervisor; from tessia.baselib.guests import Guest"
```

In order to be able to network boot LPARs with HMC in classic mode, you need first to install an auxiliar live-image to a pre-allocated disk.
This process is explained at [Live image to enable HMC netboot](live_image.md).
