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
from tessia_baselib.guests.base import GuestBase

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class GuestCms(GuestBase):
    """
    This class implements the driver to support the CMS guest type
    """

    # guest class identififer
    guest_id = 'cms'

# GuestCms
