######################################################################
#
# Copyright 2008 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import Globals
from Products.ZenModel.migrate.Migrate import Version
from Products.ZenModel.ZenPack import ZenPack, ZenPackDataSourceMigrateBase
from ZenPacks.zenoss.ZenMailTx.datasources.MailTxDataSource \
        import MailTxDataSource


class ConvertMailTxDataSources(ZenPackDataSourceMigrateBase):
    version = Version(2, 0, 0)
    
    # These provide for conversion of datasource instances to the new class
    dsClass = MailTxDataSource
    oldDsModuleName = 'Products.ZenMailTx.datasources.MailTxDataSource'
    oldDsClassName = 'MailTxDataSource'
    
    # Reindex all applicable datasource instances
    reIndex = True
            
