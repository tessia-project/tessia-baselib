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
    # Currently there is not parameters for instantiating a kvm hypervisor
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
    }
    disk_scsi = {
        "disk_type": "SCSI",
        "volume_id": "0x1024400000000000",
        "boot_device": True,
        "specs": {
            "multipath": True,
            "paths": [{
                "devno": "0.0.1800",
                "wwpns": ['0x300607630503c1ae']
            }]
        }
    }

    disk_dasd = {
        "disk_type": "DASD",
        "volume_id": "3961",
    }

    guest_parameters = {
        "storage_volumes" : [disk_scsi, disk_dasd ],
        "ifaces" : [iface]
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
    # Currently there is not parameters for instantiating a kvm hypervisor
    hypervisor_params = None
    kvm = HypervisorKvm(hypervisor_name, hypervisor_hostname,
                        hypervisor_user, hypervisor_pwd, hypervisor_params)

    # We must be logged in before submitting any command.
    kvm.login()
	kvm.stop()
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
    # Currently there is not parameters for instantiating a kvm hypervisor
    hypervisor_params = None
    kvm = HypervisorKvm(hypervisor_name, hypervisor_hostname,
                        hypervisor_user, hypervisor_pwd, hypervisor_params)

    # We must be logged in before submitting any command.
    kvm.login()
	kvm.reboot()
	kvm.logoff()
```
