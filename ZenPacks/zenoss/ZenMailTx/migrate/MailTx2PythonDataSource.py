##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

from Products.ZenModel.migrate.Migrate import Version
from Products.ZenModel.ZenPack import ZenPackMigration

from ZenPacks.zenoss.ZenMailTx.datasources.MailTxPythonDataSource import MailTxPythonDataSource

class MailTx2PythonDataSource(ZenPackMigration):
    """ Replace datasource """
    version = Version(2, 7, 0)

    def migrate(self, pack):
        for device in pack.dmd.Devices.getSubDevices():
            for template in device.getRRDTemplates():
                for datasource in template.datasources():
                    if datasource.sourcetype == 'MAILTX':
                        new_ds = MailTxPythonDataSource(datasource.id, datasource.title)
                        for p in datasource._properties:
                            setattr(new_ds, p['id'], getattr(datasource, p['id']))
                        template.datasources._delObject(datasource.id)
                        template.datasources._setObject(datasource.id, new_ds)
                        log.info('Replaced datasource %s with python datasource of the same name' % datasource.id)

migration = MailTx2PythonDataSource()
