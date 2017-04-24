# This file is part of Bika LIMS
#
# Copyright 2011-2016 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

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

    def tearDown(self):
        super(TestARImports, self).setUp()
        login(self.portal, TEST_USER_NAME)


    def test_BC_4(self):
        ar_category = self.addthing(self.portal.bika_setup.bika_analysiscategories, 'AnalysisCategory',
                      title='Metals')
        a_ser = self.addthing(self.portal.bika_setup.bika_analysisservices, 'AnalysisService',
                      title='AR1', keyword='TestKeyword',
                      category=ar_category.UID())
        sample_type = self.addthing(self.portal.bika_setup.bika_sampletypes, 'SampleType',
                      title='Water', Prefix='H2O')
        # SamplePoint
        #sample_point = self.addthing(self.portal.bika_setup.bika_samplepoints, 'SamplePoint',
        #              title='Toilet')
        #sample_point.reindexObject()
        #ll = self.addthing(self.client, 'AnalysisRequest', 
        #        Analyses=a_ser.UID(), SampleType=sample_type.UID(),)
        browser = self.getBrowser(loggedIn=True)
        browser.open(self.client.absolute_url())
        import pdb; pdb.set_trace()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestARImports))
    suite.layer = BIKA_SIMPLE_FIXTURE
    return suite
