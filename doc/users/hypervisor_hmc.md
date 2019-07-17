<!--
Copyright 2016, 2017, 2019 IBM Corp.

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
# Rationale

This page describes the usage of the HypervisorHmc class and provides some use cases.

The definition of the parameters format is available in the jsonschema folder:

```bash
 tessia/baselib/common/params_validators/schemas/hmc
```

## Start an LPAR (classic mode)

```python
from tessia.baselib.hypervisors.hmc import hmc

hypervisor_name = "CP23" # this is the CEC/CPC hosting the target LPAR
hypervisor_hostname = "hmc.domain.com" # URL where HMC API is running
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
# dasd example
parameters = {
    "boot_params": {
        "boot_method": "dasd",
        "devicenr": "9999"
    }
}

# for scsi, uncomment below
#parameters = {
#    "boot_params": {
#        "boot_method": "scsi",
#        "devicenr": "9999",
#        "lun": "123456789",
#        "wwpn": "500000000",
#    }
#}

hmc.start(guest_name, guest_cpu, guest_memory, parameters)
hmc.logoff()
```

## Start an LPAR (classic mode) using simulated network boot (live image)

```python
from tessia.baselib.hypervisors.hmc import hmc

hypervisor_name = "CP23" # this is the CEC/CPC hosting the target LPAR
hypervisor_hostname = "hmc.domain.com" # URL where HMC API is running
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
    "boot_params": {
        "boot_method" : "dasd",
        'devicenr': '6500', # this is the pre-allocated disk with the live image
        'netsetup': {
            "mac": None,
            "ip": "192.168.5.12",
            "mask": 24,
            "gateway": "192.168.5.1",
            "type": "osa", # also accepts 'pci'
            "device": "f500,f501,f502" # enter the function id when type is 'pci'
            "password": "rootpwd",
            "dns": ['192.168.15.241'],
        },
        'netboot': {
            "cmdline": "ro ramdisk_size=50000 cio_ignore=all,!condev rd.dasd=0.0.7e2c rd.znet=qeth,0.0.f500,0.0.f501,0.0.f502,layer2=1 ip=192.168.5.12::192.168.5.1:255.255.255.0:cp23lp12:enccw0.0.f500:none nameserver=192.168.15.241 nameserver=192.168.5.1 inst.sshd inst.ks=http://installserver.domain.com/ks.file inst.vnc inst.vncpassword=somepwd",
            "kernel_url": "http://repo.domain.com/redhat/RHEL7.2/DVD/images/kernel.img",
            "initrd_url": "http://repo.domain.com/redhat/RHEL7.2/DVD/images/initrd.img",
        }
    }
}

hmc.start(lpar_name, lpar_cpu, lpar_memory, lpar_parameters)
hmc.logoff()
```

## Start a partition (DPM mode)

**Important:** note that the library currently supports starting partitions only on machines where the firmware
provides the `dpm-storage-management` feature.

```python
from tessia.baselib.hypervisors.hmc import hmc

hypervisor_name = "CP23" # this is the CEC/CPC hosting the target LPAR
hypervisor_hostname = "hmc.domain.com" # URL where HMC API is running
hypervisor_user = "some_user"
hypervisor_pwd = "some_password"
# Currently there are no parameters for instantiating a hmc hypervisor
hypervisor_params = None
hmc = hmc.HypervisorHmc(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
hmc.login()

# Here we define the parameters of the guest to be started.
guest_name = "cp23lp12"
guest_cpu = 2
guest_memory = 4096

# The format of the parameters are defined in the jsonschema.
# scsi example
parameters = {
    "boot_params": {
        "boot_method": "scsi",
        "uuid": "1001036305ddc1ae000000000000820a"
    }
}

# for dasd, uncomment below
#parameters = {
#    "boot_params": {
#         "boot_method": "dasd",
#         "devicenr": "9999",
#    }
#}

# or alternatively, to boot directly from the network uncomment the lines below
#parameters = {
#    "boot_params": {
#        "boot_method": "ftp",
#        "insfile": "user:password@my_ftp_server.example.com/dir/image.ins"
#    }
#}

hmc.start(guest_name, guest_cpu, guest_memory, parameters)
hmc.logoff()
```

