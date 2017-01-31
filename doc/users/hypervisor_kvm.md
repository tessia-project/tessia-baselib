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
## Rationale

This page describes the usage of the HypervisorKvm class and provides some use cases.

The definition of the parameters format is available in the jsonschema folder:

```bash
 tessia_baselib/common/params_validators/schemas/kvm
```

## Start a Guest

```python
from tessia_baselib.hypervisors.kvm.kvm import HypervisorKvm

hypervisor_name = "cpc3lp55"
hypervisor_hostname = "cpc3lp55.domain.com"
hypervisor_user = "root"
hypervisor_pwd = "somepasswd"
# Currently there are no parameters for instantiating a kvm hypervisor
hypervisor_params = None
kvm = HypervisorKvm(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
kvm.login()

# Here we define the parameters of the guest to be started.
guest_name = "kvm054"
guest_cpu = 2
guest_memory = 4096
# The format of the parameters are defined in the jsonschema.
iface = {
    "attributes":
    {
        "libvirt": '''<interface type="direct">
          <mac address="02:57:52:01:ff:01"/>
          <source dev="eth0" mode="bridge"/>
          <model type="virtio"/>
        <address type="ccw" cssid="0xfe" ssid="0x0" devno="0xf500"/>
        </interface>'''
    }
    "mac_address": "02:57:52:01:ff:01",
    "type": "MACVTAP",
}
disk_scsi = {
    "type": "FCP",
    "volume_id": "1024400000000000",
    "boot_device": True,
    "specs": {
        "multipath": True,
        "adapters": [{
            "devno": "0.0.1800",
            "wwpns": ['300607630503c1ae']
        }]
    }
}

disk_dasd = {
    "type": "DASD",
    "volume_id": "3961",
}

guest_parameters = {
    "storage_volumes" : [disk_scsi, disk_dasd ],
    "ifaces" : [iface]
}

kvm.start(guest_name, guest_cpu, guest_memory, guest_parameters)
kvm.logoff()
```

## Start a Guest using network boot

```python
from tessia_baselib.hypervisors.kvm.kvm import HypervisorKvm

hypervisor_name = "cpc3lp55"
hypervisor_hostname = "cpc3lp55.domain.com"
hypervisor_user = "root"
hypervisor_pwd = "somepasswd"
# Currently there are no parameters for instantiating a kvm hypervisor
hypervisor_params = None
kvm = HypervisorKvm(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
kvm.login()

# Here we define the parameters of the guest to be started.
guest_name = "kvm054"
guest_cpu = 2
guest_memory = 4096
iface = {
    "attributes":
    {
        "libvirt": '''<interface type="direct">
          <mac address="02:57:52:01:ff:01"/>
          <source dev="eth0" mode="bridge"/>
          <model type="virtio"/>
        <address type="ccw" cssid="0xfe" ssid="0x0" devno="0xf500"/>
        </interface>'''
    }
    "mac_address": "02:57:52:01:ff:01",
    "type": "MACVTAP",
}
disk_scsi = {
    "type": "FCP",
    "volume_id": "1024400000000000",
    "specs": {
        "multipath": True,
        "adapters": [{
            "devno": "0.0.1800",
            "wwpns": ['300607630503c1ae']
        }]
    }
}
disk_dasd = {
    "type": "DASD",
    "volume_id": "3961",
}
guest_parameters = {
    "storage_volumes" : [disk_scsi ],
    "ifaces" : [iface],
    "parameters": {
        "boot_method": "network",
        "boot_options": {
            "kernel_uri": "http://installserver.domain.com/redhat/RHEL7.2/DVD/images/kernel.img",
            "initrd_uri": "http://installserver.domain.com/redhat/RHEL7.2/DVD/images/initrd.img",
            "cmdline": "ro ramdisk_size=40000 inst.repo=http://installserver.domain.com/redhat/RHEL7.2/DVD/ ip=192.168.5.54::192.168.5.1:22:kvm054.domain.com:eth0:none nameserver=192.168.15.241 inst.sshd inst.vnc inst.vncpassword=123456 inst.ks=http://install_server/anaconda-ks.cfg"
        }
    }
}
kvm.start(guest_name, guest_cpu, guest_memory, guest_parameters)
kvm.logoff()
```

## Stop a Guest
```python
from tessia_baselib.hypervisors.kvm.kvm import HypervisorKvm

hypervisor_name = "cpc3lp55"
hypervisor_hostname = "cpc3lp55.domain.com"
hypervisor_user = "root"
hypervisor_pwd = "somepasswd"
guest_name = "kvm054"
# Currently there are no parameters for instantiating a kvm hypervisor
hypervisor_params = None
kvm = HypervisorKvm(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
kvm.login()
kvm.stop(guest_name)
kvm.logoff()
```

## Reboot a Guest
```python
from tessia_baselib.hypervisors.kvm.kvm import HypervisorKvm

hypervisor_name = "cpc3lp55"
hypervisor_hostname = "cpc3lp55.domain.com"
hypervisor_user = "root"
hypervisor_pwd = "somepasswd"
guest_name = "kvm054"
# Currently there are no parameters for instantiating a kvm hypervisor
hypervisor_params = None
kvm = HypervisorKvm(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
kvm.login()
kvm.reboot(guest_name)
kvm.logoff()
```
