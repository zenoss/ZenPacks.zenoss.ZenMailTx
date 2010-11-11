######################################################################
#
# Copyright 2007, 2010 Zenoss, Inc.  All Rights Reserved.
#
######################################################################
__doc__ = """MailTxConfigService.py
Carries the config from ZenHub over to the zenmailtx collector
"""

import logging
log = logging.getLogger('zen.services.MailTxConfigService')

import Globals

from twisted.spread import pb

from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenUtils.ZenTales import talesEval

Status_Mail = '/App/Email/Loop'


class RRDConfig(pb.Copyable, pb.RemoteCopy):
    def __init__(self, dp):
        self.command = dp.createCmd
        self.min = dp.rrdmin
        self.max = dp.rrdmax

pb.setUnjellyableForClass(RRDConfig, RRDConfig)
    

class Config(pb.Copyable, pb.RemoteCopy):
    "Carries the config from ZenHub over to the zenmailtx collector"

    sent = 0.0
    msgid = None
    popAllowInsecureLogin = False

    def __init__(self, device, template, datasource):
        self.device = device.id
        self.name = datasource.id
        self.copyProperties(device, datasource)
        self.rrdConfig = {}
        for dp in datasource.datapoints():
            self.rrdConfig[dp.name()] = RRDConfig(dp)
        self.thresholds = []
        for thresh in template.thresholds():
            self.thresholds.append(thresh.createThresholdInstance(device))

    def copyProperties(self, device, ds):
        for prop in [p['id'] for p in ds._properties]:
            value = getattr(ds, prop)
            if str(value).find('$') >= 0:
                value = talesEval('string:%s' % (value,), device)
            setattr(self, prop, value)

    def key(self):
        return self.device, self.name

    def update(self, value):
        self.__dict__.update(value.__dict__)

    def completedOneAttempt(self):
        return self.sent > 0 and self.msgid == None

    def hasMessageOutstanding(self):
        return self.msgid

    def nextRun(self):
        if self.msgid:
            # there's a message out there already
            return self.sent + max(self.timeout, self.cycletime)
        else:
            return self.sent + self.cycletime

pb.setUnjellyableForClass(Config, Config)


class MailTxConfigService(CollectorConfigService):
    """
    ZenHub service for getting ZenMailTx configuration
    from the object database
    """

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)
        proxy.datasources = []

        for template in device.getRRDTemplates():
            for ds in template.getRRDDataSources():
                if ds.sourcetype == 'MAILTX' and \
                   self._checkMailTxDs(device.id, template, ds):
                    proxy.datasources.append(Config(device, template, ds))

        if proxy.datasources:
            return proxy

    def _checkMailTxDs(self, device, template, ds):
        if not ds.enabled:
            return False

        requiredFields = ('smtpHost', 'toAddress', 'fromAddress',
                          'popHost', 'popUsername', 'popPassword',)
        if not self._checkReqFields(device, template, ds, requiredFields):
            return False

        if ds.smtpAuth is not 'None':
            authFields = ('smtpUsername', 'smtpPassword')
            if not self._checkReqFields(device, template, ds, authFields):
                return False

        return True

    def _checkReqFields(self, device, template, ds, requiredFields):
        missing = [field for field in requiredFields if not getattr(ds, field)]
        if missing:
            log.warn("The following required fields are missing from the %s MAILTX ds %s %s: %s",
                     device, template.id, ds.id, sorted(missing))
            return False
        return True

    def remote_getStatus(self):
        """Return devices with Mail problems."""
        where = "eventClass = '%s'" % Status_Mail
        issues = self.zem.getDeviceIssues(where=where, severity=3)
        return [d
                for d, count, total in issues
                if getattr(self.config.devices, d, None)]

if __name__ == '__main__':
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    dmd = ZCmdBase().dmd
    configService = MailTxConfigService(dmd, 'localhost')
    print "Devices with mail issues = %s" % configService.remote_getStatus()
    devices = sorted([x.id for x in configService.remote_getDeviceConfigs()])
    print "MAILTX Devices = %s" % devices
