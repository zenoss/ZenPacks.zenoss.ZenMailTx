######################################################################
#
# Copyright 2007 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import Globals
import os
import sys
from Products.CMFCore.DirectoryView import registerDirectory

skinsDir = os.path.join(os.path.dirname(__file__), 'skins')
if os.path.isdir(skinsDir):
    registerDirectory(skinsDir, globals())

libDir = os.path.join(os.path.dirname(__file__), 'lib')
if os.path.isdir(libDir):
    sys.path.append(libDir)

# Used in the datasource for pathing
zpDir = os.path.dirname(__file__)
