######################################################################
#
# Copyright 2007 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import Globals

from Products.ZenHub.services.PerformanceConfig import PerformanceConfig

Status_Mail = '/App/Email/Loop'

from Products.ZenUtils.ZenTales import talesEval


from twisted.spread import pb
class RRDConfig(pb.Copyable, pb.RemoteCopy):
    def __init__(self, dp):
        self.command = dp.createCmd
        self.min = dp.rrdmin
        self.max = dp.rrdmax

pb.setUnjellyableForClass(RRDConfig, RRDConfig)
    

class Config(pb.Copyable, pb.RemoteCopy):
    "Carries the config from ZenHub over to the ZenWinTrip collector"

    sent = 0.
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


class ConfigService(PerformanceConfig):
    """ZenHub service for getting ZenMailTx configuration
    from the object database"""

    def getDeviceConfig(self, device):
        result = []
        for template in device.getRRDTemplates():
            for ds in template.getRRDDataSources():
                if ds.sourcetype == 'MAILTX' and ds.enabled:
                    result.append(Config(device, template, ds))
        return result


    def sendDeviceConfig(self, listener, config):
        return listener.callRemote('updateDeviceConfig', config)


    def remote_getConfig(self):
        result = []
        for d in self.config.devices():
            result.extend(self.getDeviceConfig(d.primaryAq()))
        return result


    def remote_getStatus(self):
        """Return devices with Mail problems."""
        where = "eventClass = '%s'" % (Status_Mail)
        issues = self.zem.getDeviceIssues(where=where, severity=3)
        return [d
                for d, count, total in issues
                if getattr(self.config.devices, d, None)]

if __name__ == '__main__':
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    dmd = ZCmdBase().dmd
    c = ConfigService(dmd, 'localhost')
    print c.remote_getStatus()
    print c.remote_getConfig()
