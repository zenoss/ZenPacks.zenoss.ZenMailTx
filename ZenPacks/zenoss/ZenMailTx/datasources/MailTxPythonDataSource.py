##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='''
Defines datasource for ZenMailTx round-trip mail testing using Python Collector
Part of ZenMailTx zenpack.
'''

from zope.component import adapts
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from twisted.internet import defer

from Products.Zuul.form import schema
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.template import RRDDataSourceInfo
from Products.Zuul.interfaces import IRRDDataSourceInfo
from Products.Zuul.utils import ZuulMessageFactory as _t

from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource \
    import PythonDataSource, PythonDataSourcePlugin


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
        {'id':'popPort', 'type':'string', 'mode':'w'},
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
        if getattr(self, 'datapoints', None) is not None:
            dpIds = map(lambda x: x.id, self.datapoints())
            for dp in ('totalTime', 'fetchTime', 'sendTime'):
                if not dp in dpIds:
                    self.manage_addRRDDataPoint(dp)


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


class MailTxPythonDataSourcePlugin(PythonDataSourcePlugin):
    @defer.inlineCallbacks
    def collect(self, config):
        results = self.new_data()
        yield
        defer.returnValue(results)
