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
    messageBody = schema.TextLine(title=_t('Message Body'))
    
    # SMTP fields
    smtpHost = schema.Text(title=_t('SMTP Host'), group=_t('SMTP'))
    smtpPort = schema.Int(title=_t('SMTP Port'), group=_t('SMTP'))
    smtpUsername = schema.Text(title=_t('SMTP Username'), group=_t('SMTP'))
    smtpPassword = schema.Password(title=_t('SMTP Password'), group=_t('SMTP'))
    smtpAuth = schema.Choice(title=_t('Transport Security'),
                           vocabulary="transportSecurity",
                           group=_t('SMTP'))

    # POP fields
    popHost = schema.Text(title=_t('POP Host'), group=_t('POP'))
    popPort = schema.Int(title=_t('POP Port'), group=_t('POP'))
    popUsername = schema.Text(title=_t('POP Username'), group=_t('POP'))
    popPassword = schema.Password(title=_t('POP Password'), group=_t('POP'))
    popAuth = schema.Choice(title=_t('Transport Security'),
                          vocabulary="transportSecurity",
                          group=_t('POP'))
    popAllowInsecureLogin = schema.Bool(title=_t('Allow Insecure Logins?'), group=_t('POP'))

    
