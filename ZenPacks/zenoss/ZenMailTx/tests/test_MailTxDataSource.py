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
from ZenPacks.zenoss.ZenMailTx.datasources.MailTxDataSource import MailTxDataSource


class TestMailTxDataSource(BaseTestCase):
    def afterSetUp(self):
        self.ds = MailTxDataSource(id=1)

    def test_init(self):
        self.assertEquals(self.ds.id, 1)
        self.assertItemsEqual((x.id for x in self.ds.datapoints()),
                              ('totalTime', 'fetchTime', 'sendTime'))

    def test_testDataSourceAgainstDevice(self):
        write, error = Mock(), Mock()

        self.ds.testDataSourceAgainstDevice(None, None, write, error)
        self.assertEquals(error.call_count, 1)
        self.assertEquals(write.call_count, 0)

        self.ds.getSubDevicesGen = Mock(next=Mock(return_value=None))
        self.ds.testDataSourceAgainstDevice(None, None, write, error)
        self.assertEquals(error.call_count, 1)
        self.assertEquals(write.call_count, 4)

        self.ds.device = Mock(return_value=None)
        self.ds.testDataSourceAgainstDevice(None, None, write, error)
        self.assertEquals(error.call_count, 2)
        self.assertEquals(write.call_count, 4)
