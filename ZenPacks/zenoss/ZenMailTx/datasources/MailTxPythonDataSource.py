##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


'''
Defines datasource for ZenMailTx round-trip mail testing using Python Collector
Part of ZenMailTx zenpack.
'''

import logging
import time
import traceback

from zope.component import adapts
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from twisted.internet import defer, error
from twisted.mail.pop3 import ServerErrorResponse
from twisted.mail.smtp import AUTHDeclinedError

from Products.Zuul.form import schema
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.template import RRDDataSourceInfo
from Products.Zuul.interfaces import IRRDDataSourceInfo
from Products.Zuul.utils import ZuulMessageFactory as _t

from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource \
    import PythonDataSource, PythonDataSourcePlugin

from  ZenPacks.zenoss.ZenMailTx.Mail import sendMessage, getMessage

log = logging.getLogger("zenmailtx")


class MailTxPythonDataSource(PythonDataSource):

    ZENPACKID = 'ZenPacks.zenoss.ZenMailTx'

    sourcetypes = ('PYMAILTX',)
    sourcetype = 'PYMAILTX'

    plugin_classname = 'ZenPacks.zenoss.ZenMailTx.datasources.MailTxPythonDataSource.MailTxPythonDataSourcePlugin'

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

    _properties = PythonDataSource._properties + (
        {'id':'smtpHost', 'type':'string', 'mode':'w'},
        {'id':'smtpPort', 'type':'int', 'mode':'w'},
        {'id':'smtpUsername', 'type':'string', 'mode':'w'},
        {'id':'smtpPassword', 'type':'string', 'mode':'w'},
        {'id':'toAddress', 'type':'string', 'mode':'w'},
        {'id':'fromAddress', 'type':'string', 'mode':'w'},
        {'id':'smtpAuth', 'type':'string', 'mode':'w'},
        {'id':'popHost', 'type':'string', 'mode':'w'},
        {'id':'popPort', 'type':'int', 'mode':'w'},
        {'id':'popUsername', 'type':'string', 'mode':'w'},
        {'id':'popPassword', 'type':'string', 'mode':'w'},
        {'id':'popAuth', 'type':'string', 'mode':'w'},
        {'id':'popAllowInsecureLogin', 'type':'boolean', 'mode':'w'},
        {'id':'cycleTime', 'type':'int', 'mode':'w'},
        {'id':'timeout', 'type':'int', 'mode':'w'},
        {'id':'messageBody', 'type':'string', 'mode':'w'},
    )


    def __init__(self, id, title=None, buildRelations=True):
        super(MailTxPythonDataSource, self).__init__(id, title, buildRelations)

        #when being copied the relation attributes won't appear till later
        if hasattr(self, 'datapoints'):
            dpIds = [x.id for x in self.datapoints()]
            for dp in ('totalTime', 'fetchTime', 'sendTime'):
                if not dp in dpIds:
                    self.manage_addRRDDataPoint(dp)

    # TODO: add "test" button to datasource
    # def testDataSourceAgainstDevice(self, testDevice, REQUEST, write, errorLog):
    #     """
    #     Does the majority of the logic for testing a datasource against the device
    #     @param string testDevice The id of the device we are testing
    #     @param Dict REQUEST the browers request
    #     @param Function write The output method we are using to stream the result of the command
    #     @parma Function errorLog The output method we are using to report errors
    #     """

    #     # Render
    #     # Determine which device to execute against
    #     device = None
    #     if testDevice:
    #         # Try to get specified device
    #         device = self.findDevice(testDevice)
    #         if not device:
    #              errorLog('Error', 'Cannot find device matching %s' % testDevice)
    #              return 
    #     elif hasattr(self, 'device'):
    #         # ds defined on a device, use that device
    #         device = self.device()
    #     elif hasattr(self, 'getSubDevicesGen'):
    #         # ds defined on a device class, use any device from the class
    #         try:
    #             device = self.getSubDevicesGen().next()
    #         except StopIteration:
    #             # No devices in this class, bail out
    #             pass
    #     if not device:
    #         errorLog('Error', 'Cannot determine a device to test against.')
    #         return 
    #     start = time.time()
    #     try:
    #         self.doMailTx(device.id, write)
    #     except:
    #         write('exception while executing mail transaction')
    #         write('type: %s  value: %s' % tuple(sys.exc_info()[:2]))
    #         from StringIO import StringIO
    #         import traceback
    #         s = StringIO()
    #         traceback.print_exc(file=s)
    #         write(s.getvalue())
    #         write('type: %s  value: %s' % tuple(sys.exc_info()[:2]))
    #     write('')
    #     write('DONE in %s seconds' % long(time.time() - start))
    #     
    # security.declareProtected('Change Device', 'manage_testDataSource')
    # def manage_testDataSource(self, testDevice, REQUEST):
    #     """ Test the datasource by executing the command and outputting the
    #     non-quiet results.
    #     """
    #     out = REQUEST.RESPONSE
    #     def write(lines):
    #         """ Output (maybe partial) result text.
    #         """
    #         # Looks like firefox renders progressive output more smoothly
    #         # if each line is stuck into a table row.  
    #         startLine = '<tr><td class="tablevalues">'
    #         endLine = '&nbsp;</td></tr>\n'
    #         if out:
    #             if not isinstance(lines, list):
    #                 lines = [lines]
    #             for l in lines:
    #                 if not isinstance(l, str):
    #                     l = str(l)
    #                 l = l.strip()
    #                 l = cgi.escape(l)
    #                 l = l.replace('\n', endLine + startLine)
    #                 out.write(startLine + l + endLine)
    #     errorLog = messaging.IMessageSender(self).sendToBrowser
    #     self.testDataSourceAgainstDevice(testDevice, REQUEST, write, errorLog)

    # def doMailTx(self, device, write):
    #     """ Test the MAILTX data source
    #     """
    #     import ZenPacks.zenoss.ZenMailTx
    #     # run the command in a separate process
    #     cmd = '%s %s/Mail.py -d "%s" -s "%s"' % (
    #         "$ZENHOME/bin/python", ZenPacks.zenoss.ZenMailTx.zpDir, device, self.id)
    #     executeStreamCommand(cmd, write)


