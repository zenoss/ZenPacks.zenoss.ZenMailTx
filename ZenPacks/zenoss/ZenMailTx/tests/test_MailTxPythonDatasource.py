##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from mock import Mock

from Products.ZenTestCase.BaseTestCase import BaseTestCase

from ZenPacks.zenoss.ZenMailTx.datasources.MailTxPythonDataSource import *


class TestMailTxPythonDataSource(BaseTestCase):
    def test_smtp_error2event(self):
        event = smtp_error2event(Mock(), Exception())
        self.assertEquals(event['summary'], 'Unknown exception in zenmailtx during SMTP transaction')

    def test_pop_error2event(self):
        event = pop_error2event(Mock(), Exception())
        self.assertEquals(event['summary'], 'Unknown exception in zenmailtx during POP transaction')
