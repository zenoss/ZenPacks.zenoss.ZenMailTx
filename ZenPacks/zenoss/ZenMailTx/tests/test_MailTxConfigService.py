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
from ZenPacks.zenoss.ZenMailTx.MailTxConfigService import (
    Config,
    MailTxConfigService
)


class MyConfig(Config):
    def __init__(self):
        pass


class MyMailTxConfigService(MailTxConfigService):
    def __init__(self):
        pass


class TestConfig(BaseTestCase):
    def afterSetUp(self):
        self.config = MyConfig()
        self.config.name = Mock()
        self.config.device = Mock()

    def test_key(self):
        self.assertEquals(self.config.key(),
                          (self.config.device, self.config.name))

    def test_update(self):
        value = Mock(value=True)
        self.config.update(value)
        self.assertTrue(self.config.value)

    def test_completedOneAttempt(self):
        self.config.sent = 1
        self.msgid = True
        self.assertTrue(self.config.completedOneAttempt())

    def hasMessageOutstanding(self):
        self.config.msgid = True
        self.assertTrue(self.config.hasMessageOutstanding())

    def test_nextRun(self):
        self.config.sent = 1
        self.config.cycletime = 1
        self.assertEquals(self.config.nextRun(), 2)

        self.config.msgid = True
        self.config.timeout = 2
        self.assertEquals(self.config.nextRun(), 3)


class TestMailTxConfigService(BaseTestCase):
    def afterSetUp(self):
        self.c = MyMailTxConfigService()

    @patch("ZenPacks.zenoss.ZenMailTx.MailTxConfigService.Config")
    @patch("Products.ZenCollector.services.config.CollectorConfigService._createDeviceProxy")
    def test_createDeviceProxy(self, *args):
        template = Mock()
        template.getRRDDataSources.return_value = [Mock(sourcetype='MAILTX')]

        device = Mock()
        device.getRRDTemplates.return_value = [template]

        self.c._checkMailTxDs = lambda *_: True
        self.assertIsNotNone(self.c._createDeviceProxy(device))

    def test_checkMailTxDs(self):
        ds = Mock(enabled=True)
        self.c._checkReqFields = Mock(return_value=True)
        self.assertTrue(self.c._checkMailTxDs(None, None, ds))

        ds.enabled = False
        self.assertFalse(self.c._checkMailTxDs(None, None, Mock(enabled=False)))

        ds.enabled = True
        self.c._checkReqFields.return_value = False
        self.assertFalse(self.c._checkMailTxDs(None, None, ds))

        ds.smtpAuth = True
        self.assertFalse(self.c._checkMailTxDs(None, None, ds))

    def test_checkReqFields(self):
        t = Mock()
        d = Mock()
        r = ['f']

        self.assertTrue(self.c._checkReqFields(d, t, Mock(f=True), r))

        with patch('ZenPacks.zenoss.ZenMailTx.MailTxConfigService.log') as log:
            self.assertFalse(self.c._checkReqFields(d, t, Mock(f=False), r))
            self.assertTrue(log.warn.called)
