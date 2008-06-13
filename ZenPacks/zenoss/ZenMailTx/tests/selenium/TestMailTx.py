#!/usr/bin/python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

#
# Contained below is the class that tests elements located under
# the "Mibs" Browse By subheading.
#
# Noel Brockett
#

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

zenhome = os.environ['ZENHOME']

sys.path.append(os.path.join(zenhome, 'Products', 'ZenUITests', 'tests',
            'selenium'))

import unittest

from SelTestBase import SelTestBase

class TestMailTx(SelTestBase):
    """Defines a class that runs tests under the MailTx zenpack"""

    def _goToPerformanceConfTemplate(self):
        self.waitForElement("link=Collectors")
        self.selenium.click("link=Collectors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("id=PerformanceMonitorlistperformanceTemplates")
        self.selenium.click("id=PerformanceMonitorlistperformanceTemplates")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("link=PerformanceConf")
        self.selenium.click("link=PerformanceConf")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addDataSource(self):
        self._goToPerformanceConfTemplate()
        if self.selenium.is_element_present("link=dataSourceTestingStringEdit"):
            self._deleteDataSourceEdit()   
        if self.selenium.is_element_present("link=dataSourceTestingString"):
            self._deleteDataSource()
        self.addDialog("DataSourcelistaddDataSource", "manage_addRRDDataSource:method", 
                        new_id=("text", "dataSourceTestingString"),
                        dsOption=("select", "MAILTX"))       
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deleteDataSource(self):
        self._goToPerformanceConfTemplate()
        self.waitForElement("id=DataSourcelistdeleteDataSource")
        self.deleteDialog("DataSourcelistdeleteDataSource", "manage_deleteRRDDataSources:method", 
                pathsList="ids:list",
                form_name="datasourceList", testData="dataSourceTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def _deleteDataSourceEdit(self):
        self._goToPerformanceConfTemplate()
        self.waitForElement("id=DataSourcelistdeleteDataSource")
        self.deleteDialog("DataSourcelistdeleteDataSource", "manage_deleteRRDDataSources:method", 
                pathsList="ids:list",
                form_name="datasourceList",
                testData="dataSourceTestingStringEdit")
        self.selenium.wait_for_page_to_load(self.WAITTIME)


    def testAddAndEditMailTxDataSource(self):
        """Creates a testing MailTx data source and edits and verifies settings"""
        self._addDataSource()
       
        self.selenium.click("link=dataSourceTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("newId", "dataSourceTestingStringEdit")
        self.selenium.select("enabled:boolean", "label=False")
        self.selenium.select("eventClass", "label=/App/Email")
        self.selenium.type("eventKey", "1234") 
        self.selenium.select("severity:int", "value=5")
        self.selenium.type("cycletime:int", "301") 
        self.selenium.type("timeout:int", "302") 
        self.selenium.type("fromAddress:string", "noel@zenoss.com") 
        self.selenium.type("smtpUsername:string", "noel") 
        self.selenium.type("smtpPassword:string", "zenoss") 
        self.selenium.select("smtpAuth:string", "value=TLS")
        self.selenium.type("messageBody:text", "Testing Party Time!!!") 
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertSelectedValue', ['enabled:boolean',
                'False'])
        self.selenium.do_command('assertSelectedValue', ['eventClass',
                '/App/Email'])
        self.selenium.do_command('assertValue', ['eventKey', '1234'])
        self.selenium.do_command('assertSelectedValue', ['severity:int',
                '5'])
        self.selenium.do_command('assertValue', ['cycletime:int', '301'])
        self.selenium.do_command('assertValue', ['timeout:int', '302'])
        self.selenium.do_command('assertValue', ['fromAddress:string',
                'noel@zenoss.com'])
        self.selenium.do_command('assertValue', ['smtpUsername:string', 'noel'])
        self.selenium.do_command('assertValue', ['smtpPassword:string', 'zenoss'])
        self.selenium.do_command('assertSelectedValue', ['smtpAuth:string','TLS'])
        self.selenium.do_command('assertValue', ['messageBody:text', 'Testing Party Time!!!'])
        self.selenium.click("link=PerformanceConf")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertElementPresent', ['link=dataSourceTestingStringEdit'])
        self.selenium.do_command('assertTextPresent', ['MAILTX'])
        self.selenium.do_command('assertTextPresent', ['False'])
        self.selenium.click("link=dataSourceTestingStringEdit")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("newId", "dataSourceTestingString") 
        self.selenium.click("name=zmanage_editProperties:method")
        self._deleteDataSource()



if __name__ == "__main__":
    framework()
