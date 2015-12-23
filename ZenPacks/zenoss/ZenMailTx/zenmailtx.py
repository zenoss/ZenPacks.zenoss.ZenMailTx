##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = '''zenmailtx

Test round-trip email delivery time.

Send a message using SMTP, fetch it back using POP.
Post the times, generate events on errors.

Configuration of this daemon is through a datasource that is attached
to a device.
'''

import os
import time
import logging


from twisted.internet import defer, error
from twisted.mail.pop3 import ServerErrorResponse
from twisted.mail.smtp import AUTHDeclinedError

import Globals
from zope.interface import implements
from zope.component import queryUtility

from  ZenPacks.zenoss.ZenMailTx.Mail import sendMessage, getMessage

from Products.ZenModel.RRDDataPoint import SEPARATOR
from Products.ZenEvents import Event

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
                                             IDataService,\
                                             IEventService,\
                                             IScheduledTask
from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                        SubConfigurationTaskSplitter,\
                                        TaskStates,\
                                        BaseTask

# do not delete this: it is needed for pb/jelly
from Products.ZenUtils.Utils import unused
from ZenPacks.zenoss.ZenMailTx.MailTxConfigService import Config
unused(Config)

COLLECTOR_NAME = "zenmailtx"
log = logging.getLogger("zen.%s" % COLLECTOR_NAME)

MAX_BACK_OFF_MINUTES = 20

mailEventClass = '/Status'


class MailTxCollectionPreferences(object):
    implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new preferences instance and
        provides default values for needed attributes.
        """
        self.collectorName = COLLECTOR_NAME
        self.defaultRRDCreateCommand = None
        self.configCycleInterval = 20 # minutes
        self.cycleInterval = 5 * 60 # seconds

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'ZenPacks.zenoss.ZenMailTx.MailTxConfigService'

        # Provide a reasonable default for the max number of tasks
        self.maxTasks = 50

        # Will be filled in based on buildOptions
        self.options = None

    def buildOptions(self, parser):
        parser.add_option('--pollingcycle',
                          dest='pollingcycle',
                          default=5,
                          help="Time between POP polls")
        parser.add_option('--maxbackoffminutes',
                          dest='maxbackoffminutes',
                          default=MAX_BACK_OFF_MINUTES,
                          type='int',
                          help="When a device fails to respond, increase the time to" \
                               " check on the device until this limit.")

    def postStartup(self):
        pass


class MailTxTaskSplitter(SubConfigurationTaskSplitter):
    subconfigName = 'datasources'
    def makeConfigKey(self, config, subconfig):
        return (config.id, subconfig.cycleTime,
                subconfig.smtpHost, subconfig.toAddress,
                subconfig.popHost, subconfig.popUsername)


class MailTxCollectionTask(BaseTask):
    """
    A task that performs periodic performance collection for devices providing
    data via SNMP agents.
    """
    implements(IScheduledTask)

    STATE_CONNECTING = 'CONNECTING'
    STATE_MAILING = 'MAILING'
    STATE_RECEIVE_POLLING = 'RECEIVE_POLLING'
    STATE_STORE_PERF = 'STORE_PERF_DATA'
    STATE_SEND_STATUS = 'SEND_STATUS_EVENT'

    def __init__(self,
                 taskName,
                 deviceId,
                 scheduleIntervalSeconds,
                 taskConfig):
        """
        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(MailTxCollectionTask, self).__init__(
                 taskName, deviceId, 
                 scheduleIntervalSeconds, taskConfig
               )
        self.name = taskName
        self.configId = deviceId
        self.state = TaskStates.STATE_IDLE

        # The taskConfig corresponds to a DeviceProxy
        self._datasources = taskConfig.datasources
        self._cfg = self._datasources[0]
        self._devId = deviceId
        self.interval = scheduleIntervalSeconds

        self._dataService = queryUtility(IDataService)
        self._eventService = queryUtility(IEventService)

        self._preferences = queryUtility(ICollectorPreferences, COLLECTOR_NAME)

        self._maxbackoffseconds = self._preferences.options.maxbackoffminutes * 60

        self._lastErrorMsg = ''

    def _failure(self, reason):
        """
        Twisted errBack to log the exception for a single device.

        @parameter reason: explanation of the failure
        @type reason: Twisted error instance
        """
        # Decode the exception
        if isinstance(reason.value, error.TimeoutError):
            # Indicate that we've handled the error by
            # not returning a result
            reason = None
            msg = None

        else:
            msg = reason.getErrorMessage()
            if not msg: # Sometimes we get blank error messages
                msg = reason.__class__
            msg = '%s %s' % (self._devId, msg)

            # Leave 'reason' alone to generate a traceback

        if not self._errorHandled:
            if self._lastErrorMsg != msg:
                self._lastErrorMsg = msg
                if msg:
                    log.error(msg)

            self._eventService.sendEvent({},
                                         device=self._devId,
                                         component='zenmailtx',
                                         summary=msg,
                                         severity=Event.Error)

            self._delayNextCheck()
        return reason

    def cleanup(self):
        pass

    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: A task to scan the OIDs on a device.
        @rtype: Twisted deferred object
        """
        # See if we need to connect first before doing any collection
        self._errorHandled = False
        d = defer.maybeDeferred(self._sendMessage)
        d.addErrback(self._handleSmtpError)
        d.addCallback(self._getMessage)
        d.addErrback(self._handlePopError)
        d.addCallback(self._storeResults)
        d.addCallback(self._updateStatus)
        d.addCallback(self._returnToNormalSchedule)
        d.addErrback(self._failure)

        # Wait until the Deferred actually completes
        return d

    def _sendMessage(self):
        self.state = MailTxCollectionTask.STATE_MAILING
        self._cfg.msgid = None
        self._cfg.sent = time.time()
        log.debug("Sending message to %s via %s",
                  self._cfg.toAddress, self._cfg.smtpHost)
        d = sendMessage(self._cfg)
        endSend = time.time()
        self.sendTime = endSend - self._cfg.sent
        return d

    def _handleSmtpError(self, result):
        self._cfg.msgid = None
        dsdev, ds = self._cfg.key()
        failure = result.value
        msg = str(failure)
        if isinstance(failure, error.ConnectionRefusedError):
            summary = "Connection refused for %s/%s SMTP server %s" % (
                      dsdev, ds, self._cfg.smtpHost)

        elif isinstance(failure, error.TimeoutError):
            summary = "Timed out while sending message for %s/%s" % (
                      dsdev, ds)

        elif isinstance(failure, error.DNSLookupError):
            summary = "Unable to resolve SMTP server %s for %s/%s" % (
                      self._cfg.smtpHost, dsdev, ds)

        elif isinstance(failure, AUTHDeclinedError):
            summary = "Authentication declined for SMTP server %s for %s/%s" % (
                       self._cfg.smtpHost, dsdev, ds)

        elif isinstance(failure, ServerErrorResponse):
            summary = "Received error '%s' while sending message for %s/%s" % (
                       failure, dsdev, ds)
        else:
            summary = "Unknown exception in zenmailtx during SMTP transaction"
            msg = result.getTraceback()

        if self._lastErrorMsg != msg:
            self._lastErrorMsg = msg
            if msg:
                log.error(msg)
        errorEvent = dict( device=self._cfg.device, component='zenmailtx',
            dedupid='%s|%s|%s|%s' % (dsdev, ds, self._cfg.smtpHost, self._cfg.popHost),
            severity=self._cfg.severity, summary=summary, message=msg,
            eventGroup="mail", dataSource=ds, eventClass=self._cfg.eventClass,
            smtpHost=self._cfg.smtpHost, smtpUsername=self._cfg.smtpUsername,
            fromAddress=self._cfg.fromAddress, toAddress=self._cfg.toAddress,
            smtpAuth=self._cfg.smtpAuth, eventKey=self._cfg.eventKey
        )
        self._eventService.sendEvent(errorEvent)
        self._delayNextCheck()
        self._errorHandled = True
        return result

    def _getMessage(self, result):
        self.state = MailTxCollectionTask.STATE_RECEIVE_POLLING
        log.debug("Getting message from %s %s",
                  self._cfg.popHost, self._cfg.popUsername)

        self._cfg.ignoreIds = set()
        startFetch = time.time()
        d = getMessage(self._cfg, self._preferences.options.pollingcycle)
        self.fetchTime = time.time() - startFetch
        log.debug("Fetch time from %s: %.1fs",
                  self._cfg.popHost, self.fetchTime)
        return d

    def _handlePopError(self, result):
        if self._errorHandled:
            return result

        self._cfg.msgid = None
        dsdev, ds = self._cfg.key()
        failure = result.value
        msg = str(failure)
        if isinstance(failure, error.ConnectionRefusedError):
            summary = "Connection refused for %s/%s POP server %s" % (
                      dsdev, ds, self._cfg.popHost)

        elif isinstance(failure, error.TimeoutError):
            summary = "Timed out while receiving message for %s/%s" % (
                      dsdev, ds)

        elif isinstance(failure, error.DNSLookupError):
            summary = "Unable to resolve POP server %s for %s/%s" % (
                      self._cfg.popHost, dsdev, ds)

        elif isinstance(failure, ServerErrorResponse):
            summary = "Received error '%s' while receiving message for %s/%s" % (
                       failure, dsdev, ds)

        else:
            summary = "Unknown exception in zenmailtx during POP transaction"
            msg = result.getTraceback()

        if self._lastErrorMsg != msg:
            self._lastErrorMsg = msg
            if msg:
                log.error(msg)

        errorEvent = dict( device=self._cfg.device, component='zenmailtx',
            dedupid='%s|%s|%s|%s' % (dsdev, ds, self._cfg.smtpHost, self._cfg.popHost),
            severity=self._cfg.severity, summary=summary, message=msg,
            eventGroup="mail", dataSource=ds, eventClass=self._cfg.eventClass,
            popHost=self._cfg.popHost, popUsername=self._cfg.popUsername,
            popAllowInsecureLogin=self._cfg.popAllowInsecureLogin,
            popAuth=self._cfg.popAuth, eventKey=self._cfg.eventKey
        )
        self._eventService.sendEvent(errorEvent)
        self._delayNextCheck()
        self._errorHandled = True
        return result

    def _storeResults(self, result):
        """
        Store the datapoint results asked for by the RRD template.
        """
        self.state = MailTxCollectionTask.STATE_STORE_PERF

        self.totalTime = time.time() - self._cfg.sent
        for name in ('totalTime', 'sendTime', 'fetchTime'):
            dpName = '%s%c%s' % (self._cfg.name, SEPARATOR, name)
            rrdConfig = self._cfg.rrdConfig[dpName]
            value = getattr(self, name, None)
            try:
                path = os.path.join('Devices', self._cfg.device)
                self._dataService.writeMetricWithMetadata(
                    dpName,
                    value,
                    'GAUGE',
                    min=rrdConfig.min,
                    max=rrdConfig.max,
                    threshEventData={
                        'eventKey': self._cfg.eventKey,
                        'component'='zenmailtx',
                    },
                )
            except AttributeError: # not a 5.x
                path = os.path.join('Devices', self._cfg.device, dpName)
                self._dataService.writeRRD(
                    path, value, 'GAUGE',
                    rrdCommand=rrdConfig.command,
                    min=rrdConfig.min,
                    max=rrdConfig.max
                )


        return result

    def _updateStatus(self, result):
        self.state = MailTxCollectionTask.STATE_SEND_STATUS
        msg = "Device %s cycle time %0.2fs (sent %0.2fs, fetch %0.2fs)" % (
                      self._cfg.device, self.totalTime, self.sendTime, self.fetchTime)
        dsdev, ds = self._cfg.key()
        self._eventService.sendEvent(dict(
            device=self._cfg.device, component='zenmailtx', severity=Event.Clear,
            dedupid='%s|%s|%s|%s' % (dsdev, ds, self._cfg.smtpHost, self._cfg.popHost),
            summary="Successfully completed transaction",
            message=msg, eventKey=self._cfg.eventKey,
            eventGroup="mail", dataSource=ds, eventClass=self._cfg.eventClass,
        ))
        return msg

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        display = self.name
        if self._lastErrorMsg:
            display += "%s\n" % self._lastErrorMsg
        return display


if __name__ == '__main__':
    myPreferences = MailTxCollectionPreferences()
    myTaskFactory = SimpleTaskFactory(MailTxCollectionTask)
    myTaskSplitter = MailTxTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
