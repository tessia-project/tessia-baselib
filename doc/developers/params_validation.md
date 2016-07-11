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
# Rationale

This document describes the mechanism created for the validation of parameters in the context of the tessia_baselib module.

# Parameters in practice

The classes that are used to manage different types of guests and hypervisors in tessia_baselib implements a common interface that provide actions to perform operations upon these components. The interface provides common methods that are implemented in different forms according to the type of guest or hypervisor. In the following example we can observe the start method used for hypervisors.
```python
    def start(self, guest_name, cpu, memory, parameters)
```

Each implementation of this interface have particularities that are intrinsic to the type of component that it is supposed to manage. Having said that, we designed the methods of this interface in a way that allow us to have common properties of these components in positional arguments of the methods. The rest of the properties are set in the "parameters" argument as a dictionary.  "parameters" are generic arguments for methods, their content depends on the implementation of these classes. For example, the "parameters" argument expected in the "start" method of the KVM Hypervisor is different in content from "parameters" that would be passed to the "start" method of a HMC Hypervisor.

"parameters" can hold complex and nested information due to the nature and variety of properties that components such a KVM guest can have. In order to avoid burdensome validation of all of the properties that can be set inside the parameters arguments, we opted to use a json schema to validate the parameters dictionary. This approach, similar to xml schemas, provides a meaningful mechanism to validate complex json data.

For more information about json schemas, please visit the following links:

* http://json-schema.org/
* https://spacetelescope.github.io/understanding-json-schema/

# Implementation

The parameters provided in the "parameters" arguments need to be validate against some schema that defines a valid format (expected) for these parameters. In tessia_baselib we chose to create a extensible interface to implement the validation of the parameters. It is possible to chose different validation libraries by using the factory function "create_params_validator". The default library used to validate the parameters is set in the tessia_baselib.yml file, in the property "default_schema_validator". It is also possible to chose different validators by setting the "validator" argument.

Right now, we only support the jsonschema library:

* https://github.com/Julian/jsonschema

In the future we may support other libraries due to performance reasons.

In order to provide a more practical mechanism for validation of parameters, we created a decorator that can be applied to methods of classes that implement guests and hypervisors. This decorator detect the type of action that is being performed based on the name of the method  (start, stop, hotplug, __init__), and the type of component that it is being applied for (hmc, kvm, linux, cms) based on the name of the module.

The schemas must be organized as the following hierarchy in the tessia_baselib source tree:

* tessia_baselib/
    * common/
        * params_validators/
            * schemas/
                * common/
                    * entities/
                         * devicenr_type.json
                         * ...
                    * actions/
                         * start.json
                         * stop.json
                         * ...
                * hmc/
                    * entities/
                        * boot_params_type.json
                        * cpc_name_type.json
                        * ...
                    * actions/
                        * start.json
                        * stop.json
                * (other kinds of hypervisors/guests)

The "schemas" directory has a "common" directory and one directory for each module that implement guests and hypervisors. The name of these directories is equal to the name of the modules. Each of these directories contain the "actions" and "entities" directories. The files in the "actions" directory are json files used to validate the "parameters" argument of the methods with the same name as the files (eg.: start.json validates the "parameters" of the "start" method). The "entities" directory define json schema entities that are only applicable for this domain (eg.: cpc_name_type.json defines the format for the CPC name in HMC hypervisors) and are referenced by the actions. Common entities, that may be referenced by multiple modules, must be defined in the "common" directory (eg.: definition of the format of a device number). For instance, the file "hmc/actions/start.json" contains the json schema that is used for validation of the parameters argument of the "start" method in HMC hypervisor while the file "/common/entities/devicenr_type.json" defines the device number format. This hierarchical structure allow us to easily reuse some definitions.

In the following example, the "validate_params" decorator will use the "tessia_baselib/common/params_validators/schemas/hmc/actions/start.json" file to validate the "parameters" method of the method.

```python
#hmc.py
from tessia_baselib.common.params_validators.utils import validate_params
...

    @validate_params
    def start(self, guest_name, cpu, memory, parameters):
	....
```
