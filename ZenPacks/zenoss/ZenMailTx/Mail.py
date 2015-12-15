##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import time
from StringIO import StringIO
from email import Message, Utils

import logging
log = logging.getLogger('zen.MailTx.Mail')

import sys

ssl = None
try:
    from twisted.internet import ssl
except ImportError:
    import warnings
    warnings.warn('OpenSSL Python bindings are missing')

import Globals
from twisted.internet import reactor, defer
from twisted.internet.error import ConnectionLost, TimeoutError

# SMTP imports
from twisted.mail.smtp import ESMTPSenderFactory, SMTPSenderFactory

# POP3 imports
from twisted.internet import protocol
from twisted.mail.pop3 import AdvancedPOP3Client, ServerErrorResponse

from Products.ZenUtils.Driver import drive


def timeout(secs):
    d = defer.Deferred()
    reactor.callLater(secs, d.callback, None)
    return d

def sendMessage(config):
    # Make a message
    msg = Message.Message()
    msgid = Utils.make_msgid()
    # remember the msgid so we can find it later
    config.msgid = msgid
    msg['To'] = config.toAddress
    msg['From'] = config.fromAddress
    msg['Message-ID'] = msgid
    msg['X-Zenoss-Time-Sent'] = str(config.sent)
    msg['Subject'] = 'Zenoss Round-Trip Mail Message'
    msg.set_payload(config.messageBody)
    log.debug("Message id %s's length is %s bytes" % (
              msgid, len(msg.as_string())))
    msgIO = StringIO(msg.as_string())
    result = defer.Deferred()

    # figure out how we should connect
    connect = reactor.connectTCP
    port = 25
    kwargs = {}
    args = ()
    if ssl and config.smtpAuth == 'SSL':
        port = 465
        connect = reactor.connectSSL
        kwargs.update(dict(requireTransportSecurity = False))
        args = (ssl.ClientContextFactory(), )
    elif ssl and config.smtpAuth == 'TLS':
        pass
    else:
        kwargs.update(dict(requireTransportSecurity = False))

    if config.smtpUsername:
        log.debug( "ESMTP login as %s/%s" % (
                   config.smtpUsername, "*" * len(config.smtpPassword)))
        factory = ESMTPSenderFactory(config.smtpUsername,
                                     config.smtpPassword,
                                     config.fromAddress,
                                     (config.toAddress,),
                                     msgIO,
                                     result,
                                     **kwargs)
    else:
        factory = SMTPSenderFactory(config.fromAddress,
                                    (config.toAddress,),
                                    msgIO,
                                    result)

    def clientConnectionFailed(self, why):
        result.errback(why)
    factory.clientConnectionFailed = clientConnectionFailed

    # initiate the message send
    log.debug( "Sending message to %s:%s with args: %s" % (
                    config.smtpHost, config.smtpPort or port, args ))
    connect(config.smtpHost, config.smtpPort or port, factory, *args)
    return result

def fetchOnce(config, lines):

    result = defer.Deferred()

    # Our own POP3Client, to scan the messages for the outstanding
    # message
    Base = AdvancedPOP3Client
    class POP3Client(Base):
        message = None
        def connectionMade(self):
            Base.connectionMade(self)
            def inner(driver):
                try:
                    self.allowInsecureLogin = config.popAllowInsecureLogin
                    yield self.login(config.popUsername, config.popPassword)
                    msg = driver.next()
                    if msg:
                        log.debug('Login message: %s', msg)
                    else:
                        log.debug('No message from server!')

                    yield self.listUID()
                    #log.debug('Found message uids on POP server %r', driver.next())
                    #driver.next())
                    log.debug('Scanning for messages...')
                    junk = set()
                    for i, uid in enumerate(driver.next()):
                        # skip any messages we've scanned before
                        if uid is None or uid in config.ignoreIds:
                            continue
                        # fetch the top of the message
                        yield self.retrieve(i, lines=lines)
                        for line in driver.next():
                            parts = line.split(':', 1)
                            if len(parts) != 2:
                                continue
                            field = parts[0].strip().lower()
                            # this is a zenoss message: baletit!
                            if field == 'x-zenoss-time-sent':
                                junk.add(i)
                            if field != 'message-id':
                                continue
                            if parts[1].strip() != config.msgid:
                                continue
                            break
                        else:
                            # add scanned message to the ignorables
                            config.ignoreIds.add(uid)
                            continue

                        # found it!
                        log.debug("Found msgid %s", config.msgid)
                        junk.add(i)
                        yield self.retrieve(i)
                        self.message = '\n'.join(driver.next())

                    for msg in junk:
                        log.debug('Deleting message %s' % msg)
                        yield self.delete(msg)
                        driver.next()
                    yield self.quit()
                    driver.next()
                    # yield the value we want to show up in the deferred result
                    yield defer.succeed(self.message)
                    driver.next()

                except ServerErrorResponse, ex:
                    dsdev, ds = config.key()
                    log.error("Error from %s/%s server %s: %s" % (
                              dsdev, ds, config.popHost, ex ))
                except Exception, ex:
                    log.exception(ex)
            drive(inner).chainDeferred(result)

        def connectionLost(self, why):
            log.debug("POP client disconnected from %s", config.popHost)

    args = ()
    connect = reactor.connectTCP
    port = 110
    if ssl and config.popAuth == 'SSL':
        connect = reactor.connectSSL
        args = (ssl.ClientContextFactory(),)
        port = 995
    factory = protocol.ClientFactory()
    factory.protocol = POP3Client

    def clientConnectionFailed(self, why):
        result.errback(why)
    factory.clientConnectionFailed = clientConnectionFailed

    log.debug("POP client attempting connection to %s", config.popHost)
    connect(config.popHost, config.popPort or port, factory, *args)
    return result


