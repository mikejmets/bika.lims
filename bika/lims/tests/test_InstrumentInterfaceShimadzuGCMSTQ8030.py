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
                      title='Water', Prefix='H2O')
        self.addthing(self.portal.bika_setup.bika_samplematrices,
                      'SampleMatrix', title='Liquids')
        self.addthing(self.portal.bika_setup.bika_samplepoints, 'SamplePoint',
                      title='Toilet')
        self.addthing(self.portal.bika_setup.bika_containertypes,
                      'ContainerType', title='Cup')
        self.addthing(self.portal.bika_setup.bika_arpriorities, 'ARPriority',
                      title='Normal', sortKey=1)
        a = self.addthing(self.portal.bika_setup.bika_analysisservices,
                          'AnalysisService', title='Ecoli', Keyword="ECO")
        #b = self.addthing(self.portal.bika_setup.bika_analysisservices,
        #                  'AnalysisService', title='Salmonella', Keyword="SAL")
        #ar_category = self.addthing(self.portal.bika_setup.bika_analysiscategories, 'AnalysisCategory',
        #              title='Metals')
        #c = self.addthing(self.portal.bika_setup.bika_analysisservices,
        #                  'AnalysisService', title='Color', Keyword="COL",
        #                    AnalysisCategory=ar_category.UID(),)
        #d = self.addthing(self.portal.bika_setup.bika_analysisservices,
        #                  'AnalysisService', title='Taste', Keyword="TAS")
        self.addthing(self.portal.bika_setup.bika_analysisprofiles,
                      'AnalysisProfile', title='MicroBio',
                      Service=[a.UID()])
        #self.addthing(self.portal.bika_setup.bika_analysisprofiles,
        #              'AnalysisProfile', title='Properties',
        #              Service=[c.UID(), d.UID()])

    #def setUp(self):
    #    super(TestInstrumentImport, self).setUp()
    #    login(self.portal, TEST_USER_NAME)
    #    clients = self.portal.clients
    #    self.client = self.addthing(self.portal.clients, 'Client',
    #                                title='Happy Hills', ClientID='HH')
    #    #bs = self.portal.bika_setup
    #    ## @formatter:off
    #    #self.client = self.addthing(clients, 'Client', title='Happy Hills', ClientID='HH')
    #    #contact = self.addthing(self.client, 'Contact', Firstname='Rita', Lastname='Mohale')
    #    ## Sample
    #    #sampletype = self.addthing(bs.bika_sampletypes, 'SampleType', title='1', Prefix='1')
    #    #ar_category = self.addthing(self.portal.bika_setup.bika_analysiscategories, 'AnalysisCategory',
    #    #              title='Metals')
    #    #analysis = self.addthing(self.portal.bika_setup.bika_analysis, 'Analysis',
    #    #              title='alphaPinene')
    #    #service = self.addthing(bs.bika_analysisservices, 
    #    #        'AnalysisService', 
    #    #        title='alphaPinene', 
    #    #        AnalysisKeyword="alphaPinene",
    #    #        AnalysisCategory=ar_category.UID(),)
    #    #bac = getToolByName(self.portal, 'bika_analysis_catalog')
    #    #analyses = bac(portal_type='Analysis')
    #    ## Create Sample
    #    #self.sample1 = self.addthing(self.client, 'Sample', SampleType=sampletype)
    #    #api.content.transition(obj=self.sample1, transition='sampling_workflow')
    #    #api.content.transition(obj=self.sample1, transition='sample')
    #    #api.content.transition(obj=self.sample1, transition='sample_due')
    #    #api.content.transition(obj=self.sample1, transition='receive')
    #    #transaction.commit()
    #    ## Create an AR
    #    #self.ar1 = self.addthing(self.client, 'AnalysisRequest', Contact=contact,
    #    #                        Sample=self.sample1, Analyses=[service], SamplingDate=DateTime())
    #    #import pdb; pdb.set_trace()
    #    #api.content.transition(obj=self.ar1, transition='sampling_workflow')
    #    #state = api.content.get_state(self.ar1)
    #    #if state == 'to_be_sampled':
    #    #    try:
    #    #        api.content.transition(obj=self.ar1, transition='sample')
    #    #        transaction.commit()
    #    #    except Exception, e:
    #    #        pass
    #    #state = api.content.get_state(self.ar1)
    #    ##api.content.transition(obj=self.ar1, transition='sample_due')
    #    #api.content.transition(obj=self.ar1, transition='receive')
    #    #state = api.content.get_state(self.ar1)
    #    #transaction.commit()
    #    #if state != 'sample_received':
    #    #    self.fail("Incorrect state for AR")

    def tearDown(self):
        super(TestInstrumentImport, self).setUp()
        login(self.portal, TEST_USER_NAME)

    def test_complete_valid_batch_import(self):
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
Samples,    ClientSampleID,    SamplingDate,DateSampled,SamplePoint,SampleMatrix,SampleType,ContainerType,ReportDryMatter,Priority,Total number of Analyses or Profiles,Price excl Tax,ECO,,,,MicroBio,,
Analysis price,,,,,,,,,,,,,,
"Total Analyses or Profiles",,,,,,,,,,,,,9,,,
Total price excl Tax,,,,,,,,,,,,,,
"Sample 1", HHS14001,          3/9/2014,    3/9/2014,   Toilet,     Liquids,     Water,     Cup,          0,              Normal,  1,                                   0,             0,0,0,0,0,1
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
        api.content.transition(obj=ars[0].getObject(), transition='receive')
        transaction.commit()
        #if not ars[0].getObject().getContact():
        #    self.fail('No Contact imported into ar.Contact field.')
        #l = len(ars)
        #if l != 4:
        #    self.fail('4 AnalysisRequests were not created!  We found %s' % l)
        #l = len(bc(portal_type='Sample'))
        #if l != 4:
        #    self.fail('4 Samples were not created!  We found %s' % l)
        #bac = getToolByName(self.portal, 'bika_analysis_catalog')
        #analyses = bac(portal_type='Analysis')
        #l = len(analyses)
        #if l != 12:
        #    self.fail('12 Analysis not found! We found %s' % l)
        #states = [workflow.getInfoFor(a.getObject(), 'review_state')
        #          for a in analyses]
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
        #if states != ['sample_due'] * 12:
        #    self.fail('Analysis states should all be sample_due, but are not!')

    #def test_BC_4(self):
    #    path = os.path.dirname(__file__)
    #    filename = '%s/files/GC-MS output.txt' % path
    #    if not os.path.isfile(filename):
    #        self.fail("File %s not found" % filename)
    #    data = open(filename, 'r').read()
    #    file = FileUpload(TestFile(cStringIO.StringIO(data)))
    #    request = TestRequest()
    #    request = TestRequest(form=dict(
    #                                submitted=True,
    #                                artoapply='received',
    #                                override='nooverride',
    #                                file=file,
    #                                sample='requestid',
    #                                instrument=''))
    #    context = self.portal
    #    results = Import(context, request)
    #    import pdb; pdb.set_trace()
    #    text = 'Import finished successfully: 1 ARs and 1 results updated'
    #    if text not in results:
    #        self.fail("AR did not get updated")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestInstrumentImport))
    suite.layer = BIKA_SIMPLE_FIXTURE
    return suite
