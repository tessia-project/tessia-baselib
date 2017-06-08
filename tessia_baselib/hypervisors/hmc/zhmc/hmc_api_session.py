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

'''
HMC Api Session Handler
'''

#
# IMPORTS
#
from datetime import timedelta
from contextlib import suppress
from tessia_baselib.common.logger import get_logger
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcRequestError
# the import is there but pylint does not recognize it
# pylint: disable=import-error
from requests.packages.urllib3.exceptions import InsecureRequestWarning
# pylint: enable=import-error

import time
import requests
import warnings

#
# CONSTANTS AND DEFINITIONS
#

DEFAULT_HMC_PORT = 6794

REQUESTS = {
    "GET": requests.get,
    "POST": requests.post,
    "DELETE": requests.delete,
    "PUT": requests.put
}

#
# CODE
#


class HmcApiSession(object):
    """
    This class is responsible for creating the session with the HMC and
    providing the necessary methods to make (post and get) requests to
    the HMC.
    """
    def __init__(self, host_name, user, passwd, timeout, port):
        """
        Constructor

        Args:
            host_name (str): hostname or ip address of system
            user (str): user to login to system
            passwd (str): password to login to system
            port (int): post to connect to HMC
            timeout (int): connection timeout

        Raises:
            None
        """
        # suppress warnings from urllib3 related to cert validation
        warnings.filterwarnings('ignore', category=InsecureRequestWarning)

        self._logger = get_logger(__name__)

        self.host_name = host_name
        self.timeout = timeout

        if port is None:
            self.port = DEFAULT_HMC_PORT
        else:
            self.port = port

        self._user = user
        self._passwd = passwd

        self.session_id = None
    # __init__()

    def open_session(self):
        """
        This is an auxiliary method to open a session to the HMC.

        Args:
            None

        Raises:
            None
        """
        # Create a session with the HMC
        logon_response = self.json_request(
            "POST",
            "/api/session",
            body={"userid": self._user, "password": self._passwd}
        )

        self.session_id = logon_response["api-session"]

    def close_session(self):
        """
        This is an auxiliary method to close an active session to the HMC.

        Args:
            None

        Raises:
            None
        """

        if self.session_id is not None:
            self.json_request(
                "DELETE",
                "/api/session/this-session"
            )
            self.session_id = None

    def _validate_response(self, response):
        """
        This is an auxiliary method to validade the HTTP response from the HMC.

        Args:
            response (requests.Response): http response from requests lib

        Raises:
            ZHmcRequestError: if request fails
        """
        self._logger.debug("Validating HTTP response")

        # If the request fails in some way (HTTP status not 2xx), the HMC
        # Web Services  API response will usually include a standard error
        # response body in JSON format that includes a more detailed reason
        # code (and message) for the failure. It provides this data in JSON
        # format even if the request would return some other format if the
        # request had been successful. So if the request  has failed, grab
        # that additional info  for use in raising exceptions below.

        if response.status_code < 200 or response.status_code > 299:
            failure_reason = 0
            failure_message = None
            failure_stack = None

            # The HMC API provides the JSON error response in all usual error
            # cases.  But for certain less common errors this does not occur
            # because the error is caught higher in the processing stack.
            # So try to interpret the response as a JSON response body, but
            # just  silently ignore problems if we can't do this.

            with suppress(ValueError, KeyError):
                error_resp = response.json()
                failure_reason = error_resp["reason"]
                failure_message = error_resp["message"]
                failure_stack = error_resp["stack"]

            raise ZHmcRequestError(
                response.status_code,
                failure_reason,
                failure_message,
                failure_stack
            )
    # _validate_response()

    def json_request(self, method, uri, body=None, headers=None):
        """
        Issue an HMC WS API request that is defined to take JSON input and
        produce JSON output.

        Args:
            method (str): the HTTP method to issue (eg. GET, PUT, POST, DELETE)
            uri (uri): URI path and query parameter string for the request.
            body (dict): the request body in the form of a dict or list
                         object. This object is automatically converted to
                         corresponding JSON by this function.
            headers (dict): request headers for this request, optional

        Returns:
            dict: response body

        Raises:
            ZHmcRequestError: Raised if response body was not JSON
        """
        start_time = time.time()

        if headers is None:
            headers = dict()

        if self.session_id is not None:
            headers["X-API-Session"] = self.session_id

        url = "https://" + self.host_name + ":" + str(self.port) + uri

        response = REQUESTS[method](
            url,
            headers=headers,
            json=body,
            verify=False, # TODO Need to add a certificate and remove this
            timeout=self.timeout
        )

        self._validate_response(response)

        end_time = time.time()

        human_uptime = timedelta(seconds=int(end_time - start_time))

        self._logger.debug(
            "HTTP Request\n start_time='%s'\n end_time='%s'\n duration='%s' "
            "method='%s'\n URI='%s'\n header='%s'\n response_status='%s'\n "
            "response_body='%s'",
            start_time,
            end_time,
            human_uptime,
            method,
            uri,
            format(headers),
            response.status_code,
            response.text
        )

        # 204 means no body: return empty response
        if response.status_code == 204:
            return dict()

        try:
            return_body = response.json()
        except ValueError:
            raise ZHmcRequestError("Response body expected to be JSON.")

        return return_body
    # json_request()
# HmcApiSession
