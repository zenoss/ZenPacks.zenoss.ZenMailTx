##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from mock import Mock, patch
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from ZenPacks.zenoss.ZenMailTx.Mail import sendMessage


class TestMail(BaseTestCase):
    def test_sendMessage(self):
        config = MyMock()
        sender_factory = Mock()

        @patch('twisted.internet.reactor.connectTCP')
        @patch('twisted.mail.smtp.SMTPSenderFactory', new_callable=sender_factory)
        def _test(*_):
            sendMessage(config)
        _test()
        self.assertTrue(sender_factory.called)


class MyMock(object):
    """ Mocking __getattr__ method here """
    def __getattr__(self, item):
        return str(item)
