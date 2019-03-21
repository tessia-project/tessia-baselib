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
# Tessia base library - tessia-baselib

[![pipeline status](https://gitlab.com/tessia-project/tessia-baselib/badges/master/build.svg)](https://gitlab.com/tessia-project/tessia-baselib/commits/master)
[![coverage report](https://gitlab.com/tessia-project/tessia-baselib/badges/master/coverage.svg?job=unittest)](https://gitlab.com/tessia-project/tessia-baselib/commits/master)

# What is it?

A python library which provides an abstraction layer to manage the communication with various types of hypervisors and guest systems on IBM Z in order to perform
actions like activate, deactivate, hotplug resources, and others.

Hypervisors supported:

- zHMC (classic and DPM modes)
- z/VM
- KVM for IBM Z

Guests supported:

- CMS (z/VM)
- Linux

# Quickstart

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

In order to be able to network boot LPARs on machines in classic mode, you need first to install an auxiliar live-image to a pre-allocated disk.
This process is explained at [Live image to enable HMC netboot](doc/users/live_image.md).

# What's new

Check the [Release notes](doc/releases.md).

# Documentation

See the [Users section](doc/index.md#users) for the API and usage examples.

# Contributing

If you are interested in contributing to the project, read [How to contribute (development process)](doc/developers/contributing.md).
Additional topics for developers are available at the [Developers section](doc/index.md#developers).

# Contact

You can join us on IRC at the `#tessia` channel on [OFTC](http://www.oftc.net)

# License

tessia and tessia-baselib are licensed under the [Apache 2.0 license](LICENSE).
