##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
from Products.ZenModel.migrate.Migrate import Version
from Products.ZenModel.ZenPack import ZenPack, ZenPackDataSourceMigrateBase
from ZenPacks.zenoss.ZenMailTx.datasources.MailTxDataSource \
        import MailTxDataSource


class ConvertMailTxDataSources(ZenPackDataSourceMigrateBase):
    version = Version(2, 0, 1)
    
    # These provide for conversion of datasource instances to the new class
    dsClass = MailTxDataSource
    oldDsModuleName = 'Products.ZenMailTx.datasources.MailTxDataSource'
    oldDsClassName = 'MailTxDataSource'
    
    # Reindex all applicable datasource instances
    reIndex = True
