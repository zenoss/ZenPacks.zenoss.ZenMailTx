######################################################################
#
# Copyright 2009 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

__doc__ = '''zenmailtx

Test round-trip email delivery time.

Send a message using SMTP, fetch it back using POP.
Post the times, generate events on errors.

Configuration of this daemon is through a datasource that is attached
to a device.
'''

import os
import time
import traceback
from sets import Set

import Mail

import Globals
import ZenPacks.zenoss.ZenMailTx as ZenMailTx
from Products.ZenRRD.RRDDaemon import RRDDaemon
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenUtils.Driver import drive
from Products.ZenRRD.Thresholds import Thresholds
from Products.ZenModel.RRDDataPoint import SEPARATOR
from Products.ZenEvents import Event

from twisted.python import failure
from twisted.internet import defer, reactor, error
from twisted.mail.pop3 import ServerErrorResponse
from twisted.mail.smtp import AUTHDeclinedError, SMTPClientError

# do not delete this: it is needed for pb/jelly
from ZenPacks.zenoss.ZenMailTx.ConfigService import Config

mailEventClass = '/Status'

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
        self.thresholds = Thresholds()


    def remote_deleteDevice(self, doomed):
        self.log.debug("zenhub requested us to delete"
                       " device %s -- ignoring" % doomed)


    def remote_updateDeviceConfig(self, config):
        self.log.debug("Configuration device update from zenhub")
        self.updateConfig(config)


    def updateConfig(self, newconfig):
        if isinstance(newconfig, failure.Failure):
            self.log.error("Received configuration failure (%s) from zenhub" % (
                           str(newconfig)))
            return
        self.log.debug("Received %d configuration updates from zenhub" % (
                       len(newconfig)))
        orig = {}
        for obj in self.config:
            orig[obj.key()] = obj

        for obj in newconfig:
            deviceName = obj.key()[0]
            if hasattr(self.options, 'device') and \
               self.options.device != '' and \
               self.options.device != deviceName:
                self.log.debug("Skipping update for %s as we're" \
                               " only looking for %s updates" % (
                               deviceName, self.options.device))
                continue

            self.log.debug("Configuration object for %s/%s found" % obj.key())
            old = orig.get(obj.key(), None)
            if old is None:
                obj.ignoreIds = Set()
                self.config.append(obj)
            else:
                old.update(obj)
            self.thresholds.updateList(obj.thresholds)


    def handleSmtpError(self, cfg, ex):
        cfg.msgid = None
        dsdev, ds = cfg.key()
        msg = str(ex)
        if isinstance(ex, error.ConnectionRefusedError):
            summary = "Connection refused for %s/%s SMTP server %s" % (
                      dsdev, ds, cfg.smtpHost)

        elif isinstance(ex, error.TimeoutError):
            summary = "Timed out while sending message for %s/%s" % (
                      dsdev, ds)

        elif isinstance(ex, error.DNSLookupError):
            summary = "Unable to resolve SMTP server %s for %s/%s" % (
                      cfg.smtpHost, dsdev, ds)

        elif isinstance(ex, AUTHDeclinedError):
            summary = "Authentication declined for SMTP server %s for %s/%s" % (
                       cfg.smtpHost, dsdev, ds)

        elif isinstance(ex, ServerErrorResponse):
            summary = "Received error '%s' while sending message for %s/%s" % (
                       ex, dsdev, ds)
        else:
            summary = "Unknown exception in zenmailtx during SMTP transaction"
            msg = '%s' % traceback.format_exc()

        self.log.error(msg)
        errorEvent = dict( device=cfg.device, component='zenmailtx',
            dedupid='%s|%s|%s|%s' % (dsdev, ds, cfg.smtpHost, cfg.popHost),
            severity=Event.Error, summary=summary, message=msg,
            eventGroup="mail", dataSource=ds, eventClass=mailEventClass,
            smtpHost=cfg.smtpHost, smtpUsername=cfg.smtpUsername,
            fromAddress=cfg.fromAddress, toAddress=cfg.toAddress,
            smtpAuth=cfg.smtpAuth,
        )
        self.sendEvent(errorEvent)


    def handlePopError(self, cfg, ex):
        cfg.msgid = None
        dsdev, ds = cfg.key()
        msg = str(ex)
        if isinstance(ex, error.ConnectionRefusedError):
            summary = "Connection refused for %s/%s POP server %s" % (
                      dsdev, ds, cfg.popHost)

        elif isinstance(ex, error.TimeoutError):
            summary = "Timed out while receiving message for %s/%s" % (
                      dsdev, ds)

        elif isinstance(ex, error.DNSLookupError):
            summary = "Unable to resolve POP server %s for %s/%s" % (
                      cfg.popHost, dsdev, ds)

        elif isinstance(ex, ServerErrorResponse):
            summary = "Received error '%s' while receiving message for %s/%s" % (
                       ex, dsdev, ds)

        else:
            summary = "Unknown exception in zenmailtx during POP transaction"
            msg = traceback.format_exc()

        self.log.error(msg)
        errorEvent = dict( device=cfg.device, component='zenmailtx',
            dedupid='%s|%s|%s|%s' % (dsdev, ds, cfg.smtpHost, cfg.popHost),
            severity=Event.Error, summary=summary, message=msg,
            eventGroup="mail", dataSource=ds, eventClass=mailEventClass,
            popHost=cfg.popHost, popUsername=cfg.popUsername,
            popAllowInsecureLogin=cfg.popAllowInsecureLogin,
            popAuth=cfg.popAuth,
        )
        self.sendEvent(errorEvent)


    def processSchedule(self, result = None):
        if isinstance(result, failure.Failure):
            if not isinstance(result.value, error.TimeoutError):
                self.log.error(str(result.value))

        def compare(a, b):
            return cmp(a.nextRun(), b.nextRun())

        schedule = sorted(self.config, compare)
        self.log.info("Scheduling %d runs" % len(schedule))
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
                def inner(driver):
                    try:
                        cfg.sent = time.time()
                        self.log.debug("Sending message to %s", cfg.device)
                        yield Mail.SendMessage(cfg)
                        driver.next()
                        endSend = time.time()

                    except (SystemExit, KeyboardInterrupt):
                        raise
                    except Exception, ex:
                        self.handleSmtpError(cfg, ex)
                        raise

                    try:
                        self.log.debug("Getting message from %s", cfg.popHost)
                        yield Mail.GetMessage(cfg, self.options.pollingcycle)
                        driver.next()
                    except (SystemExit, KeyboardInterrupt):
                        raise
                    except Exception, ex:
                        self.handlePopError(cfg, ex)
                        raise

                    try:
                        endFetch = time.time()
                        fetchTime = endFetch - endSend
                        self.log.debug("Total trip time to/from %s: %.1fs",
                                       cfg.device, endFetch - cfg.sent)
                        self.postResults(cfg,
                                         endFetch - cfg.sent,
                                         endSend - cfg.sent,
                                         endFetch - endSend)
                        cfg.msgid = None
                    except Exception, ex:
                        cfg.msgid = None
                        self.log.exception(ex)
                        dsdev, ds = cfg.key()
                        self.sendEvent(dict(
                          device=cfg.device, component='zenmailtx', severity=Event.Error,
                          dedupid='%s|%s|%s|%s' % (dsdev, ds, cfg.smtpHost, cfg.popHost),
                          summary="Unknown exception in zenmailtx while writing results",
                          message=traceback.format_exc(),
                          eventGroup="mail", dataSource=ds, eventClass=mailEventClass,
                        ))
                        raise

                d = drive(inner)
                d.addBoth(self.processSchedule)

        if schedule:
            earliest = schedule[0].nextRun()
            if earliest > now:
                reactor.callLater(earliest - now, self.processSchedule)


    def postResults(self, cfg, totalTime, sendTime, fetchTime):
        msg = "Device %s cycle time %0.2fs (sent %0.2fs, fetch %0.2fs)" % (
                      cfg.device, totalTime, sendTime, fetchTime)
        self.log.info(msg)
        for name in ('totalTime', 'sendTime', 'fetchTime'):
            dpName = '%s%c%s' % (cfg.name, SEPARATOR, name)
            rrdConfig = cfg.rrdConfig[dpName]
            path = os.path.join('Devices', cfg.device, dpName)
            value = self.rrd.save(path, locals()[name], 'GAUGE',
                                  rrdConfig.command, cfg.cycleTime,
                                  rrdConfig.min, rrdConfig.max)

            for evt in self.thresholds.check(path, time.time(), value):
                self.sendThresholdEvent(**evt)

        dsdev, ds = cfg.key()
        self.sendEvent(dict(
            device=cfg.device, component='zenmailtx', severity=Event.Clear,
            dedupid='%s|%s|%s|%s' % (dsdev, ds, cfg.smtpHost, cfg.popHost),
            summary="Successfully completed transaction",
            message=msg,
            eventGroup="mail", dataSource=ds, eventClass=mailEventClass,
        ))


    def heartbeat(self, *unused):
        Base.heartbeat(self)
        reactor.callLater(self.heartbeatTimeout / 3, self.heartbeat)


    def connected(self):
        self.log.debug("Gathering information from zenhub")
        Base.heartbeat(self)
        def inner(driver):
            try:
                now = time.time()
                self.log.info("Fetching default RRDCreateCommand")
                yield self.model().callRemote('getDefaultRRDCreateCommand')
                createCommand = driver.next()
                self.rrd = RRDUtil(createCommand, DEFAULT_HEARTBEAT_TIME)
                self.log.info("Getting Threshold Classes")
                yield self.model().callRemote('getThresholdClasses')
                self.remote_updateThresholdClasses(driver.next())
                self.log.info("Retrieving configuration from zenhub...")
                yield self.model().callRemote('getConfig')
                self.updateConfig(driver.next())
                self.log.info("Starting mail tests")
                self.processSchedule()
                yield self.firstRun
                driver.next()
                self.log.info("Processed %d mail round-trips in %0.2f seconds",
                              len(self.config),
                              time.time() - now)
            except Exception, ex:
                self.log.exception(ex)
                raise
        d = drive(inner)
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
