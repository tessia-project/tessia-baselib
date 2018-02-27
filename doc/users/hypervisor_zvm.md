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
## Rationale

This page describes the usage of the HypervisorZvm class and provides some use cases.

The definition of the parameters format is available in the jsonschema folder:

```bash
 tessia/baselib/common/params_validators/schemas/zvm
```

## Start a guest using a disk

```python
from tessia.baselib.hypervisors.zvm.zvm import HypervisorZvm

hypervisor_name = "vmhost"
hypervisor_hostname = "vmhost.domain.com"
username = "vmguest01"
passwd = "vmpasswd"
# as parameters one can specify {'byuser': 'vmadmin'}
parameters = None
zvm = HypervisorZvm(hypervisor_name, hypervisor_hostname,
                    username, passwd, parameters)

# we must be logged in before submitting any command.
zvm.login()

# here we define the parameters of the guest to be started
guest_cpu = 2
# memory in megabytes
guest_memory = 2048
# on z/VM the guest name must match the username
guest_name = username
# The format of the parameters can be viewed in the jsonschema
iface = {
    "type": "osa",
    "id": "f5f0,f5f1,f5f2"
}
# FCP disks are also supported
disk_dasd = {
    "type": "dasd",
    "devno": "1c5d",
    "boot_device": True
}

guest_parameters = {
    "boot_method": "disk",
    "storage_volumes" : [disk_dasd],
    "ifaces" : [iface]
}

# ipl the guest after attaching the specified devices
zvm.start(guest_name, guest_cpu, guest_memory, guest_parameters)

# The method name 'logoff' comes from the base class which defines the common
# interface, therefore it means 'close the connection to the hypervisor'.
# On z/VM this method in fact executes a disconnect to keep the guest running.
# For a 'real' z/VM logoff where the guest is stopped, use 'zvm.stop()'
zvm.logoff()
```

## Start a guest via network

```python
from tessia.baselib.hypervisors.zvm.zvm import HypervisorZvm

hypervisor_name = "vmhost"
hypervisor_hostname = "vmhost.domain.com"
username = "vmguest01"
passwd = "vmpasswd"
# as parameters one can specify {'byuser': 'vmadmin'}
parameters = None
zvm = HypervisorZvm(hypervisor_name, hypervisor_hostname,
                    guest_user, guest_pwd, parameters)

# we must be logged in before submitting any command.
zvm.login()

# here we define the parameters of the guest to be started
guest_cpu = 3
# memory in megabytes
guest_memory = 2048
# on z/VM the guest name must match the username
guest_name = username
# The format of the parameters can be viewed in the jsonschema
iface = {
    "type": "osa",
    "id": "f5f0,f5f1,f5f2"
}
disk_dasd = {
    "type": "dasd",
    "devno": "1c5d",
}

guest_parameters = {
    "boot_method": "network",
    "storage_volumes" : [disk_dasd],
    "ifaces" : [iface],
    "netboot": {
        "cmdline": "ro ramdisk_size=50000 cio_ignore=all,!condev zfcp.allow_lun_scan=0 rd.znet=qeth,0.0.f5f0,0.0.f5f1,0.0.f5f2,layer2=0 rd.dasd=0.0.1c5d rd.dasd=0.0.1c5f inst.repo=http://installserver.domain.com/RHEL7.2/DVD ip=192.168.1.32::192.168.1.1:24:vmguest01:enccw0.0.f5f0:none nameserver=192.168.1.241 inst.sshd inst.vnc inst.vncpassword=vmpasswd inst.ks=http://installserver.domain.com/vmguest01.ks",
        "kernel_uri": "http://installserver.domain.com/redhat/RHEL7.2/DVD/images/kernel.img",
        "initrd_uri": "http://installserver.domain.com/redhat/RHEL7.2/DVD/images/initrd.img",
    }
}

# attach devices, download kernel/initrd, punch files to reader, ipl it
zvm.start(guest_name, guest_cpu, guest_memory, guest_parameters)

# The method name 'logoff' comes from the base class which defines the common
# interface, therefore it means 'close the connection to the hypervisor'.
# On z/VM this method in fact executes a disconnect to keep the guest running.
# For a 'real' z/VM logoff where the guest is stopped, use 'zvm.stop()'
zvm.logoff()
```

## Stop a guest

```python
hypervisor_name = "vmhost"
hypervisor_hostname = "vmhost.domain.com"
username = "vmguest01"
passwd = "vmpasswd"
# as parameters one can specify {'byuser': 'vmadmin'}
parameters = None
zvm = HypervisorZvm(hypervisor_name, hypervisor_hostname,
                    username, passwd, parameters)

# we must be logged in before submitting any command.
zvm.login()

# performs a z/VM 'real logoff' to stop the guest
zvm.stop(guest_name)
```
