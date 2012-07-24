##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.Zuul.interfaces import IRRDDataSourceInfo
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t


class IMailTxDataSourceInfo(IRRDDataSourceInfo):
    cycleTime = schema.Int(title=_t(u'Cycle Time (seconds)'))
    timeout = schema.Int(title=_t(u"Timeout (seconds)"))
    toAddress = schema.TextLine(title=_t(u"To Address"))
    fromAddress = schema.TextLine(title=_t(u"From Address"))
    messageBody = schema.TextLine(title=_t(u'Message Body'), xtype="twocolumntextarea")
    
    # SMTP fields
    smtpHost = schema.TextLine(title=_t(u'SMTP Host'), group=_t(u'SMTP'))
    smtpPort = schema.Int(title=_t(u'SMTP Port'), group=_t(u'SMTP'))
    smtpUsername = schema.TextLine(title=_t(u'SMTP Username'), group=_t(u'SMTP'))
    smtpPassword = schema.Password(title=_t(u'SMTP Password'), group=_t(u'SMTP'))
    smtpAuth = schema.Choice(title=_t(u'Transport Security'),
                           vocabulary="transportSecurity",
                           group=_t(u'SMTP'))

    # POP fields
    popHost = schema.TextLine(title=_t(u'POP Host'), group=_t(u'POP'))
    popPort = schema.Int(title=_t(u'POP Port'), group=_t(u'POP'))
    popUsername = schema.TextLine(title=_t(u'POP Username'), group=_t(u'POP'))
    popPassword = schema.Password(title=_t(u'POP Password'), group=_t(u'POP'))
    popAuth = schema.Choice(title=_t(u'Transport Security'),
                          vocabulary="transportSecurity",
                          group=_t(u'POP'))
    popAllowInsecureLogin = schema.Bool(title=_t(u'Allow Insecure Logins?'), group=_t(u'POP'))
