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

