# This file is part of Bika LIMS
#
# Copyright 2011-2016 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from DateTime import DateTime
from Products.CMFPlone.utils import _createObjectByType
from bika.lims import logger
from bika.lims.content.analysis import Analysis
from bika.lims.testing import BIKA_SIMPLE_FIXTURE
from bika.lims.tests.base import BikaSimpleTestCase
from bika.lims.utils import tmpID
from bika.lims.workflow import doActionFor
from plone.app.testing import login, logout
from plone.app.testing import TEST_USER_NAME
from Products.CMFCore.utils import getToolByName

import re
import transaction
import unittest
import StringIO
from zope.testbrowser import interfaces
from zope.interface.verify import verifyObject

try:
    import unittest2 as unittest
except ImportError:  # Python 2.7
    import unittest


class TestARImports(BikaSimpleTestCase):

    def addthing(self, folder, portal_type, **kwargs):
        thing = _createObjectByType(portal_type, folder, tmpID())
        thing.unmarkCreationFlag()
        thing.edit(**kwargs)
        thing._renameAfterCreation()
        return thing

    def setUp(self):
        super(TestARImports, self).setUp()
        login(self.portal, TEST_USER_NAME)
        self.clients = self.addthing(self, 'Clients',title='Clients')
        self.client = self.addthing(self.clients, 'Client',
                                    title='Happy Hills', ClientID='HH')
        self.addthing(self.client, 'Contact', Firstname='Rita Mohale',
                      Lastname='Mohale')

    def setUp(self):
        super(TestARImports, self).setUp()
        login(self.portal, TEST_USER_NAME)
        clients = self.portal.clients
        bs = self.portal.bika_setup
        # @formatter:off
        self.client = self.addthing(clients, 'Client', title='Happy Hills', ClientID='HH')
        contact = self.addthing(self.client, 'Contact', Firstname='Rita', Lastname='Mohale')
        container = self.addthing(bs.bika_containers, 'Container', title='Bottle', capacity="10ml")
        # Sample
        sampletype = self.addthing(bs.bika_sampletypes, 'SampleType', title='Water', Prefix='H2O')
        samplepoint = self.addthing(bs.bika_samplepoints, 'SamplePoint', title='Toilet')
        priority = self.addthing(bs.bika_arpriorities, 'ARPriority', title='Normal', sortKey=1)

        ar_category = self.addthing(self.portal.bika_setup.bika_analysiscategories, 'AnalysisCategory',
                      title='Metals')
        service = self.addthing(bs.bika_analysisservices, 
                'AnalysisService', 
                title='Ecoli', 
                Keyword="ECO",
                Category=ar_category.UID())
        batch = self.addthing(self.portal.batches, 'Batch', title='B1')
        # Create Sample with single partition
        self.sample1 = self.addthing(self.client, 'Sample', SampleType=sampletype)
        self.sample2 = self.addthing(self.client, 'Sample', SampleType=sampletype)
        self.addthing(self.sample1, 'SamplePartition', Container=container)
        self.addthing(self.sample2, 'SamplePartition', Container=container)
        # Create an AR
        self.ar1 = self.addthing(self.client, 'AnalysisRequest', Contact=contact,
                                Sample=self.sample1, Analyses=[service], SamplingDate=DateTime())
        # Create a secondary AR - linked to a Batch
        self.ar2 = self.addthing(self.client, 'AnalysisRequest', Contact=contact,
                                Sample=self.sample1, Analyses=[service], SamplingDate=DateTime(),
                                Batch=batch)
        # Create an AR - single AR on sample2
        self.ar3 = self.addthing(self.client, 'AnalysisRequest', Contact=contact,
                                Sample=self.sample2, Analyses=[service], SamplingDate=DateTime())
        transaction.commit()
    def tearDown(self):
        super(TestARImports, self).setUp()
        login(self.portal, TEST_USER_NAME)


    def test_BC_4(self):
        browser = self.getBrowser(loggedIn=True)
        browser.open(self.client.absolute_url())
        import_exim_url = 'import?exim=shimadzu.gcms.tq8030_gc_ms_ms'
        import_url = '%s/%s' % (self.portal.absolute_url(), import_exim_url)
        browser.open(import_url)
        content = browser.contents
        if 'Advanced options' not in content:
            self.fail('Text Advanced options not in content')
        import pdb; pdb.set_trace()
        ctrl = browser.getControl(name='file')
        path = '/home/lunga/instances/bikafromrestore/zinstance/src/bika.lims/bika/lims/exportimport/instruments/shimadzu/gcms/samples'
        filename = '%s/GC-MS output.txt' % path
        ctrl.add_file(open(filename, 'r'),'text/plain', 'test.txt')
        #verifyObject(interfaces.IControl, ctrl)


        #Pass read_data as file contents
        browser.getControl(name="firstsubmit").click()
        # Import
        #Import Instrument File     Horiba Jobin-Yvon - ICP  ${PATH_TO_TEST}/files/ICPlimstest.csv
        #Page should contain        Service keyword Ni221647 not found
        #Page should contain        Import finished successfully: 1 ARs and 1 results updated
        #Go to    ${PLONEURL}/clients/client-1/BR-0001-R01/manage_results
        #Textfield value should be        css=[selector="Result_Al396152"]  0.1337
        #>>> ctrl = browser.getControl('File Control')
        #>>> ctrl
        #<Control name='file-value' type='file'>
        #>>> verifyObject(interfaces.IControl, ctrl)
        #True
        #>>> ctrl.value is None
        #True
        #>>> import 
        #>>> ctrl.add_file(cStringIO.StringIO('File contents'),

        #        ...               'text/plain', 'test.txt')
        #browser.getControl(name="form.button.save").click()
        import pdb; pdb.set_trace()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestARImports))
    suite.layer = BIKA_SIMPLE_FIXTURE
    return suite
