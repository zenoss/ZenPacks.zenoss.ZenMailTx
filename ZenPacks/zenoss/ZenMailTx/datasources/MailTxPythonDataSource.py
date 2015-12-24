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

    smtpHost = schema.TextLine(title=_t('SMTP Host'))
    smtpPort = schema.TextLine(title=_t('SMTP Port'))
    # TODO:
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
