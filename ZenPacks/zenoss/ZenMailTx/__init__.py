##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
import os
from Products.ZenUtils.Utils import monkeypatch


@monkeypatch('twisted.mail.smtp.SMTPClientError')
def __str__(self):
    if self.code > 0:
        if hasattr(self.code, 'code') and hasattr(self.code, 'resp'):
            res = ["%s: %s" % (self.code.code, self.code.resp)]
        else:
            res = ["%s %s" % (self.code, self.resp)]
    else:
        res = [self.resp]
    if self.log:
        res.append(self.log)
        res.append('')
    return '\n'.join(res)

# Used in the datasource for pathing
zpDir = os.path.dirname(__file__)
