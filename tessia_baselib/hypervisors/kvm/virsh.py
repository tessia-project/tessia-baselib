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
from tessia_baselib.common.logger import get_logger
from tempfile import mkstemp
from xml.etree import ElementTree

import os
#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class Virsh(object):
    """
    This class provides an wrapper for the virsh command
    that is executed in the hypervisor.
    """
    def __init__(self, host_cnn, cmd_channel):
        """
        Class constructor. Initialize object variables and logging.

        Args:
            cmd_channel An object that provides a method in the format
                        "run(self, cmd, timeout=120):". This method is used
                        to perform commands in the hypervisor.

        Returns:
            None

        Raises:
            None
        """
        self._cmd_channel = cmd_channel
        self._host_cnn = host_cnn
        self._logger = self._logger = get_logger(__name__)
        # These variables keep tracks of temporary files created to perform
        # a network boot.
        self._tmp_netboot_initrd = None
        self._tmp_netboot_kernel = None
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

        self._logger.debug("Boot domain %s:", boot_domain_xml)

        return boot_domain_xml
    # _add_boot_tag()

    def clean_tmp_netboot_files(self):
        """
        Auxiliary method to remove the temporary kernel and initrd
        created in the host.
        """

        if self._tmp_netboot_kernel is not None:
            cmd = "rm {}".format(self._tmp_netboot_kernel)
            ret, output = self._cmd_channel.run(cmd)

            if ret != 0:
                self._logger.warning("Error while removing temporary"
                                     " kernel file %s: %s",
                                     self._tmp_netboot_kernel,
                                     output)
        else:
            self._logger.warning("Temporary kernel file does not exist.")

        if self._tmp_netboot_initrd is not None:
            cmd = "rm {}".format(self._tmp_netboot_initrd)
            ret, output = self._cmd_channel.run(cmd)

            if ret != 0:
                self._logger.warning("Error while removing temporary"
                                     " initrd file %s: %s",
                                     self._tmp_netboot_initrd,
                                     output)
        else:
            self._logger.warning("Temporary initrd file does not exist.")

        self._tmp_netboot_initrd = None
        self._tmp_netboot_kernel = None
    # clean_tmp_netboot_files()


    def define_netboot(self, domain_xml, boot_params):
        """
        Defines a domain xml used for network boot.

        Args:
            domain_xml (str): String containing the domain xml.
            boot_params (dict): A dictionary contaning information about the
                                the netboot, as described in the jsonschema
                                kvm/entitites/boot_params_type.json.

        Returns:
            None

        Raises:
            RuntimeError: In case there is a error while creating the temporary
                          files.
        """
        kernel_uri = boot_params["kernel_uri"]
        initrd_uri = boot_params["initrd_uri"]
        cmdline = boot_params["cmdline"]

        self._logger.debug("Defining domain xml for network boot with"
                           " parameters: %s", boot_params)

        if (self._tmp_netboot_initrd is not None or
                self._tmp_netboot_kernel is not None):
            self._logger.warning("The kernel and initrd from"
                                 " a previous netboot still"
                                 " exist. Performing cleaning up.")
            self.clean_tmp_netboot_files()

        # create temporary files to hold the kernel and initrd
        cmd = "mktemp"
        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            raise RuntimeError("Error while creating "
                               "temporary file in the"
                               " host: {}".format(output))
        self._tmp_netboot_kernel = output.strip()

        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            raise RuntimeError("Error while creating "
                               "temporary file in the"
                               " host: {}".format(output))
        self._tmp_netboot_initrd = output.strip()

        # send kernel and initrd to the temporary files.
        self._host_cnn.push_file(kernel_uri, self._tmp_netboot_kernel)
        self._host_cnn.push_file(initrd_uri, self._tmp_netboot_initrd)

        self.define(self._add_boot_tag(domain_xml,
                                       self._tmp_netboot_kernel,
                                       self._tmp_netboot_initrd, cmdline))
    # define_netboot()

    def define(self, domain_xml):
        """
        Defines a domain xml.

        Args:
            domain_xml (str): String containing the domain xml.

        Returns:
            None

        Raises:
            RuntimeError: In case it is not possible to create a
                         temporary file in the hypervisor.
                         In the define command fails.
        """

        self._logger.debug("Defining domain xml: %s", domain_xml)

        file_descriptor, path = mkstemp(suffix=".xml", text=True)
        tmp_file = open(file_descriptor, "w")

        tmp_file.write(domain_xml)
        tmp_file.close()

        source_url = "file://" + path

        cmd = "mktemp --suffix='.xml'"
        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            raise RuntimeError("Error while creating "
                               "temporary file in the"
                               " host: {}".format(output))

        domain_file = output.strip()

        self._host_cnn.push_file(source_url, domain_file)

        cmd = "virsh define {}".format(domain_file)
        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            raise RuntimeError("Error while defining domain: "
                               "{}".format(output))
        os.remove(path)
        cmd = "rm {}".format(domain_file)
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

        Returns:
            None

        Raises:
            RuntimeError: If the destroy command fails.
        """
        self._logger.debug("Destroying domain %s", domain_name)

        cmd = "virsh destroy {}".format(domain_name)
        status, output = self._cmd_channel.run(cmd)

        if status != 0:
            raise RuntimeError("Error while destroying domain: "
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

        Returns:
            None

        Raises:
            RuntimeError: If the reset command fails.
        """
        self._logger.debug("Reseting domain %s", domain_name)

        cmd = "virsh reset {}".format(domain_name)
        status, output = self._cmd_channel.run(cmd)

        if status != 0:
            raise RuntimeError("Error while reseting domain "
                               "{}: {}".format(domain_name, output))
    # reset()

    def start(self, domain_name):
        """
        Starts a domain.

        Args:
            domain_name (str): Name of the domain to be started.

        Returns:
            None

        Raises:
            RuntimeError: If the start command fails.
        """
        self._logger.debug("Starting domain %s", domain_name)

        cmd = "virsh start {}".format(domain_name)
        status, output = self._cmd_channel.run(cmd)
        if status != 0:
            raise RuntimeError("Error while starting domain "
                               "{}: {}".format(domain_name, output))
    # start()

    def undefine(self, domain_name):
        """
        Undefine a domain xml.

        Args:
            domain_name (str): Name of the domain to be undefined.

        Returns:
            None

        Raises:
            RuntimeError: in case there is a error while executing the
                         undefine command.
        """
        self._logger.debug("Undefining domain %s", domain_name)

        cmd = "virsh undefine {}".format(domain_name)
        status, output = self._cmd_channel.run(cmd)

        if status != 0:
            raise RuntimeError("Error while undefining "
                               "domain {}: {}".format(domain_name, output))
    # undefine()
# Virsh