class IMailTxPythonDataSourceInfo(IRRDDataSourceInfo):
    """Interface that creates the web form for this data source type."""

    toAddress = schema.TextLine(title=_t('To address'), group=_t('Email'))
    fromAddress = schema.TextLine(title=_t('From address'), group=_t('Email'))
    messageBody = schema.Text(title=_t('Message body'), group=_t('Email'))

    cycleTime = schema.Int(title=_t('Cycle time'))
    timeout = schema.Int(title=_t('Timeout'))

    smtpHost = schema.TextLine(title=_t('SMTP host'), group=_t('SMTP'))
    smtpPort = schema.TextLine(title=_t('SMTP port'), group=_t('SMTP'))
    smtpUsername = schema.TextLine(title=_t('SMTP username'), group=_t('SMTP'))
    smtpPassword = schema.Password(title=_t('SMTP password'), group=_t('SMTP'))
    smtpAuth = schema.Choice(
        title=_t('SMTP auth'),
        group=_t('SMTP'),
        vocabulary=SimpleVocabulary.fromValues(MailTxPythonDataSource.AuthModes)
    )

    popHost = schema.TextLine(title=_t('POP host'), group=_t('POP'))
    popPort = schema.TextLine(title=_t('POP port'), group=_t('POP'))
    popUsername = schema.TextLine(title=_t('POP username'), group=_t('POP'))
    popPassword = schema.Password(title=_t('POP password'), group=_t('POP'))
    popAuth = schema.Choice(
        title=_t('POP auth'),
        group=_t('POP'),
        vocabulary=SimpleVocabulary.fromValues(MailTxPythonDataSource.AuthModes)
    )
    popAllowInsecureLogin = schema.Bool(title=_t('Allow insecure login'), group=_t('POP'))



class MailTxPythonDataSourceInfo(RRDDataSourceInfo):
    implements(IMailTxPythonDataSourceInfo)
    adapts(MailTxPythonDataSource)

    testable = False

    smtpHost = ProxyProperty('smtpHost')
    smtpPort = ProxyProperty('smtpPort')
    smtpUsername = ProxyProperty('smtpUsername')
    smtpPassword = ProxyProperty('smtpPassword')
    toAddress = ProxyProperty('toAddress')
    fromAddress = ProxyProperty('fromAddress')
    smtpAuth = ProxyProperty('smtpAuth')
    popHost = ProxyProperty('popHost')
    popPort = ProxyProperty('popPort')
    popUsername = ProxyProperty('popUsername')
    popPassword = ProxyProperty('popPassword')
    popAuth = ProxyProperty('popAuth')
    popAllowInsecureLogin = ProxyProperty('popAllowInsecureLogin')
    cycleTime = ProxyProperty('cycleTime')
    timeout = ProxyProperty('timeout')
    messageBody = ProxyProperty('messageBody')

