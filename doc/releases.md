<!--
Copyright 2018 IBM Corp.

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
# Release notes

## 0.2.3 (2018-04-25)

### Fixes

- ssh shell: prevent unicode decode errors while reading from socket

### Improvements

- zvm: handle logoffs forced by hypervisor during login process
- zvm: make sure terminal does not clear screen immediately
- hmc: allow boot with layer2 on and no mac address specified

## 0.2.2 (2018-03-21)

### Fixes

- kvm: avoid errors when multipath can't properly detect a disk

## 0.2.1 (2018-03-18)

### Fixes

- zvm: increase timeout while waiting for initrd file to be punched during netboot
- zvm: raise PermissionsError when login failed due to invalid credentials

## 0.2.0 (2018-03-13)

### New features

- Add support to manage z/VM guests ([#1](https://gitlab.com/tessia-project/tessia-baselib/issues/1)):
    - Boot (IPL) guest with CMS, or from a DASD or SCSI-FCP disk;
    - Boot (IPL) guest with Linux from a network URL (kernel/initrd);
    - Issue console commands and upload files to the guest.
- Add capability to set CPUs' type dynamically during LPAR activation ([#4](https://gitlab.com/tessia-project/tessia-baselib/issues/4))

### Improvements

- Provide detailed information from HMC API when an LPAR activation fails ([#5](https://gitlab.com/tessia-project/tessia-baselib/issues/5)).

## 0.1.0 (2018-01-12)

### New features

- Initial release
- Add support to manage LPARs in HMC classic mode
    - Boot (IPL) LPAR from a DASD or SCSI-FCP disk;
    - Boot (IPL) LPAR with Linux from a network URL (kernel/initrd) using an auxiliar disk.
- Add support to manage zKVM guests
    - Boot (IPL) guest from a DASD or SCSI-FCP disk;
    - Boot (IPL) guest with Linux from a network URL (kernel/initrd).
- Add support to perform actions on a Linux system (via SSH):
    - upload files
    - issues commands