## Start a partition (DPM mode) using simulated network boot (live image)

**Important:** note that the library currently supports starting partitions from scsi disks
and on machines where the firmware provides the `dpm-storage-management` feature.

```python
from tessia.baselib.hypervisors.hmc import hmc

hypervisor_name = "CP23" # this is the CEC/CPC hosting the target LPAR
hypervisor_hostname = "hmc.domain.com" # URL where HMC API is running
hypervisor_user = "some_user"
hypervisor_pwd = "some_password"
# Currently there are no parameters for instantiating a hmc hypervisor
hypervisor_params = None
hmc = hmc.HypervisorHmc(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
hmc.login()

# Here we define the parameters of the guest to be started.
guest_name = "cp23lp12"
guest_cpu = 2
guest_memory = 4096
# The format of the parameters are defined in the jsonschema.
parameters = {
    "boot_params": {
        "boot_method": "scsi",
        "uuid": "1001036305ddc1ae000000000000820a"
        'netsetup': {
            "mac": None,
            "ip": "192.168.5.12",
            "mask": 24,
            "gateway": "192.168.5.1",
            "type": "osa", # also accepts 'pci'
            "device": "f500,f501,f502" # enter the function id when type is 'pci'
            "password": "rootpwd",
            "dns": ['192.168.15.241'],
        },
        'netboot': {
            "cmdline": "ro ramdisk_size=50000 cio_ignore=all,!condev rd.dasd=0.0.7e2c rd.znet=qeth,0.0.f500,0.0.f501,0.0.f502,layer2=1 ip=192.168.5.12::192.168.5.1:255.255.255.0:cp23lp12:enccw0.0.f500:none nameserver=192.168.15.241 nameserver=192.168.5.1 inst.sshd inst.ks=http://installserver.domain.com/ks.file inst.vnc inst.vncpassword=somepwd",
            "kernel_url": "http://repo.domain.com/redhat/RHEL7.2/DVD/images/kernel.img",
            "initrd_url": "http://repo.domain.com/redhat/RHEL7.2/DVD/images/initrd.img",
        }
    }
}

hmc.start(guest_name, guest_cpu, guest_memory, parameters)
hmc.logoff()
```

## Stop an LPAR or partition (classic and DPM mode)

```python
from tessia.baselib.hypervisors.hmc import hmc

hypervisor_name = "CP23" # this is the CEC/CPC hosting the target LPAR
hypervisor_hostname = "hmc.domain.com" # URL where HMC API is running
hypervisor_user = "some_user"
hypervisor_pwd = "some_password"
# Currently there are no parameters for instantiating a hmc hypervisor
hypervisor_params = None
hmc = hmc.HypervisorHmc(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
hmc.login()

# Here we define the parameters of the guest to be stopped.
guest_name = "CP23LP12"
parameters = {} # no special parameters are used currently

hmc.stop(guest_name, parameters)
hmc.logoff()
```

## Reboot an LPAR or partition (classic and DPM mode)

```python
from tessia.baselib.hypervisors.hmc import hmc

hypervisor_name = "CP23" # this is the CEC/CPC hosting the target LPAR
hypervisor_hostname = "hmc.domain.com" # URL where HMC API is running
hypervisor_user = "some_user"
hypervisor_pwd = "some_password"
# Currently there are no parameters for instantiating a hmc hypervisor
hypervisor_params = None
hmc = hmc.HypervisorHmc(hypervisor_name, hypervisor_hostname,
                    hypervisor_user, hypervisor_pwd, hypervisor_params)

# We must be logged in before submitting any command.
hmc.login()

# Here we define the parameters of the guest to be rebooted.
guest_name = "CP23LP12"
parameters = {} # no special parameters are used currently

hmc.reboot(guest_name, parameters)
hmc.logoff()
```
