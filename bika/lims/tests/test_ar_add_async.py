# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from bika.lims.testing import BIKA_FUNCTIONAL_TESTING
from bika.lims.tests.base import BikaFunctionalTestCase
from bika.lims.utils.analysisrequest import create_analysisrequest
from bika.lims.workflow import doActionFor
from plone.app.testing import login, logout
from plone.app.testing import TEST_USER_NAME
import unittest

try:
    import unittest2 as unittest
except ImportError: # Python 2.7
    import unittest


class TestHiddenAnalyses(BikaFunctionalTestCase):
    layer = BIKA_FUNCTIONAL_TESTING

    def setUp(self):
        super(TestHiddenAnalyses, self).setUp()
        login(self.portal, TEST_USER_NAME)
        servs = self.portal.bika_setup.bika_analysisservices

        # analysis-service-3: Calcium (Ca)
        # analysis-service-6: Cooper (Cu)
        # analysis-service-7: Iron (Fe)
        self.services = [servs['analysisservice-3'],
                         servs['analysisservice-6'],
                         servs['analysisservice-7']]

        profs = self.portal.bika_setup.bika_analysisprofiles
        # analysisprofile-1: Trace Metals
        self.analysisprofile = profs['analysisprofile-1']

        artemp = self.portal.bika_setup.bika_artemplates
        # artemplate-2: Bruma Metals
        self.artemplate = artemp['artemplate-2']

    def tearDown(self):
        # Restore
        for s in self.services:
            s.setHidden(False)

        self.analysisprofile.setAnalysisServicesSettings([])
        self.artemplate.setAnalysisServicesSettings([])

        logout()
        super(TestHiddenAnalyses, self).tearDown()

    def test_async_add_analysisrequest(self):
        # Input results
        # Client:       Happy Hills
        # SampleType:   Apple Pulp
        # Contact:      Rita Mohale
        # Analyses:     [Calcium, Copper, Iron]
        client = self.portal.clients['client-1']
        sampletype = self.portal.bika_setup.bika_sampletypes['sampletype-1']
        request = {}
        services = [s.UID() for s in self.services]
        values = {'Client': client.UID(),
                  'Contact': client.getContacts()[0].UID(),
                  'SamplingDate': '2015-01-01',
                  'SampleType': sampletype.UID()}
        ar = create_analysisrequest(client, request, values, services)
        self.assertTrue(ar)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHiddenAnalyses))
    suite.layer = BIKA_FUNCTIONAL_TESTING
    return suite
