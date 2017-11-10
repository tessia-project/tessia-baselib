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

"""
Factory to expose the hypervisor interface to library consumers
"""

#
# IMPORTS
#
from tessia.baselib.hypervisors.hmc import Hypervisor as hypervisorHmc
from tessia.baselib.hypervisors.kvm import Hypervisor as hypervisorKvm
from tessia.baselib.hypervisors.zvm import Hypervisor as hypervisorZvm

#
# CONSTANTS AND DEFINITIONS
#
SUPPORTED_DRIVERS = {
    hypervisorHmc.HYP_ID: hypervisorHmc,
    hypervisorKvm.HYP_ID: hypervisorKvm,
    hypervisorZvm.HYP_ID: hypervisorZvm,
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
            hyp_type (str): one of the types specified in SUPPORTED_DRIVERS
            args (tuple): positional arguments to forward to driver's
                          constructor
            kwargs (dict): keyword arguments to forward to driver's constructor

        Raises:
            RuntimeError: in case hyp_type is not supported
        """
        # fetch the correct class based on provided type
        driver_cls = SUPPORTED_DRIVERS.get(hyp_type)
        if driver_cls is None:
            raise RuntimeError(
                'Hypervisor type {} is not supported'.format(hyp_type)
            )

        # instantiate the driver and forward arguments from user
        self.__driver = driver_cls(*args, **kwargs)
    # __init__()

    def __getattr__(self, attr):
        """
        Override the method to get object's attribute in order to forward the
        call to the driver object.

        Args:
            attr (str): string with attribute name

        Returns:
            any: the attribute from the driver object

        Raises:
            AttributeError: in case attribute is not present in driver's object
        """
        return getattr(self.__driver, attr)
    # __getattr__()

# Hypervisor
