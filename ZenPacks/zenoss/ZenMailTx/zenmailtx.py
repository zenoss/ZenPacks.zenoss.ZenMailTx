######################################################################
#
# Copyright 2007 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

__doc__ = '''zenmailtx

Test round-trip email delivery time.

Send a message using SMTP, fetch it back using POP.
Post the times, generate events on errors.

'''

import os

import Globals
import ZenPacks.zenoss.ZenMailTx as ZenMailTx
from Products.ZenRRD.RRDDaemon import RRDDaemon
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenUtils.Driver import drive
from Products.ZenRRD.Thresholds import Thresholds
from Products.ZenModel.RRDDataPoint import SEPARATOR

from twisted.python import failure
from twisted.internet import defer, reactor

import time
from sets import Set

import Mail

# do not delete this: it is needed for pb/jelly
from ZenPacks.zenoss.ZenMailTx.ConfigService import Config

try:
    sorted
except NameError:
    def sorted(seq, comp=cmp):
        result = list(seq)
        result.sort(comp)
        return result

DEFAULT_HEARTBEAT_TIME = 500

Base = RRDDaemon
class zenmailtx(Base):
    initialServices = Base.initialServices + [
        'ZenPacks.zenoss.ZenMailTx.ConfigService'
        ]


    def __init__(self):
        Base.__init__(self, 'zenmailtx')
        self.firstRun = defer.Deferred()
        self.config = []
        self.clearables = Set()
        self.thresholds = Thresholds()


    def remote_deleteDevice(self, doomed):
        self.log.debug("Async delete device %s" % doomed)


    def remote_updateDeviceConfig(self, config):
        self.log.debug("Async device update")
        self.updateConfig(config)


    def updateConfig(self, config):
        orig = {}
        for obj in self.config:
            orig[obj.key()] = obj
        for obj in config:
            old = orig.get(obj.key(), None)
            if old is None:
                obj.ignoreIds = Set()
                self.config.append(obj)
            else:
                old.update(obj)
            self.thresholds.updateList(obj.thresholds)


    def updateStatus(self, status):
        self.log.debug("Status %r", status)
        self.clearables = Set(status)


    def processSchedule(self, result = None):
        if isinstance(result, failure.Failure):
            if not isinstance(result.value, error.TimeoutError):
                self.log.error(str(result.value))

        def compare(a, b):
            return cmp(a.nextRun(), b.nextRun())
        schedule = sorted(self.config, compare)
        if len([s for s in schedule if not s.completedOneAttempt()]) == 0:
            # everything has executed at least once: tell someone
            if not self.firstRun.called:
                self.firstRun.callback(None)
        outstanding = len([c for c in schedule if c.hasMessageOutstanding()])
        now = time.time()
        for cfg in schedule:
            if outstanding >= self.options.parallel:
                break
            if cfg.nextRun() <= now:
                outstanding += 1
                def sendReceive(driver):
                    cfg.sent = time.time()
                    yield Mail.SendMessage(cfg)
                    driver.next()
                    endSend = time.time()
                    yield Mail.GetMessage(cfg, self.options.pollingcycle)
                    driver.next()
                    endFetch = time.time()
                    fetchTime = endFetch - endSend
                    self.postResults(cfg,
                                     endFetch - cfg.sent,
                                     endSend - cfg.sent,
                                     endFetch - endSend)
                d = drive(sendReceive)
                def resetId(arg):
                    cfg.msgid = None
                    return arg
                d.addBoth(resetId)
                d.addBoth(self.processSchedule)
        if schedule:
            earliest = schedule[0].nextRun()
            if earliest > now:
                reactor.callLater(earliest - now, self.processSchedule)
        return self.firstRun


    def postResults(self, cfg, totalTime, sendTime, fetchTime):
        self.log.info("Device %s cycle time %0.2f (sent %0.2f, fetch %0.2f)",
                      cfg.device, totalTime, sendTime, fetchTime)
        for name in ('totalTime', 'sendTime', 'fetchTime'):
            dpName = '%s%c%s' % (cfg.name, SEPARATOR, name)
            rrdConfig = cfg.rrdConfig[dpName]
            path = os.path.join('Devices', cfg.device, dpName)
            value = self.rrd.save(path, locals()[name], 'GAUGE',
                                  rrdConfig.command, cfg.cycleTime,
                                  rrdConfig.min, rrdConfig.max)
            for evt in self.thresholds.check(path, time.time(), value):
                self.sendThresholdEvent(**evt)


    def fetchInitialConfigAndScan(self, driver):
        now = time.time()
        self.log.info("fetching default RRDCreateCommand")
        yield self.model().callRemote('getDefaultRRDCreateCommand')
        createCommand = driver.next()
        self.rrd = RRDUtil(createCommand, DEFAULT_HEARTBEAT_TIME)
        self.log.info("Getting Threshold Classes")
        yield self.model().callRemote('getThresholdClasses')
        self.remote_updateThresholdClasses(driver.next())
        self.log.info("Loading Config")
        yield self.model().callRemote('getConfig')
        self.updateConfig(driver.next())
        self.log.info("Getting current status")
        yield self.model().callRemote('getStatus')
        self.updateStatus(driver.next())
        self.log.info("Starting mail tests")
        yield self.processSchedule()
        driver.next()
        self.log.info("Processed %d mail round trips in %s seconds",
                      len(self.config),
                      time.time() - now)


    def heartbeat(self, *unused):
        Base.heartbeat(self)
        reactor.callLater(self.heartbeatTimeout / 3, self.heartbeat)

        
    def connected(self):
        Base.heartbeat(self)
        d = drive(self.fetchInitialConfigAndScan)
        d.addCallbacks(self.heartbeat, self.errorStop)


    def buildOptions(self):
        Base.buildOptions(self)
        self.parser.add_option('--parallel',
                               dest='parallel',
                               default=100,
                               help="Maximum number of outstanding checks")
        self.parser.add_option('--pollingcycle',
                               dest='pollingcycle',
                               default=5,
                               help="Time between POP polls")

if __name__ == '__main__':
    zmt = zenmailtx()
    zmt.run()
