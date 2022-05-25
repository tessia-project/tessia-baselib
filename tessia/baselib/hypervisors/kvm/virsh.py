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
Module for Virsh class
"""

#
# IMPORTS
#
from tessia.baselib.common.logger import get_logger
from tempfile import mkstemp
from xml.etree import ElementTree

import os
import time

#
# CONSTANTS AND DEFINITIONS
#
DOMAIN_FILENAME = 'domain'
KERNEL_FILENAME = 'kernel'
INITRD_FILENAME = 'initrd'

#
# CODE
#


class Virsh:
    """
    This class provides a wrapper for the virsh commands that are executed in
    the hypervisor.
    """

    def __init__(self, host_cnn):
        """
        Class constructor. Initialize object variables and logging.

        Args:
            host_cnn (GuestLinux): instance connected to linux host

        Raises:
            None
        """
        self._logger = get_logger(__name__)
        self._host_cnn = host_cnn
        self._cmd_channel = self._host_cnn.open_session()

        # temporary directory to hold working files (domain xml, kernel,
        # initrd)
        self._tmp_dir = None
    # __init__()

    def _add_boot_tag(self, domain_xml, kernel_path, initrd_path, cmdline):
        """
        Auxiliary method, add the boot parameters to the domain xml.

        Args:
            domain_xml (str):  The original domain xml.
            kernel_path (str): Path to kernel in the host.
            initrd_path (str): Path to the initrd in the host.
            cmdline (str):     Parameters passed to the kernel during the boot.

        Returns:
            str: Domain xml with the boot tag fulfilled.

        Raises:
            None
        """
        domain_element = ElementTree.fromstring(domain_xml)

        os_element = domain_element.find("os")

        # create the new tags
        kernel_element = ElementTree.SubElement(os_element, "kernel")
        initrd_element = ElementTree.SubElement(os_element, "initrd")
        cmdline_element = ElementTree.SubElement(os_element, "cmdline")

        kernel_element.text = kernel_path
        initrd_element.text = initrd_path
        cmdline_element.text = cmdline
        boot_domain_xml = ElementTree.tostring(domain_element,
                                               encoding="unicode")

        self._logger.debug("Domain after adding boot tag: %s", boot_domain_xml)

        return boot_domain_xml
    # _add_boot_tag()

    def _get_tmp_dir(self):
        """
        Return the temp directory used by the object to store working files.

        Returns:
            str: path to temp directory on host

        Raises:
            RuntimeError: in case of error while creating temp dir on host
        """
        # temp dir already exists: return it
        if self._tmp_dir is not None:
            return self._tmp_dir

        # first time usage: create the temp dir on host and set appropriate
        # permissions
        cmd = "mktemp -d"
        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            raise RuntimeError("Error while creating "
                               "temporary directory in the"
                               " host: {}".format(output))
        self._tmp_dir = output.strip()
        cmd = "chmod 755 {}".format(self._tmp_dir)
        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            self._raise_and_cleanup(
                "Failed to set permissions for temporary directory in the "
                "host: {}".format(output))

        return self._tmp_dir
    # _get_tmp_dir()

    def _raise_and_cleanup(self, msg):
        """
        In case some operation fails, make sure to clean up temp dir otherwise
        files will be forgotten in filesystem

        Args:
            msg (str): message to used in Exception

        Raises:
            RuntimeError: always
        """
        self.clean_tmp_dir()
        raise RuntimeError(msg)
    # _raise_and_cleanup()

    def clean_tmp_dir(self):
        """
        Auxiliary method to remove the temporary directory created in the host.
        """

        # no temp directory created: nothing to do
        if self._tmp_dir is None:
            return

        cmd = "rm -rf {}".format(self._tmp_dir)
        ret, output = self._cmd_channel.run(cmd)

        if ret != 0:
            self._logger.warning(
                "Failed to remove temporary directory %s: %s",
                self._tmp_dir,
                output)
        self._tmp_dir = None

    # clean_tmp_dir()

    def close(self):
        """
        Perform cleanup and close the shell session.
        """
        self.clean_tmp_dir()
        self._cmd_channel.close()
        self._cmd_channel = None
        self._host_cnn = None
    # close()

    def define_netboot(self, domain_xml, boot_params):
        """
        Defines a domain xml used for network boot.

        Args:
            domain_xml (str): String containing the domain xml.
            boot_params (dict): A dictionary containing information about the
                                netboot, as described in the jsonschema
                                kvm/entitites/boot_params_type.json.

        Raises:
            RuntimeError: In case there is an error while creating the
                          temporary files.
        """
        kernel_uri = boot_params["kernel_uri"]
        initrd_uri = boot_params["initrd_uri"]
        cmdline = boot_params["cmdline"]

        self._logger.debug("Defining domain xml for network boot with"
                           " parameters: %s", boot_params)

        # send kernel and initrd to the temporary files.
        tmp_kernel = os.path.join(self._get_tmp_dir(), KERNEL_FILENAME)
        self._host_cnn.push_file(kernel_uri, tmp_kernel)
        tmp_initrd = os.path.join(self._get_tmp_dir(), INITRD_FILENAME)
        self._host_cnn.push_file(initrd_uri, tmp_initrd)

        self.define(self._add_boot_tag(
            domain_xml, tmp_kernel, tmp_initrd, cmdline))
    # define_netboot()

    def define(self, domain_xml):
        """
        Defines a domain xml.

        Args:
            domain_xml (str): String containing the domain xml.

        Raises:
            RuntimeError: In case it is not possible to create a
                         temporary file in the hypervisor.
                         In the define command fails.
        """

        self._logger.debug("Defining domain xml: %s", domain_xml)

        # create local file with the xml content
        file_descriptor, path = mkstemp(suffix=".xml", text=True)
        with open(file_descriptor, "w") as local_domain_file:
            local_domain_file.write(domain_xml)

        # push the local file to the host in our temporary directory
        source_url = "file://" + path
        domain_file = os.path.join(self._get_tmp_dir(), DOMAIN_FILENAME)
        self._host_cnn.push_file(source_url, domain_file)

        cmd = "virsh define {}".format(domain_file)
        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            self._raise_and_cleanup(
                "Error while defining domain: {}".format(output))
        os.remove(path)
        cmd = "rm -f {}".format(domain_file)
        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            self._logger.warning("Unable to remove "
                                 "temporary file in the"
                                 " hypervisor: %s", domain_file)
    # define()

    def destroy(self, domain_name):
        """
        Destroys a domain.

        Args:
            domain_name (str): Name of the domain to be destroyed.

        Raises:
            RuntimeError: If the destroy command fails.
        """
        self._logger.debug("Destroying domain %s", domain_name)

        cmd = "virsh destroy {}".format(domain_name)
        status, output = self._cmd_channel.run(cmd)

        if status != 0:
            self._raise_and_cleanup("Error while destroying domain: "
                                    "{}: {}".format(domain_name, output))
    # destroy()

    def get_dominfo(self, domain_name):
        """
        Get the dominfo properties of a domain.

        Args:
            domain_name (str): Name of the domain.

        Returns:
            dict: A dictionary containing the domain info as key/value pairs.

        Raises:
            RuntimeError: In case the dominfo command fails.
        """
        cmd = "virsh dominfo {}".format(domain_name)
        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            raise RuntimeError("Error while getting dominfo for "
                               "domain {}".format(domain_name))

        dominfo_str = output.strip()
        dominfo = {}

        for line in dominfo_str.split("\n"):
            key, _, value = line.partition(":")
            dominfo[key] = value.lstrip()

        return dominfo
    # get_dominfo()

    def is_defined(self, domain_name):
        """
        Checks that a domain is defined.

        Args:
            domain_name (str): Name of the domain to be checked.

        Returns:
            bool: True if the domain is defined. False otherwise.

        Raises:
            None
        """
        try:
            self.get_dominfo(domain_name)
        except RuntimeError:
            return False
        return True
    # is_defined()

    def is_running(self, domain_name):
        """
        Checks if the domain is running.

        Args:
            domain_name (str): Name of the domain.

        Returns:
            bool: True if the domain is running, False otherwhise.

        Raises:
            None
        """
        try:
            dominfo = self.get_dominfo(domain_name)
        except RuntimeError:
            return False

        state = dominfo.get("State")

        if state == "running":
            return True

        return False
    # is_running()

    def reset(self, domain_name):
        """
        Resets a domain.

        Args:
            domain_name (str): Name of the domain to be reset.

        Raises:
            RuntimeError: If the reset command fails.
        """
        self._logger.debug("Reseting domain %s", domain_name)

        cmd = "virsh reset {}".format(domain_name)
        status, output = self._cmd_channel.run(cmd)

        if status != 0:
            self._raise_and_cleanup("Error while reseting domain "
                                    "{}: {}".format(domain_name, output))
    # reset()

    def shutdown(self, domain_name, timeout=120):
        """
        Shutdown (stop) a domain.

        Args:
            domain_name (str): Name of the domain to be shut down.
            timeout (float): Timeout to wait for shutdown in seconds.

        Raises:
            RuntimeError: If the shutdown command fails.
        """
        self._logger.debug("Shutting down domain %s", domain_name)
        cmd = f"virsh shutdown {domain_name}"
        status, output = self._cmd_channel.run(cmd)

        if status != 0:
            self._raise_and_cleanup("Error while shutting down domain: "
                                    f"{domain_name}: {output}")

        time_end = time.monotonic() + timeout
        while True:
            if not self.is_running(domain_name):
                break

            if time.monotonic() > time_end:
                self._logger.debug("Timed out waiting for shutdown of %s",
                                   domain_name)
                self.destroy(domain_name)
                break
            time.sleep(5.)
    # shutdown()

    def start(self, domain_name):
        """
        Starts a domain.

        Args:
            domain_name (str): Name of the domain to be started.

        Raises:
            RuntimeError: If the start command fails.
        """
        self._logger.debug("Starting domain %s", domain_name)

        cmd = "virsh start {}".format(domain_name)
        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            self._raise_and_cleanup("Error while starting domain "
                                    "{}: {}".format(domain_name, output))
    # start()

    def undefine(self, domain_name):
        """
        Undefine a domain xml.

        Args:
            domain_name (str): Name of the domain to be undefined.

        Raises:
            RuntimeError: in case there is a error while executing the
                         undefine command.
        """
        self._logger.debug("Undefining domain %s", domain_name)

        cmd = "virsh undefine {}".format(domain_name)
        status, output = self._cmd_channel.run(cmd)

        if status != 0:
            self._raise_and_cleanup(
                "Error while undefining domain {}: {}".format(
                    domain_name, output)
            )
    # undefine()
# Virsh
