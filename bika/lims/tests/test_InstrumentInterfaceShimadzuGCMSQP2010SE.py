# -*- coding: utf-8 -*-
# This file is part of Bika LIMS
#
# Copyright 2011-2016 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from DateTime import DateTime
from Products.CMFPlone.utils import _createObjectByType
from bika.lims import logger
from bika.lims.content.analysis import Analysis
from bika.lims.exportimport.instruments.shimadzu.gcms.qp2010se import Import
from bika.lims.testing import BIKA_SIMPLE_FIXTURE
from bika.lims.tests.base import BikaSimpleTestCase
from bika.lims.utils import tmpID
from bika.lims.workflow import doActionFor
from plone import api
from plone.app.testing import login, logout
from plone.app.testing import TEST_USER_NAME
from zope.publisher.browser import TestRequest
from zope.publisher.browser import FileUpload
from Products.CMFCore.utils import getToolByName

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
        self.client = self.addthing(self.portal.clients, 'Client',
                                    title='AA Test Client', ClientID='AAT')
        self.addthing(self.client, 'Contact', Firstname='A Test Client Contact',
                      Lastname='Contact')
        self.addthing(self.portal.bika_setup.bika_sampletypes, 'SampleType',
                      title='Water', Prefix='1')
        self.addthing(self.portal.bika_setup.bika_samplematrices,
                      'SampleMatrix', title='Liquids')
        self.addthing(self.portal.bika_setup.bika_samplepoints, 'SamplePoint',
                      title='Toilet')
        self.addthing(self.portal.bika_setup.bika_containertypes,
                      'ContainerType', title='Cup')
        self.addthing(self.portal.bika_setup.bika_arpriorities, 'ARPriority',
                      title='Normal', sortKey=1)
        a = self.addthing(self.portal.bika_setup.bika_analysisservices,
                          'AnalysisService', title='Diazinone', Keyword="Diazinone")
        self.addthing(self.portal.bika_setup.bika_analysisprofiles,
                      'AnalysisProfile', title='BIO',
                      Service=[a.UID()])

    def tearDown(self):
        super(TestInstrumentImport, self).setUp()
        login(self.portal, TEST_USER_NAME)

    def test_BC5_Shimadzu_QP2010Import(self):
        pc = getToolByName(self.portal, 'portal_catalog')
        workflow = getToolByName(self.portal, 'portal_workflow')
        arimport = self.addthing(self.client, 'ARImport')
        arimport.unmarkCreationFlag()
        arimport.setFilename("test1.csv")
        arimport.setOriginalFile("""
Header,File name,Client name,Client ID,Contact,CC Names - Report,CC Emails - Report,CC Names - Invoice,CC Emails - Invoice,Client Order Number,Client Reference,No of Samples,,,,,,,,,,,,,,,,,,,
Header Data,ALSBikaImportToBatch201701,AA Test Client,AAT,A Test Client Contact,,,,,,,,,,,,,,,,,,,,,,,,,,
Batch Header,title,description,ClientBatchID,BatchDate,ClientBatchComment,BatchLabels,ReturnSampleToClient,,,,,,,,,,,,,,,,,,,,,,,
Batch Data,,,,11/9/2016,,,,,,,,,,,,,,,,,,,,,,,,,,
Samples,ClientSampleID,SamplingDate,DateSampled,Sampler,SamplePoint,Activity Sampled,Amount Sampled,Metric,SampleMatrix,SampleType,ContainerType,ReportDryMatter,Priority,Total number of Profiles or Analyses ,Price excl Tax,Diazinone,W11,GW4,W20F,W300,WKDC02,WB01,BIO,,,,,,,
Analysis price,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
Total Analyses or Profiles,,,,,,,,,,,,,,0,,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
Total price excl Tax,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
Sample 1,ClientSampleID 1,,01/17/2017 10:29:00,Client Sampler,KKPW03B,,,,,Potable Water,Plastic Bottle,,,,,,,,1,,,,,,,,,,,
        """)

        # check that values are saved without errors
        arimport.setErrors([])
        arimport.save_header_data()
        arimport.save_sample_data()
        arimport.create_or_reference_batch()
        errors = arimport.getErrors()
        if errors:
            self.fail("Unexpected errors while saving data: " + str(errors))
        # check that batch was created and linked to arimport without errors
        if not pc(portal_type='Batch'):
            self.fail("Batch was not created!")
        if not arimport.schema['Batch'].get(arimport):
            self.fail("Batch was created, but not linked to ARImport.")

        # the workflow scripts use response.write(); silence them
        arimport.REQUEST.response.write = lambda x: x

        # check that validation succeeds without any errors
        workflow.doActionFor(arimport, 'validate')
        state = workflow.getInfoFor(arimport, 'review_state')
        if state != 'valid':
            errors = arimport.getErrors()
            self.fail(
                'Validation failed!  %s.Errors: %s' % (arimport.id, errors))

        # Import objects and verify that they exist
        workflow.doActionFor(arimport, 'import')
        state = workflow.getInfoFor(arimport, 'review_state')
        if state != 'imported':
            errors = arimport.getErrors()
            self.fail(
                'Importation failed!  %s.Errors: %s' % (arimport.id, errors))

        bc = getToolByName(self.portal, 'bika_catalog')
        ars = bc(portal_type='AnalysisRequest')
        ar = ars[0]
        api.content.transition(obj=ar.getObject(), transition='receive')
        transaction.commit()
        #Testing Import for Instrument
        path = os.path.dirname(__file__)
        filename = '%s/files/GC-QQQ output.txt' % path
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
        transaction.commit()
        text = 'Import finished successfully: 1 ARs and 1 results updated'
        import pdb; pdb.set_trace()
        if text not in results:
            self.fail("AR Import failed")
        browser = self.getBrowser(loggedIn=True)
        browser.open(ar.getObject().absolute_url() + "/manage_results")
        content = browser.contents
        if '0.02604' not in content:
            self.fail("AR Result did not get updated")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestInstrumentImport))
    suite.layer = BIKA_SIMPLE_FIXTURE
    return suite
