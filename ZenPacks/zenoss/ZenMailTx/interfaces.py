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
from Products.Zuul.interfaces import IRRDDataSourceInfo
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t


class IMailTxDataSourceInfo(IRRDDataSourceInfo):
    timeout = schema.Int(title=_t(u"Timeout (seconds)"))
    component = schema.Text(title=_t(u"Component"))
    eventKey = schema.Text(title=_t(u"Event Key"))
    toAddress = schema.Text(title=_t(u"To Address"))
    fromAddress = schema.Text(title=_t(u"From Address"))
    messageBody = schema.TextLine(title=_t(u'Message Body'), xtype="twocolumntextarea")
    
    # SMTP fields
    smtpHost = schema.Text(title=_t(u'SMTP Host'), group=_t(u'SMTP'))
    smtpPort = schema.Int(title=_t(u'SMTP Port'), group=_t(u'SMTP'))
    smtpUsername = schema.Text(title=_t(u'SMTP Username'), group=_t(u'SMTP'))
    smtpPassword = schema.Password(title=_t(u'SMTP Password'), group=_t(u'SMTP'))
    smtpAuth = schema.Choice(title=_t(u'Transport Security'),
                           vocabulary="transportSecurity",
                           group=_t(u'SMTP'))

    # POP fields
    popHost = schema.Text(title=_t(u'POP Host'), group=_t(u'POP'))
    popPort = schema.Int(title=_t(u'POP Port'), group=_t(u'POP'))
    popUsername = schema.Text(title=_t(u'POP Username'), group=_t(u'POP'))
    popPassword = schema.Password(title=_t(u'POP Password'), group=_t(u'POP'))
    popAuth = schema.Choice(title=_t(u'Transport Security'),
                          vocabulary="transportSecurity",
                          group=_t(u'POP'))
    popAllowInsecureLogin = schema.Bool(title=_t(u'Allow Insecure Logins?'), group=_t(u'POP'))

    
