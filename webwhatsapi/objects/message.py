import mimetypes
from base64 import b64decode
from datetime import datetime

import os

from webwhatsapi.helper import safe_str
from webwhatsapi.objects.contact import Contact
from webwhatsapi.objects.whatsapp_object import WhatsappObject


def factory_message(js_obj, driver):
    if js_obj["isMedia"]:
        return MediaMessage(js_obj, driver)

    if js_obj["isNotification"]:
        return NotificationMessage(js_obj, driver)

    if js_obj["isMMS"]:
        return MMSMessage(js_obj, driver)

    if js_obj["type"] in ["vcard", "multi_vcard"]:
        return VCardMessage(js_obj, driver)

    return Message(js_obj, driver)


class Message(WhatsappObject):

    def __init__(self, js_obj, driver=None):
        """
        Constructor

        :param js_obj: Raw JS message obj
        :type js_obj: dict
        """
        super(Message, self).__init__(js_obj, driver)
        self.sender = False if js_obj["sender"] == False else Contact(js_obj["sender"], driver)
        self.timestamp = datetime.fromtimestamp(js_obj["timestamp"])
        if js_obj["content"]:
            self.content = js_obj["content"]
            self.safe_content = safe_str(self.content[0:25]) + '...'
        self.js_obj = js_obj

    def __repr__(self):
        return "<Message - from {sender} at {timestamp}: {content}>".format(
            sender=safe_str(self.sender.get_safe_name()),
            timestamp=self.timestamp,
            content=self.safe_content)


class MediaMessage(Message):
    def __init__(self, js_obj, driver=None):
        super(MediaMessage, self).__init__(js_obj, driver)

        self.type = self.js_obj["type"]
        self.size = self.js_obj["size"]
        self.mime = self.js_obj["mime"]

        extension = mimetypes.guess_extension(self.mime)
        try:
            self.filename = ''.join([self.js_obj["__x_filehash"], extension])
        except KeyError:
            self.filename = ''.join([str(id(self)), extension])

    def save_media(self, path):
        with open(os.path.join(path, self.filename), "wb") as output:
            output.write(b64decode(self.content))

    def __repr__(self):
        return "<MediaMessage - {type} from {sender} at {timestamp} ({filename})>".format(
            type=self.type,
            sender=safe_str(self.sender.get_safe_name()),
            timestamp=self.timestamp,
            filename=self.filename
        )


class MMSMessage(MediaMessage):
    """
    Represents MMS messages

    Example of an MMS message: "ptt" (push to talk), voice memo
    """

    def __init__(self, js_obj, driver=None):
        super(MMSMessage, self).__init__(js_obj, driver)

    def __repr__(self):
        return "<MMSMessage - {type} from {sender} at {timestamp}>".format(
            type=self.type,
            sender=safe_str(self.sender.get_safe_name()),
            timestamp=self.timestamp
        )


class VCardMessage(Message):
    def __init__(self, js_obj, driver=None):
        super(VCardMessage, self).__init__(js_obj, driver)

        self.type = js_obj["type"]
        self.contacts = js_obj["content"].encode("ascii", "ignore")

    def __repr__(self):
        return "<VCardMessage - {type} from {sender} at {timestamp} ({contacts})>".format(
            type=self.type,
            sender=safe_str(self.sender.get_safe_name()),
            timestamp=self.timestamp,
            contacts=self.contacts
        )


class NotificationMessage(Message):
    def __init__(self, js_obj, driver=None):
        super(NotificationMessage, self).__init__(js_obj, driver)
        self.type = js_obj["type"]
        self.subtype = js_obj["subtype"].encode("ascii", "ignore")
        if js_obj["recipients"]:
            self.recipients = [self.driver.get_contact_from_id(x) for x in js_obj["recipients"]]

    def __repr__(self):
        readable = {
            'call_log': {
                'miss': "Missed Call",
            },
            'e2e_notification': {
                'encrypt': "Messages now Encrypted"
            },
            'gp2': {
                'create': "Created group",
                'add': "Added to group",
                'remove': "Removed from group",
                'leave': "Left the group"
            }
        }
        sender = "" if not self.sender else ("from " + str(safe_str(self.sender.get_safe_name())))
        return "<NotificationMessage - {type} {recip} {sender} at {timestamp}>".format(
            type=readable[self.type][self.subtype],
            sender=sender,
            timestamp=self.timestamp,
            recip="" if not hasattr(self, 'recipients') else "".join(
                [safe_str(x.get_safe_name()) for x in self.recipients]),
        )


class MessageGroup(object):
    def __init__(self, chat, messages):
        """
        Constructor

        :param chat: Chat that contains messages
        :type chat: chat.Chat
        :param messages: List of messages
        :type messages: list[Message]
        """
        self.chat = chat
        self.messages = messages

    def __repr__(self):
        safe_chat_name = safe_str(self.chat.name)
        return "<MessageGroup - {num} {messages} in {chat}>".format(
            num=len(self.messages),
            messages="message" if len(self.messages) == 1 else "messages",
            chat=safe_chat_name)