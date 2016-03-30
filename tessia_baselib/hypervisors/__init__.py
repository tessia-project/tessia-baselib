# Copyright 2016, 2017 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# IMPORTS
#
from tessia_baselib.hypervisors.hmc import hypClass as hypervisorHmc
from tessia_baselib.hypervisors.kvm import hypClass as hypervisorKvm
from tessia_baselib.hypervisors.zvm import hypClass as hypervisorZvm

#
# CONSTANTS AND DEFINITIONS
#
SUPPORTED_DRIVERS = {
    hypervisorHmc.hyp_id: hypervisorHmc,
    hypervisorKvm.hyp_id: hypervisorKvm,
    hypervisorZvm.hyp_id: hypervisorZvm,
}


#
# CODE
#

class Hypervisor(object):
    """
    This is the hypervisor class to be consumed by the user.
    It acts as a factory by determining the correct specific class to
    instantiate based on the type provided and also as a proxy by forwarding
    the calls to the instantiated object.
    """

    def __init__(self, hyp_type, *args, **kwargs):
        """
        Constructor

        Args:
            hyp_type: one of the types specified in SUPPORTED_DRIVERS
            args: positional arguments to forward to driver's constructor
            kwargs: keyword arguments to forward to driver's constructor

        Returns:
            None

        Raises:
            RuntimeError: in case hyp_type is not supported
        """
        # fetch the correct class based on provided type
        driverClass = SUPPORTED_DRIVERS.get(hyp_type)
        if driverClass is None:
            raise RuntimeError(
                'Hypervisor type {} is not supported'.format(hyp_type)
            )

        # instantiate the driver and forward arguments from user
        self.__driver = driverClass(*args, **kwargs)
    # __init__()

    def __getattr__(self, attr):
        """
        Override the method to get object's attribute in order to forward the
        call to the driver object.

        Args:
            attr: string with attribute name

        Returns:
            the attribute from the driver object

        Raises:
            AttributeError: in case attribute is not present in driver's object
        """
        return getattr(self.__driver, attr)
    # __getattr__()

# Hypervisor

