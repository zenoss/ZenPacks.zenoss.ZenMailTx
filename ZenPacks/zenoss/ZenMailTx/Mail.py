######################################################################
#
# Copyright 2007 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import time
from sets import Set
from StringIO import StringIO
from email import Message, Utils

# include our OpenSSL libs in the path
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

ssl = None
try:
    from twisted.internet import ssl
except ImportError:
    import warnings
    warnings.warn('OpenSSL python bindings are missing')


import Globals
from twisted.internet import reactor, defer
from twisted.internet.error import ConnectionLost, TimeoutError

# SMTP imports
from twisted.mail.smtp import ESMTPSenderFactory, SMTPSenderFactory

# POP3 imports
from twisted.internet import protocol
from twisted.mail.pop3 import AdvancedPOP3Client

from Products.ZenUtils.Driver import drive

import logging
log = logging.getLogger('zen.MailTx.Mail')

def timeout(secs):
    d = defer.Deferred()
    reactor.callLater(secs, d.callback, None)
    return d

def SendMessage(config):
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
    msg = StringIO(msg.as_string())
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
        factory = ssl.ClientContextFactory()
        args = (ssl.ClientContextFactory(), )
    elif ssl and config.smtpAuth == 'TLS':
        pass
    else:
        kwargs.update(dict(requireTransportSecurity = False))
    if config.smtpUsername:
        factory = ESMTPSenderFactory(config.smtpUsername,
                                     config.smtpPassword,
                                     config.fromAddress,
                                     (config.toAddress,),
                                     msg,
                                     result,
                                     **kwargs)
    else:
        factory = SMTPSenderFactory(config.fromAddress,
                                    (config.toAddress,),
                                    msg,
                                    result)
        
    # initiate the message send
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
                    log.debug('login %s', driver.next())
                    yield self.listUID()
                    log.debug('uids %r', driver.next())
                    junk = Set()
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
                        # FIXME: use \r\n?
                        self.message = '\n'.join(driver.next())
                    log.debug('Deleting: %r', junk)
                    for msg in junk:
                        yield self.delete(msg)
                        driver.next()
                    yield self.quit()
                    driver.next()
                    # yield the value we want to show up in the deferred result
                    yield defer.succeed(self.message)
                    driver.next()
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
    log.debug("POP client connected to %s", config.popHost)
    connect(config.popHost, config.popPort or port, factory, *args)
    return result

def GetMessage(config, pollSeconds, lines=50):
    "poll a pop account for the message that goes with this config"
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
            except ConnectionLost, ex:
                pass
            remaining = end - time.time()
            if remaining < 0:
                raise TimeoutError
            yield timeout(min(remaining, pollSeconds))
            driver.next()
    return drive(poll)
    
def test():
    def go(driver):
        class Object: pass
        config = Object()
        config.sent = time.time()
        config.toAddress = 'ecn@swcomplete.com'
        config.fromAddress = 'eric.newton@gmail.com'
        config.messageBody = "This is the body of this message\n\n-Eric\n"
        config.smtpUsername = 'eric.newton'
        config.smtpPassword = sys.argv[1]
        config.smtpHost = 'smtp.gmail.com'
        config.smtpPort = None
        config.smtpAuth = 'SSL'
        config.device = 'zenoss'
        config.name = 'MailTx'
        config.timeout = 10
        config.ignoreIds = Set()
        now = time.time()
        yield SendMessage(config)
        try:
            driver.next()
        except Exception, ex:
            if reactor.running:
                reactor.stop()
            raise ex

        config.popUsername = 'ecn@zenoss.com'
        config.popPassword = config.smtpPassword
        config.popHost = 'mail.zenoss.com'
        config.popPort = None
        config.popAuth = None
        yield GetMessage(config, 5.0)
        driver.next()
        print time.time() - now

    def printError(result):
        log.error('Error: %s', result)
    d = drive(go)
    d.addErrback(printError)
    d.addBoth(lambda x: reactor.stop())
    reactor.run()

def error(why):
    sys.stderr.write("Error: %s" % (why,))

def stop(ignored):
    if reactor.running:
        reactor.stop()

def testDevice(device, datasource):
    log.info("Testing mail transaction against device %s" % (device,))
    def go(driver):
        from Products.ZenUtils.ZenScriptBase import ZenScriptBase
        from ZenPacks.zenoss.ZenMailTx.ConfigService import ConfigService
        zendmd = ZenScriptBase(noopts=True, connect=True)
        dmd = zendmd.dmd
        d = dmd.Devices.findDevice(device)
        if not d:
            sys.stderr.write("Unable to find device %s\n" % device)
            sys.exit(1)
        s = ConfigService(dmd, d.perfServer().id)
        if not s:
            sys.stderr.write("Unable to find configuration for %s" % device)
        config = s.getDeviceConfig(d)
        if datasource:
            config = [c for c in config if c.name == datasource]
        if not config:
            raise ValueError("Unable to find a MailTx config %s for device %s" %
                             (datasource or '', device))
        config = config[0]
        config.ignoreIds = Set()
        now = time.time()
        yield SendMessage(config)
        log.debug("Result of message send: %s", driver.next())
        yield GetMessage(config, 5.0)
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
    elif names:
        test()
    else:
        print "Usage: %s -d device"
        sys.exit(1)