def getMessage(config, pollSeconds, lines=0):
    "Poll a pop account for the message that goes with this config"
    if config.msgid is None:
        return defer.fail(ValueError("No outstanding message for %s:%s" % (
                                     config.device, config.name)))
    start = time.time()
    end = start + config.timeout
    def poll(driver):
        while 1:
            remaining = end - time.time()
            if remaining < 0:
                raise TimeoutError
            yield fetchOnce(config, lines)
            try:
                if driver.next() is not None:
                    yield defer.succeed(driver.next())
                    config.msgid = None
                    break
            except ConnectionLost:
                pass
            remaining = end - time.time()
            if remaining < 0:
                raise TimeoutError
            yield timeout(min(remaining, pollSeconds))
            driver.next()
    return drive(poll)


def error(why):
    if hasattr(why, 'value'):
        sys.stderr.write("Error %s" % why.value)
    else:
        sys.stderr.write("Error %s" % why)


def stop(ignored):
    if reactor.running:
        reactor.stop()


# Note: The following is used by the datasource to test
def testDevice(device, datasource):
    log.info("Testing mail transaction against device %s" % (device,))
    def go(driver):
        from Products.ZenUtils.ZenScriptBase import ZenScriptBase
        from ZenPacks.zenoss.ZenMailTx.MailTxConfigService import MailTxConfigService
       
        zendmd = ZenScriptBase(noopts=True, connect=True)
        dmd = zendmd.dmd
        d = dmd.Devices.findDevice(device)
        if not d:
            sys.stderr.write("Unable to find device %s\n" % device)
            sys.exit(1)
        log.setLevel(logging.DEBUG)
        service = MailTxConfigService(dmd, d.perfServer().id)
        if not service:
            sys.stderr.write("Unable to find configuration for %s" % device)
        proxy = service.remote_getDeviceConfigs( [device] )
        if proxy:
            proxy = proxy[0]
        else:
            raise ValueError("Unable to find a valid MailTx config for device %s" % device)
        config = proxy.datasources
        if datasource:
            config = [c for c in proxy.datasources if c.name == datasource]
        if not config:
            raise ValueError("Unable to find a MailTx config %s for device %s" %
                             (datasource or '', device))
        config = config[0]
        config.ignoreIds = set()
        now = time.time()
        yield sendMessage(config)
        log.debug("Result of message send: %s", driver.next())
        yield getMessage(config, 5.0)
        log.debug("Result of message fetch: %s", driver.next())
        log.info("Message delivered in %.2f seconds" % (time.time() - now))
    d = drive(go)
    d.addErrback(error)
    d.addCallback(stop)
    reactor.run()

if __name__ == '__main__':
    logging.basicConfig()
    log.setLevel(10)
    import getopt
    args, names = getopt.getopt(sys.argv[1:], 'd:s:')
    device = None
    source = None
    for opt, value in args:
        if opt == '-d':
            device = value
        elif opt == '-s':
            source = value
        else:
            raise ValueError("Unknown option: " + opt)
    if device:
        name = (names and names[0]) or 'localhost'
        testDevice(device, source)
    else:
        print "Usage: %s -d device"
        sys.exit(1)
