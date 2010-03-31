###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
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

