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
from zhmcclient import NotificationReceiver, NotificationJMSError

#
# CONSTANTS
#
NOTIFICATION_TYPE_MSG_FIELDS = {
    'os-message': 'os-messages'
}

# Internal queue length
# Queue accumulates messages from NotificationReceiver
# and blocks when length is exceeded.
# Each queue entry is not a single message, but a chunk of several messages,
# as received by NotificationReceiver.
# The exact value is therefore somewhat arbitrary chosen, but value of 1 will
# serialize processing/waiting loop
MAX_QUEUED_NOTIFICATIONS = 20


class Messages:
    """
    This class implements Operating System Messages channel

    Messages are read by a separate thread by zhmcclient.NotificationReceiver
    and buffered until requested with get_messages()
    """

    def __init__(self, reconnect_function, notification_type='os-message'):
        """
        Create an async reader from notifications channel

        Args:
            reconnect_function (Callable[[], zhmcclient.NotificationReceiver]):
                a function returning a NotificationReceiver object
            notification_type (str): type of messages to process
        """
        self._reconnect = reconnect_function
        self.channel = self._reconnect()
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
        if self.channel:
            self.channel.close()
        if self.poll_thread:
            self.poll_thread.join(timeout=5.0)
    # __exit__()

    @classmethod
    def connect(cls, channel_topic, hmc, user, passwd):
        """
        Create Messages instance from parameters

        Args:
            channel_topic (Union[str, Callable]): channel topic to listen to.
                May be a callable in case topic changes
            hmc (str): HMC to connnect to
            user (str): username for HMC
            passwd (str): user password for HMC

        Returns:
            Messages: Messages instance
        """
        def _reconnect():
            if callable(channel_topic):
                topic = channel_topic()
            else:
                topic = channel_topic

            return NotificationReceiver(topic, hmc, user, passwd)

        return cls(_reconnect)

    def _get_notification(self):
        """
        Retrieve pending HMC notifications, which may contain several messages

        Reading notifications is a blocking procedure and stalls an event loop,
        so this method should be run in a separate thread
        """
        if not self.channel:
            return

        try:
            for headers, message in self.channel.notifications():
                if headers['notification-type'] != self.notification_type:
                    continue

                messages = [{
                    'type': 'OS message',
                    'text': entry['message-text'].strip('\n')}
                    for entry in message[self.msg_field]]
                self.received_msg_queue.put(messages)
        except NotificationJMSError as jms_error:
            # there is an error raised, and connection is somewhat broken
            self.received_msg_queue.put([{
                'type': 'JMS error',
                'text': "{}".format(jms_error)}])
            self.channel = None

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
        if not self.channel:
            # we are calling reconnect, which may raise, and we want exceptions
            # to be propagated in caller thread, not in our separete listener
            self.channel = self._reconnect()

        if not self.poll_thread or not self.poll_thread.is_alive():
            self.poll_thread = Thread(
                name="hmc-listener", target=self._get_notification)
            self.poll_thread.start()

        try:
            return self.received_msg_queue.get(timeout=timeout)
        except Empty:
            return []
    # get_messages()
