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

This page describes the usage of the HypervisorHmc class and provides some use cases.

The definition of the parameters format is available in the jsonschema folder:

```bash
 tessia_baselib/common/params_validators/schemas/hmc
```

## Start a Guest

```python
from tessia_baselib.hypervisors.hmc import hmc

hypervisor_name = "hmcserver"
hypervisor_hostname = "hmcserver.domain.com"
hypervisor_user = "some_user"
hypervisor_pwd = "some_password"
# Currently there are no parameters for instantiating a hmc hypervisor
hypervisor_params = None
hmc = hmc.HypervisorHmc(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
hmc.login()

# Here we define the parameters of the guest to be started.
guest_name = "CP23LP12"
guest_cpu = 2
guest_memory = 4096
# The format of the parameters are defined in the jsonschema.
parameters = {
    "cpc_name": "CP23",
    "boot_params": {
        "boot_method": "dasd",
        "devicenr": "some_address"
    }
}

hmc.start(guest_name, guest_cpu, guest_memory, parameters)
hmc.logoff()
```

## Start a Guest using network boot

```python
from tessia_baselib.hypervisors.hmc import hmc

hypervisor_name = "hmcserver"
hypervisor_hostname = "hmcserver.domain.com"
hypervisor_user = "some_user"
hypervisor_pwd = "some_password"
# Currently there are no parameters for instantiating a hmc hypervisor
hypervisor_params = None
hmc = hmc.HypervisorHmc(hypervisor_name, hypervisor_hostname,
                        hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
hmc.login()

# Here we define the parameters of the guest to be started.
lpar_name = "CP23LP12"
lpar_cpu = 6
lpar_memory = 4096
lpar_parameters = {
"cpc_name": "CP23",
"boot_params": {
    "boot_method" : "network",
    "kernel_url": "http://installserver.domain.com/redhat/RHEL7.2/DVD/images/kernel.img",
    "initrd_url": "http://installserver.domain.com/redhat/RHEL7.2/DVD/images/initrd.img",
    "cmdline": "root=live:ftp://installserver.domain.com/redhat/RHEL7.2/DVD/images/install.img ro ramdisk_size=50000 cio_ignore=all, !condev rd.dasd=0.0.7e2c, readonly=0 rd.znet=qeth,0.0.f500,0.0.f501,0.0.f502,layer2=1 ip=192.168.5.12::192.168.5.1:255.255.255.0:cp23lp12:enccw0.0.f500:none nameserver=192.168.15.241 searchdns=domain.com inst.ks=http://installserver.domain.com/ks.file inst.vnc inst.vncpassword=",
    "mac": "02:23:12:00:76:00",
    "ip": "192.168.5.12",
    "mask": "255.255.255.0",
    "gateway": "192.168.5.1",
    "device": "f500,f501,f502"
    }
}

hmc.start(lpar_name, lpar_cpu, lpar_memory, lpar_parameters)
hmc.logoff()
```

## Stop a Guest
```python
from tessia_baselib.hypervisors.hmc import hmc

hypervisor_name = "hmcserver"
hypervisor_hostname = "hmcserver.domain.com"
hypervisor_user = "some_user"
hypervisor_pwd = "some_password"
# Currently there are no parameters for instantiating a hmc hypervisor
hypervisor_params = None
hmc = hmc.HypervisorHmc(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
hmc.login()

# Here we define the parameters of the guest to be started.
guest_name = "CP23LP12"
parameters = {
    "cpc_name": "CP23"
}

hmc.login()
hmc.stop(guest_name, parameters)
hmc.logoff()
```
## Reboot a Guest
```python
from tessia_baselib.hypervisors.hmc import hmc

hypervisor_name = "hmcserver"
hypervisor_hostname = "hmcserver.domain.com"
hypervisor_user = "some_user"
hypervisor_pwd = "some_password"
# Currently there are no parameters for instantiating a hmc hypervisor
hypervisor_params = None
hmc = hmc.HypervisorHmc(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
hmc.login()

# Here we define the parameters of the guest to be started.
guest_name = "CP23LP12"
parameters = {
    "cpc_name": "CP23"
}

hmc.login()
hmc.reboot(guest_name, parameters)
hmc.logoff()
```

