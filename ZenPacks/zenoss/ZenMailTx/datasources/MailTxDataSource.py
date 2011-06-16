######################################################################
#
# Copyright 2007 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

__doc__='''MailTxDataSource.py

Defines datasource for ZenMailTx round-trip mail testing.
Part of ZenMailTx zenpack.
'''

from Products.ZenModel.RRDDataSource import RRDDataSource
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenPackPersistence import ZenPackPersistence
from Products.ZenUtils.Utils import executeStreamCommand
from Products.ZenWidgets import messaging

import sys
import time
import cgi

Base = RRDDataSource
class MailTxDataSource(ZenPackPersistence, Base):

    ZENPACKID = 'ZenPacks.zenoss.ZenMailTx'

    sourcetypes = ('MAILTX',)
    sourcetype = 'MAILTX'

    AuthModes = ('None', 'TLS', 'SSL')
    smtpHost = ''
    smtpPort = 25
    smtpUsername = ''
    smtpPassword = ''
    toAddress = ''
    fromAddress = ''
    smtpAuth = 'None'
    popHost = ''
    popPort = 110
    popUsername = ''
    popPassword = ''
    popAuth = 'None'
    popAllowInsecureLogin = False
    cycleTime = 300
    timeout = 300
    messageBody = '''This message is used by the Zenoss monitoring system to gauge e-mail delivery transaction time. Please ignore this message.'''
    
    eventClass = '/App/Email/Loop'

    _properties = Base._properties + (
        {'id':'smtpHost', 'type':'string', 'mode':'w'},
        {'id':'smtpPort', 'type':'int', 'mode':'w'},
        {'id':'smtpUsername', 'type':'string', 'mode':'w'},
        {'id':'smtpPassword', 'type':'string', 'mode':'w'},
        {'id':'toAddress', 'type':'string', 'mode':'w'},
        {'id':'fromAddress', 'type':'string', 'mode':'w'},
        {'id':'smtpAuth', 'type':'string', 'mode':'w'},
        {'id':'popHost', 'type':'string', 'mode':'w'},
        {'id':'popPort', 'type':'string', 'mode':'w'},
        {'id':'popUsername', 'type':'string', 'mode':'w'},
        {'id':'popPassword', 'type':'string', 'mode':'w'},
        {'id':'popAuth', 'type':'string', 'mode':'w'},
        {'id':'popAllowInsecureLogin', 'type':'boolean', 'mode':'w'},
        {'id':'cycleTime', 'type':'int', 'mode':'w'},
        {'id':'timeout', 'type':'int', 'mode':'w'},
        {'id':'messageBody', 'type':'string', 'mode':'w'},
        )

        
    _relations = Base._relations + (
        )

    security = ClassSecurityInfo()


    def __init__(self, id, title=None, buildRelations=True):
        Base.__init__(self, id, title, buildRelations)
        #when being copied the relation attributes won't appear till later
        if getattr(self, 'datapoints') is not None:
            dpIds = map(lambda x: x.id, self.datapoints())
            for dp in ('totalTime', 'fetchTime', 'sendTime'):
                if not dp in dpIds:
                    self.manage_addRRDDataPoint(dp)

    def zmanage_editProperties(self, REQUEST=None):
        '''validation, etc'''
        return Base.zmanage_editProperties(self, REQUEST)

    def testDataSourceAgainstDevice(self, testDevice, REQUEST, write, errorLog):
        """
        Does the majority of the logic for testing a datasource against the device
        @param string testDevice The id of the device we are testing
        @param Dict REQUEST the browers request
        @param Function write The output method we are using to stream the result of the command
        @parma Function errorLog The output method we are using to report errors
        """

        # Render
        # Determine which device to execute against
        device = None
        if testDevice:
            # Try to get specified device
            device = self.findDevice(testDevice)
            if not device:
                 errorLog('Error', 'Cannot find device matching %s' % testDevice)
                 return 
        elif hasattr(self, 'device'):
            # ds defined on a device, use that device
            device = self.device()
        elif hasattr(self, 'getSubDevicesGen'):
            # ds defined on a device class, use any device from the class
            try:
                device = self.getSubDevicesGen().next()
            except StopIteration:
                # No devices in this class, bail out
                pass
        if not device:
            errorLog('Error', 'Cannot determine a device to test against.')
            return 
        start = time.time()
        try:
            self.doMailTx(device.id, write)
        except:
            write('exception while executing mail transaction')
            write('type: %s  value: %s' % tuple(sys.exc_info()[:2]))
            from StringIO import StringIO
            import traceback
            s = StringIO()
            traceback.print_exc(file=s)
            write(s.getvalue())
            write('type: %s  value: %s' % tuple(sys.exc_info()[:2]))
        write('')
        write('DONE in %s seconds' % long(time.time() - start))
        
    security.declareProtected('Change Device', 'manage_testDataSource')
    def manage_testDataSource(self, testDevice, REQUEST):
        """ Test the datasource by executing the command and outputting the
        non-quiet results.
        """
        out = REQUEST.RESPONSE
        def write(lines):
            """ Output (maybe partial) result text.
            """
            # Looks like firefox renders progressive output more smoothly
            # if each line is stuck into a table row.  
            startLine = '<tr><td class="tablevalues">'
            endLine = '&nbsp;</td></tr>\n'
            if out:
                if not isinstance(lines, list):
                    lines = [lines]
                for l in lines:
                    if not isinstance(l, str):
                        l = str(l)
                    l = l.strip()
                    l = cgi.escape(l)
                    l = l.replace('\n', endLine + startLine)
                    out.write(startLine + l + endLine)
        errorLog = messaging.IMessageSender(self).sendToBrowser
        self.testDataSourceAgainstDevice(testDevice, REQUEST, write, errorLog)

    def doMailTx(self, device, write):
        """ Test the MAILTX data source
        """
        import ZenPacks.zenoss.ZenMailTx
        # run the command in a separate process
        cmd = '%s %s/Mail.py -d "%s" -s "%s"' % (
            "$ZENHOME/bin/python", ZenPacks.zenoss.ZenMailTx.zpDir, device, self.id)
        executeStreamCommand(cmd, write)
