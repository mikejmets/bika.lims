# This file is part of Bika LIMS
#
# Copyright 2011-2016 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

""" Shimadzu ICPE-9000 Multitype
"""
from DateTime import DateTime
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import t
from bika.lims import logger
from bika.lims.browser import BrowserView
from bika.lims.idserver import renameAfterCreation
from bika.lims.utils import changeWorkflowState
from bika.lims.utils import tmpID
from cStringIO import StringIO
from datetime import datetime
from operator import itemgetter
from plone.i18n.normalizer.interfaces import IIDNormalizer
from zope.component import getUtility
import csv
import json
import plone
import re
import zope
import zope.event
from bika.lims.exportimport.instruments.resultsimport import InstrumentCSVResultsFileParser,\
    AnalysisResultsImporter
import traceback

title = "Shimadzu ICPE-9000 Multitype"


def Import(context, request):
    """ Read Shimadzu GICPE-9000 Multitype analysis results
    """
    form = request.form
    #TODO form['file'] sometimes returns a list
    infile = form['file'][0] if isinstance(form['file'],list) else form['file']
    artoapply = form['artoapply']
    override = form['override']
    sample = form.get('sample', 'requestid')
    instrument = form.get('instrument', None)
    errors = []
    logs = []

    # Load the most suitable parser according to file extension/options/etc...
    parser = None
    if not hasattr(infile, 'filename'):
        errors.append(_("No file selected"))
    parser = GCMSTQ8030GCMSMSCSVParser(infile)

    if parser:
        # Load the importer
        status = ['sample_received', 'attachment_due', 'to_be_verified']
        if artoapply == 'received':
            status = ['sample_received']
        elif artoapply == 'received_tobeverified':
            status = ['sample_received', 'attachment_due', 'to_be_verified']

        over = [False, False]
        if override == 'nooverride':
            over = [False, False]
        elif override == 'override':
            over = [True, False]
        elif override == 'overrideempty':
            over = [True, True]

        sam = ['getRequestID', 'getSampleID', 'getClientSampleID']
        if sample =='requestid':
            sam = ['getRequestID']
        if sample == 'sampleid':
            sam = ['getSampleID']
        elif sample == 'clientsid':
            sam = ['getClientSampleID']
        elif sample == 'sample_clientsid':
            sam = ['getSampleID', 'getClientSampleID']

        importer = GCMSTQ8030GCMSMSImporter(parser=parser,
                                           context=context,
                                           idsearchcriteria=sam,
                                           allowed_ar_states=status,
                                           allowed_analysis_states=None,
                                           override=over,
                                           instrument_uid=instrument)
        tbex = ''
        try:
            importer.process()
        except:
            tbex = traceback.format_exc()
        errors = importer.errors
        logs = importer.logs
        warns = importer.warns
        if tbex:
            errors.append(tbex)

    results = {'errors': errors, 'log': logs, 'warns': warns}

    return json.dumps(results)


class GCMSTQ8030GCMSMSCSVParser(InstrumentCSVResultsFileParser):

    def __init__(self, csv):
        InstrumentCSVResultsFileParser.__init__(self, csv)
        self._end_header = False
        self._quantitationresultsheader = []
        self._numline = 0

    def _parseline(self, line):
        return self.parse_quantitationesultsline(line)


    def parse_quantitationesultsline(self, line):
        """ Parses quantitation result lines
            Please see samples/GC-MS output.txt
            [MS Quantitative Results] section
        """

        # Metals Mix Method with IS longer cali\tCAL1\tBlank\t9/23/2016 11:54:59 AM\t\tMRC\tAs\tQUANT\t193.759\t1\tppb\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tAfter Drift Correction\t-0.0936625\t-0.1063610\t-0.1266098\t\t\t\t\t\t\t\t-0.1088778\t0.0166172\t15.26
        splitted = [token.strip() for token in line.split('\t')]
        quantitation = {'DefaultResult': 'Conc.'}
        for item in splitted:
            token = splitted[i]
            quantitation[colname] = token
            val = re.sub(r"\W", "", splitted[1])
            self._addRawResult(quantitation['ID#'],
                               values={val:quantitation},
                               override=True)


class GCMSTQ8030GCMSMSImporter(AnalysisResultsImporter):

    def __init__(self, parser, context, idsearchcriteria, override,
                 allowed_ar_states=None, allowed_analysis_states=None,
                 instrument_uid=''):
        AnalysisResultsImporter.__init__(self, parser, context, idsearchcriteria,
                                         override, allowed_ar_states,
                                         allowed_analysis_states,
                                         instrument_uid)
