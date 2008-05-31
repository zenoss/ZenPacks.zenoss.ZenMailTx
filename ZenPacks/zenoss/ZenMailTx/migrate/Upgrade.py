######################################################################
#
# Copyright 2007 Zenoss, Inc.  All Rights Reserved.
#
######################################################################
import Globals
from Products.ZenModel.migrate.Migrate import Version
import logging

class Upgrade:
    version = Version(0, 9, 0)

    oldAuthor = None

    def migrate(self, pack):
        oldAuthor = pack.author
        pack.author = "Zenoss Team"
