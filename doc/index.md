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
![Logo](img/logo_128.png)

# Tessia base library - tessia-baselib

# What is it?

A python library which provides an abstraction layer to manage the communication with various types of hypervisors and guest systems on IBM Z in order to perform
actions like activate, deactivate, hotplug resources, and others.
This library is part of the tessia solution but can also be used standalone by developers/system administrators seeking for a python library to automate their IBM Z environments.

Hypervisors supported:

- zHMC (classic and DPM modes)
- z/VM
- KVM for IBM Z

Guests supported:

- CMS (z/VM)
- Linux

# What's new

Check the [Release notes](releases.md).

# Users

- Installation
    - [How to install](users/install.md)
    - [Live image to enable HMC netboot](users/live_image.md)
- API documentation
    - [Hypervisors API](users/api_hypervisors.md)
    - [Guests API](users/api_guests.md)
- Usage examples
    - [Hypervisor HMC](users/hypervisor_hmc.md)
    - [Hypervisor z/VM](users/hypervisor_zvm.md)
    - [Hypervisor KVM](users/hypervisor_kvm.md)
- Misc
    - Library's [versioning scheme](users/versioning.md)

# Developers

- [How to contribute (development process)](developers/contributing.md)
- [How to setup a development environment](developers/dev_env.md)
- [Coding guidelines](developers/coding_guidelines.md)
- [Tests](developers/tests.md)
- [Working with documentation](developers/documentation.md)
- [Validation of parameters with json schemas](developers/params_validation.md)
