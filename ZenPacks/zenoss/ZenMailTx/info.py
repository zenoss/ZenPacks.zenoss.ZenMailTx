######################################################################
#
# Copyright 2010 Zenoss, Inc.  All Rights Reserved.
#
######################################################################
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.template import RRDDataSourceInfo
from ZenPacks.zenoss.ZenMailTx.interfaces import IMailTxDataSourceInfo
from ZenPacks.zenoss.ZenMailTx.datasources.MailTxDataSource import MailTxDataSource

def transportSecurityVocabulary(context):
    """
    The vocabulary used for the Transport Security Drop Down. 
    """
    return SimpleVocabulary.fromValues(MailTxDataSource.AuthModes)

class MailTxDataSourceInfo(RRDDataSourceInfo):
    implements(IMailTxDataSourceInfo)
    cycleTime = ProxyProperty('cycleTime')
    timeout = ProxyProperty('timeout')
    toAddress = ProxyProperty('toAddress')
    fromAddress = ProxyProperty('fromAddress')
    
    # SMTP fields
    smtpHost = ProxyProperty('smtpHost')
    smtpPort = ProxyProperty('smtpPort')
    smtpUsername = ProxyProperty('smtpUsername')
    smtpPassword = ProxyProperty('smtpPassword')
    smtpAuth = ProxyProperty('smtpAuth')

    # POP fields
    popHost = ProxyProperty('popHost')
    popPort = ProxyProperty('popPort')
    popUsername = ProxyProperty('popUsername')
    popPassword = ProxyProperty('popPassword')
    popAuth = ProxyProperty('popAuth')
    popAllowInsecureLogin = ProxyProperty('popAllowInsecureLogin')
    messageBody = ProxyProperty('messageBody')

    @property
    def testable(self):
        """
        Denotes that this datasource is testable from the UI
        """
        return True
