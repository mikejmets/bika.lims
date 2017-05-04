# This file is part of Bika LIMS
#
# Copyright 2011-2016 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from DateTime import DateTime
from Products.CMFPlone.utils import _createObjectByType
from bika.lims import logger
from bika.lims.content.analysis import Analysis
from bika.lims.exportimport.instruments.shimadzu.gcms.tq8030 import Import
from bika.lims.testing import BIKA_SIMPLE_FIXTURE
from bika.lims.tests.base import BikaSimpleTestCase
from bika.lims.utils import tmpID
from bika.lims.workflow import doActionFor
from plone import api
from plone.app.testing import login, logout
from plone.app.testing import TEST_USER_NAME
from zope.publisher.browser import TestRequest
from zope.publisher.browser import FileUpload

import cStringIO
import os
import re
import transaction
import unittest

try:
    import unittest2 as unittest
except ImportError:  # Python 2.7
    import unittest

class TestFile(object):
    def __init__(self, file):
        self.file = file
        self.headers = {}
        self.filename = 'dummy.txt'

class TestInstrumentImport(BikaSimpleTestCase):

    def addthing(self, folder, portal_type, **kwargs):
        thing = _createObjectByType(portal_type, folder, tmpID())
        thing.unmarkCreationFlag()
        thing.edit(**kwargs)
        thing._renameAfterCreation()
        return thing

    def setUp(self):
        super(TestInstrumentImport, self).setUp()
        login(self.portal, TEST_USER_NAME)
        clients = self.portal.clients
        bs = self.portal.bika_setup
        # @formatter:off
        self.client = self.addthing(clients, 'Client', title='Happy Hills', ClientID='HH')
        contact = self.addthing(self.client, 'Contact', Firstname='Rita', Lastname='Mohale')
        # Sample
        sampletype = self.addthing(bs.bika_sampletypes, 'SampleType', title='1', Prefix='1')
        ar_category = self.addthing(self.portal.bika_setup.bika_analysiscategories, 'AnalysisCategory',
                      title='Metals')
        service = self.addthing(bs.bika_analysisservices, 
                'AnalysisService', 
                title='alpha-Pinene', 
                Keyword="alphaPinene",
                Category=ar_category.UID())
        # Create Sample
        self.sample1 = self.addthing(self.client, 'Sample', SampleType=sampletype)
        # Create an AR
        self.ar1 = self.addthing(self.client, 'AnalysisRequest', Contact=contact,
                                Sample=self.sample1, Analyses=[service], SamplingDate=DateTime())
        api.content.transition(obj=self.ar1, transition='sampling_workflow')
        state = api.content.get_state(self.ar1)
        if state == 'to_be_sampled':
            try:
                api.content.transition(obj=self.ar1, transition='sample')
                transaction.commit()
            except Exception, e:
                pass
        state = api.content.get_state(self.ar1)
        api.content.transition(obj=self.ar1, transition='sample_due')
        api.content.transition(obj=self.ar1, transition='receive')
        state = api.content.get_state(self.ar1)
        transaction.commit()
        if state != 'sample_received':
            self.fail("Incorrect state for AR")

    def tearDown(self):
        super(TestInstrumentImport, self).setUp()
        login(self.portal, TEST_USER_NAME)


    def test_BC_4(self):
        path = os.path.dirname(__file__)
        filename = '%s/files/GC-MS output.txt' % path
        if not os.path.isfile(filename):
            self.fail("File %s not found" % filename)
        data = open(filename, 'r').read()
        file = FileUpload(TestFile(cStringIO.StringIO(data)))
        request = TestRequest()
        request = TestRequest(form=dict(
                                    submitted=True,
                                    artoapply='received',
                                    override='nooverride',
                                    file=file,
                                    sample='requestid',
                                    instrument=''))
        context = self.portal
        results = Import(context, request)
        text = 'Import finished successfully: 1 ARs and 1 results updated'
        if text not in results:
            self.fail("AR did not get updated")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestInstrumentImport))
    suite.layer = BIKA_SIMPLE_FIXTURE
    return suite
