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
from Products.ZenEvents.ZenEventClasses import Status_Web
from Products.ZenUtils.ZenTales import talesCompile, getEngine
from Products.ZenModel.ZenPackPersistence import ZenPackPersistence

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


    factory_type_information = ( 
    { 
        'immediate_view' : 'editMailTxDataSource',
        'actions'        :
        ( 
            { 'id'            : 'edit',
              'name'          : 'Data Source',
              'action'        : 'editMailTxDataSource',
              'permissions'   : ( Permissions.view, ),
            },
            { 'id'            : 'testcheckcommand',
              'name'          : 'Test Now',
              'action'        : 'testMailTxDataSource',
              'permissions'   : ( Permissions.view, ),
              },
        )
    },
    )

    security = ClassSecurityInfo()


    def __init__(self, id, title=None, buildRelations=True):
        Base.__init__(self, id, title, buildRelations)
        for dp in ('totalTime', 'fetchTime', 'sendTime'):
            if not hasattr(self.datapoints, dp):
                self.manage_addRRDDataPoint(dp)

    def zmanage_editProperties(self, REQUEST=None):
        '''validation, etc'''
        return Base.zmanage_editProperties(self, REQUEST)

    security.declareProtected('Change Device', 'manage_testDataSource')
    def manage_testDataSource(self, testDevice, REQUEST):
        ''' Test the datasource by executing the command and outputting the
        non-quiet results.
        '''
        # Render
        header, footer = self.testMailTxOutput().split('OUTPUT_TOKEN')
        out = REQUEST.RESPONSE
        out.write(str(header))

        def write(lines):
            ''' Output (maybe partial) result text.
            '''
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


        # Determine which device to execute against
        device = None
        if testDevice:
            # Try to get specified device
            device = self.findDevice(testDevice)
            if not device:
                REQUEST['message'] = 'Cannot find device matching %s' % testDevice
                return self.callZenScreen(REQUEST)
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
            REQUEST['message'] = 'Cannot determine a device to test against.'
            return self.callZenScreen(REQUEST)
        

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
        out.write(str(footer))


    def doMailTx(self, device, write):
        ''' Execute the given twill commands
        '''
        import ZenPacks.zenoss.ZenMailTx
        # Write twill commands to temp file
        import os, select, fcntl, popen2
        cmd = '%s %s/Mail.py -d "%s" -s "%s"' % (
            sys.executable, ZenPacks.zenoss.ZenMailTx.zpDir, device, self.id)
        child = popen2.Popen4(cmd)
        flags = fcntl.fcntl(child.fromchild, fcntl.F_GETFL)
        fcntl.fcntl(child.fromchild, fcntl.F_SETFL, flags | os.O_NDELAY)
        timeout = max(self.timeout, 1)
        endtime = time.time() + timeout
        pollPeriod = 1
        firstPass = True
        while time.time() < endtime and (firstPass or child.poll() == -1):
            firstPass = False
            r, w, e = select.select([child.fromchild], [], [], pollPeriod)
            if r:
                t = child.fromchild.read()
                # We are sometimes getting to this point without any data
                # from child.fromchild.  I don't think that should happen
                # but the conditional below seems to be necessary.
                if t:
                    write(t)

        if child.poll() == -1:
            write('Mail transaction timed out')
            import signal
            os.kill(child.pid, signal.SIGKILL)