class Config(object):
    ''' Just a container for attributes '''

class MailTxPythonDataSourcePlugin(PythonDataSourcePlugin):
    @defer.inlineCallbacks
    def collect(self, config):
        results = self.new_data()
        datasources = config.datasources
        cfg = Config()
        cfg.__dict__ = datasources[0].params
        cfg.datasource = datasources[0]
        cfg.device = config
        cfg.msgid = None
        cfg.sent = time.time()
        log.debug("Sending message to %s via %s", cfg.toAddress, cfg.smtpHost)

        results['values'][None] = {}
        try:
            res = yield sendMessage(cfg)
            end_sent = time.time()
            results['values'][None]['sendTime'] = (end_sent - cfg.sent, end_sent)
        except Exception as e:
            results['events'].append(smtp_error2event(cfg, e))
            defer.returnValue(results)

        log.debug("Getting message from %s %s", cfg.popHost, cfg.popUsername)
        cfg.ignoreIds = set()
        start_fetch = time.time()
        try:
            res = yield getMessage(cfg, 5)
            now = time.time()
            results['values'][None]['fetchTime'] = (now - start_fetch, now)
            results['values'][None]['totalTime'] = (now - cfg.sent, now)
        except Exception as e:
            results['events'].append(pop_error2event(cfg, e))

        defer.returnValue(results)

    def onResult(self, result, config):
        return result

    @staticmethod
    def params(datasource, context):
        p = {}
        for property in MailTxPythonDataSource._properties:
            attr = property['id']
            p[attr] = datasource.talesEval(getattr(datasource, attr), context)
            if property['type'] == 'int':
                p[attr] = int(p[attr])
        return p


def smtp_error2event(config, failure):
    dsdev = str(config.device)
    ds = config.datasource.datasource
    msg = str(failure)
    if isinstance(failure, error.ConnectionRefusedError):
        summary = "Connection refused for %s/%s SMTP server %s" % (
                  dsdev, ds, config.smtpHost)

    elif isinstance(failure, error.TimeoutError):
        summary = "Timed out while sending message for %s/%s" % (
                  dsdev, ds)

    elif isinstance(failure, error.DNSLookupError):
        summary = "Unable to resolve SMTP server %s for %s/%s" % (
                  config.smtpHost, dsdev, ds)

    elif isinstance(failure, AUTHDeclinedError):
        summary = "Authentication declined for SMTP server %s for %s/%s" % (
                   config.smtpHost, dsdev, ds)

    elif isinstance(failure, ServerErrorResponse):
        summary = "Received error '%s' while sending message for %s/%s" % (
                   failure, dsdev, ds)
    else:
        summary = "Unknown exception in zenmailtx during SMTP transaction"
        msg = traceback.format_exc()

    log.error(msg)
    return dict(
        device=dsdev,
        severity=config.severity,
        summary=summary,
        message=msg,
        dataSource=ds,
        eventClass=config.eventClass,
        smtpHost=config.smtpHost,
        smtpUsername=config.smtpUsername,
        fromAddress=config.fromAddress,
        toAddress=config.toAddress,
        smtpAuth=config.smtpAuth,
        eventKey=config.eventKey
    )


def pop_error2event(cfg, failure):
    cfg.msgid = None
    dsdev = str(cfg.device)
    ds = cfg.datasource.datasource
    msg = str(failure)
    if isinstance(failure, error.ConnectionRefusedError):
        summary = "Connection refused for %s/%s POP server %s" % (
                  dsdev, ds, cfg.popHost)

    elif isinstance(failure, error.TimeoutError):
        summary = "Timed out while receiving message for %s/%s" % (
                  dsdev, ds)

    elif isinstance(failure, error.DNSLookupError):
        summary = "Unable to resolve POP server %s for %s/%s" % (
                  cfg.popHost, dsdev, ds)

    elif isinstance(failure, ServerErrorResponse):
        summary = "Received error '%s' while receiving message for %s/%s" % (
                   failure, dsdev, ds)

    else:
        summary = "Unknown exception in zenmailtx during POP transaction"
        msg = traceback.format_exc()

    log.error(msg)

    return dict(
        device=dsdev,
        severity=cfg.severity,
        summary=summary,
        message=msg,
        dataSource=ds,
        eventClass=cfg.eventClass,
        popHost=cfg.popHost,
        popUsername=cfg.popUsername,
        popAllowInsecureLogin=cfg.popAllowInsecureLogin,
        popAuth=cfg.popAuth,
        eventKey=cfg.eventKey,
    )
