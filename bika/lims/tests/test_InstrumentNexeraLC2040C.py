# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from DateTime import DateTime
from Products.CMFPlone.utils import _createObjectByType
from bika.lims import logger
from bika.lims.exportimport.instruments.shimadzu.nexera.LC2040C import Import
from bika.lims.testing import BIKA_SIMPLE_FIXTURE
from bika.lims.tests.base import BikaSimpleTestCase
from bika.lims.utils import tmpID
from bika.lims.workflow import doActionFor
from bika.lims import api
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
                                    title='Happy Hills', ClientID='HH')
        self.addthing(self.client, 'Contact', Firstname='Rita Mohale',
                      Lastname='Mohale')
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
                          'AnalysisService', title='Ecoli', Keyword="Ecoli")
        b = self.addthing(self.portal.bika_setup.bika_analysisservices,
                          'AnalysisService', title='Calcium', Keyword="Ca")
        self.addthing(self.portal.bika_setup.bika_analysisprofiles,
                      'AnalysisProfile', title='MicroBio',
                      Service=[a.UID(), b.UID()])

    def tearDown(self):
        super(TestInstrumentImport, self).setUp()
        login(self.portal, TEST_USER_NAME)

    def test_Shimadzu_NexeraLC2040CImport_AutoTransition_SamplingEnabled(self):
        pc = getToolByName(self.portal, 'portal_catalog')
        api.get_bika_setup().setSamplingWorkflowEnabled(True)
        api.get_bika_setup().setAutoTransition('submit')
        transaction.commit()
        workflow = getToolByName(self.portal, 'portal_workflow')
        arimport = self.addthing(self.client, 'ARImport')
        arimport.unmarkCreationFlag()
        arimport.setFilename("test1.csv")
        arimport.setOriginalFile("""
Header,      File name,  Client name,  Client ID, Contact,     CC Names - Report, CC Emails - Report, CC Names - Invoice, CC Emails - Invoice, No of Samples, Client Order Number, Client Reference,,
Header Data, test1.csv,  Happy Hills,  HH,        Rita Mohale,                  ,                   ,                    ,                    , 10,            HHPO-001,                            ,,
Batch Header, id,       title,     description,    ClientBatchID, ClientBatchComment, BatchLabels, ReturnSampleToClient,,,
Batch Data,   B15-0123, New Batch, Optional descr, CC 201506,     Just a batch,                  , TRUE                ,,,
Samples,    ClientSampleID,    SamplingDate,DateSampled,Sampler,SamplePoint,SampleMatrix,SampleType,ContainerType,ReportDryMatter,Priority,Total number of Analyses or Profiles,Price excl Tax,CAL1,,,,MicroBio,,
Analysis price,,,,,,,,,,,,,,
"Total Analyses or Profiles",,,,,,,,,,,,,9,,,
Total price excl Tax,,,,,,,,,,,,,,
"Sample 1", HHS14001,          3/9/2014,    3/9/2014,,Toilet,     Liquids,     Water,     Cup,          0,              Normal,  1,                                   0,             0,0,0,0,0,1
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
        analyses = ar.getObject().getAnalyses(full_objects=True)
        for a in analyses:
            state = workflow.getInfoFor(a, 'review_state')
            if state == 'to_be_sampled':
                workflow.doActionFor(a, 'sample')
                transaction.commit()
            state = workflow.getInfoFor(a, 'review_state')
            if state == 'sample_due':
                workflow.doActionFor(a, 'receive')
                transaction.commit()
        workflow.doActionFor(ar.getObject(), 'receive')
        transaction.commit()
        #Testing Import for Instrument
        path = os.path.dirname(__file__)
        filename = '%s/files/nexera' % path
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
                                    instrument='',
                                    advancetostate='submit'))
        context = self.portal
        results = Import(context, request)
        transaction.commit()
        text = 'Import finished successfully: 1 ARs and 2 results updated'
        if text not in results:
            self.fail("AR Import failed")
        analyses = ar.getObject().getAnalyses(full_objects=True)
        for an in analyses:
            state = workflow.getInfoFor(an, 'review_state')
            if state != 'to_be_verified':
                self.fail('Auto Transition failed for:{}'.format(an))
            if an.getKeyword() == 'Ca':
                if an.getResult() != '0.0':
                    self.fail("%s:Result did not get updated" % an.getKeyword())
            if an.getKeyword() == 'Ecoli':
                if an.getResult() != '0.8':
                    self.fail("%s:Result did not get updated" % an.getKeyword())

        filename = '%s/files/nexera-ToBeVerified' % path
        if not os.path.isfile(filename):
            self.fail("File %s not found" % filename)
        data = open(filename, 'r').read()
        file = FileUpload(TestFile(cStringIO.StringIO(data)))
        request = TestRequest()
        request = TestRequest(form=dict(
                                    submitted=True,
                                    artoapply='received_tobeverified',
                                    override='nooverride',
                                    file=file,
                                    sample='requestid',
                                    instrument='',
                                    advancetostate='submit'))
        context = self.portal
        results = Import(context, request)
        transaction.commit()
        text = 'Import finished successfully: 1 ARs and 2 results updated'
        if text not in results:
            self.fail("AR Import failed")
        analyses = ar.getObject().getAnalyses(full_objects=True)
        for an in analyses:
            state = workflow.getInfoFor(an, 'review_state')
            if state != 'to_be_verified':
                self.fail('Auto Transition failed for:{}'.format(an))
            if an.getKeyword() == 'Ca':
                if an.getResult() != '0.0':
                    self.fail("%s:Result did not get updated" % an.getKeyword())
            if an.getKeyword() == 'Ecoli':
                if an.getResult() != '0.9':
                    self.fail("%s:Result did not get updated" % an.getKeyword())

    def test_Shimadzu_NexeraLC2040CImport_NoAutoTransition_SamplingDisabled(self):
        '''SamplingWorkflowEnabled = False
           AutoTransition = ''
        '''
        pc = getToolByName(self.portal, 'portal_catalog')
        #NOTE: SamplingWorkflowEnabled has to set before ARs are added
        api.get_bika_setup().setSamplingWorkflowEnabled(False)
        api.get_bika_setup().setAutoTransition('')
        transaction.commit()
        workflow = getToolByName(self.portal, 'portal_workflow')
        pc = getToolByName(self.portal, 'portal_catalog')
        workflow = getToolByName(self.portal, 'portal_workflow')
        arimport = self.addthing(self.client, 'ARImport')
        arimport.unmarkCreationFlag()
        arimport.setFilename("test1.csv")
        arimport.setOriginalFile("""
Header,      File name,  Client name,  Client ID, Contact,     CC Names - Report, CC Emails - Report, CC Names - Invoice, CC Emails - Invoice, No of Samples, Client Order Number, Client Reference,,
Header Data, test1.csv,  Happy Hills,  HH,        Rita Mohale,                  ,                   ,                    ,                    , 10,            HHPO-001,                            ,,
Batch Header, id,       title,     description,    ClientBatchID, ClientBatchComment, BatchLabels, ReturnSampleToClient,,,
Batch Data,   B15-0123, New Batch, Optional descr, CC 201506,     Just a batch,                  , TRUE                ,,,
Samples,    ClientSampleID,    SamplingDate,DateSampled,Sampler,SamplePoint,SampleMatrix,SampleType,ContainerType,ReportDryMatter,Priority,Total number of Analyses or Profiles,Price excl Tax,CAL1,,,,MicroBio,,
Analysis price,,,,,,,,,,,,,,
"Total Analyses or Profiles",,,,,,,,,,,,,9,,,
Total price excl Tax,,,,,,,,,,,,,,
"Sample 1", HHS14001,          3/9/2014,    3/9/2014,,Toilet,     Liquids,     Water,     Cup,          0,              Normal,  1,                                   0,             0,0,0,0,0,1
        """)

        # check that values are saved without errors
        arimport.setErrors([])
        arimport.save_header_data()
        arimport.save_sample_data()
        arimport.create_or_reference_batch()
        errors = arimport.getErrors()
        transaction.commit()
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
        transaction.commit()
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
        transaction.commit()


        bc = getToolByName(self.portal, 'bika_catalog')
        ars = bc(portal_type='AnalysisRequest')
        ar = ars[0]
        analyses = ar.getObject().getAnalyses(full_objects=True)
        for a in analyses:
            state = workflow.getInfoFor(a, 'review_state')
            if state == 'to_be_sampled':
                workflow.doActionFor(a, 'sample')
                transaction.commit()
            state = workflow.getInfoFor(a, 'review_state')
            if state == 'sampled':
                workflow.doActionFor(a, 'sample_due')
            state = workflow.getInfoFor(a, 'review_state')
            if state == 'sample_due':
                workflow.doActionFor(a, 'receive')
                transaction.commit()
        workflow.doActionFor(ar.getObject(), 'receive')
        transaction.commit()

        #Testing Import for Instrument
        path = os.path.dirname(__file__)
        filename = '%s/files/nexera' % path
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
                                    instrument='',
                                    advancetostate='submit'))
        context = self.portal
        results = Import(context, request)
        transaction.commit()
        text = 'Import finished successfully: 1 ARs and 2 results updated'
        if text not in results:
            self.fail("AR Import failed")
        analyses = ar.getObject().getAnalyses(full_objects=True)
        for an in analyses:
            state = workflow.getInfoFor(an, 'review_state')
            if state == 'to_be_verified':
                self.fail('Auto Transition occured for:{}'.format(an))
            if an.getKeyword() == 'Ca':
                if an.getResult() != '0.0':
                    self.fail("%s:Result did not get updated" % an.getKeyword())
            if an.getKeyword() == 'Ecoli':
                if an.getResult() != '0.8':
                    self.fail("%s:Result did not get updated" % an.getKeyword())



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestInstrumentImport))
    suite.layer = BIKA_SIMPLE_FIXTURE
    return suite
