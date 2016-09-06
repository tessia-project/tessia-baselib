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
Factory to expose the guest interface to library consumers
"""
#
# IMPORTS
#
from tessia_baselib.guests.cms import GUESTCLASS as guestCms
from tessia_baselib.guests.linux import GUESTCLASS as guestLinux

#
# CONSTANTS AND DEFINITIONS
#
GUEST_TYPES = {
    guestCms.GUEST_ID: guestCms,
    guestLinux.GUEST_ID: guestLinux,
}


#
# CODE
#

class Guest(object):
    """
    This is the guest class to be consumed by the user.
    It acts as a factory by determining the correct specific class to
    instantiate based on the type provided and also as a proxy by forwarding
    the calls to the instantiated object.
    """

    def __init__(self, guest_type, *args, **kwargs):
        """
        Constructor

        Args:
            guest_type (str): one of the types specified in GUEST_TYPES
            args (tuple): positional arguments to forward to driver's
                          constructor
            kwargs (dict): keyword arguments to forward to driver's constructor

        Returns:
            None

        Raises:
            RuntimeError: in case guest_type is not supported
        """
        # fetch the correct factory based on provided type
        guest_cls = GUEST_TYPES.get(guest_type)
        if guest_cls is None:
            raise RuntimeError(
                'Guest type {} is not supported'.format(guest_type)
            )

        # instantiate the driver and forward arguments from user
        self.__driver = guest_cls(*args, **kwargs)

    # __init__()

    def __getattr__(self, attr):
        """
        Override the method to get object's attribute in order to forward the
        call to the driver object.

        Args:
            attr (str): attribute name

        Returns:
            any: the attribute from the driver object

        Raises:
            AttributeError: in case attribute is not present in driver's object
        """
        return getattr(self.__driver, attr)
    # __getattr__()

# Guest
