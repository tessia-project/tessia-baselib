# Copyright 2020 IBM Corp.
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
Implementation of Operating System Messages reader
"""

#
# IMPORTS
#
from queue import Empty, Queue
from threading import Thread
from zhmcclient import NotificationReceiver

#
# CONSTANTS
#
NOTIFICATION_TYPE_MSG_FIELDS = {
    'os-message': 'os-messages'
}

# Internal queue length
MAX_QUEUED_NOTIFICATIONS = 20


class Messages:
    """
    This class implements Operating System Messages channel

    Messages are read by a separate thread by zhmcclient.NotificationReceiver
    and buffered until requested with get_messages()
    """

    def __init__(self, notification_receiver, notification_type='os-message'):
        """
        Create an async reader from notifications channel

        Args:
            notification_receiver (zhmcclient.NotificationReceiver):
                an active NotificationReceiver object
            notification_type (str): type of messages to process
        """
        self.channel = notification_receiver
        self.notification_type = notification_type
        self.msg_field = NOTIFICATION_TYPE_MSG_FIELDS[self.notification_type]
        self.received_msg_queue = Queue(MAX_QUEUED_NOTIFICATIONS)
        self.poll_thread = None
    # __init__()

    def __enter__(self):
        """
        Context managing entrypoint
        """
        return self
    # __enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context managing exit point

        Having context assures that this object owns communication channel
        and will close it after it is no longer needed
        """
        self.channel.close()
        if self.poll_thread:
            self.poll_thread.join(timeout=5.0)
    # __exit__()

    @classmethod
    def connect(cls, channel_topic, hmc, user, passwd):
        """
        Create Messages instance from parameters
        """
        return cls(NotificationReceiver(channel_topic, hmc, user, passwd))

    def _get_notification(self):
        """
        Retrieve a single HMC notification, which may contain several messages

        Reading notifications is a blocking procedure and stalls an event loop,
        so this method should be run in a separate thread
        """
        for headers, message in self.channel.notifications():
            if headers['notification-type'] != self.notification_type:
                continue

            messages = [entry['message-text'].strip('\n')
                        for entry in message[self.msg_field]]
            self.received_msg_queue.put(messages)
    # _get_notification()

    def get_messages(self, timeout=5.0):
        """
        Get all messages from notification channel.
        Blocking call up to timeout seconds

        Args:
            timeout (number): max seconds to wait

        Returns:
            List: messages
        """
        if not self.poll_thread or not self.poll_thread.is_alive():
            self.poll_thread = Thread(
                name="hmc-listener", target=self._get_notification)
            self.poll_thread.start()

        try:
            return self.received_msg_queue.get(timeout=timeout)
        except Empty:
            return []
    # get_messages()
