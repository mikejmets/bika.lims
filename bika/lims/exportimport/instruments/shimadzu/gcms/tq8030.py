# This file is part of Bika LIMS
#
# Copyright 2011-2016 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

""" Shimadzu GCMS-TQ8030 GC/MS/MS
"""
from DateTime import DateTime
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import api
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

title = "Shimadzu GCMS-TQ8030 GC/MS/MS"

def Import(context, request):
    """ Read Shimadzu GCMS-TQ8030 GC/MS/MS analysis results
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
    parser = GCMSQP2010SECSVParser(infile)

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
                                           instrument_uid=instrument,
                                           form=form)
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

class GCMSQP2010SECSVParser(InstrumentCSVResultsFileParser):

    def __init__(self, csv):
        InstrumentCSVResultsFileParser.__init__(self, csv)
        self._currentresultsheader = []
        self._currentanalysiskw = ''
        self._numline = 0

    def _parseline(self, line):
        return self.parse_resultsline(line)

    def parse_resultsline(self, line):
        """ Parses result lines
        """

        split_row = [token.strip() for token in line.split('\t')]
        if len(split_row) == 1:
            self._currentanalysiskw = split_row[0]
            return 0

        #'Average\t\t-----\t-----\t-----\t-----\t-----\t\t-----\t\t\t\t-----'
        elif split_row[0] == 'Average':
            return 0
        #'%RSD\t\t-----\t-----\t-----\t-----\t-----\t\t-----\t\t\t\t-----'
        elif split_row[0] == '%RSD':
            return 0
        #'Maximum\t\t-----\t-----\t-----\t-----\t-----\t\t-----\t\t\t\t-----'
        elif split_row[0] == 'Maximum':
            return 0
        #'Minimum\t\t-----\t-----\t-----\t-----\t-----\t\t-----\t\t\t\t-----'
        elif split_row[0] == 'Minimum':
            return 0
        #'Std. Dev.\t\t-----\t-----\t-----\t-----\t-----\t\t-----\t\t\t\t----'
        elif split_row[0] == 'Std. Dev.':
            return 0
        else:
            self._currentresultsheader = ['Title%s' % i for i in range(len(split_row))]
            _results = {'DefaultResult': 'Title3'}
            _results.update(dict(zip(self._currentresultsheader, split_row)))

            result = _results[_results['DefaultResult']]
            column_name = _results['DefaultResult']
            result = self.zeroValueDefaultInstrumentResults(
                                                    column_name, result, line)
            _results[_results['DefaultResult']] = result

            val = re.sub(r"\W", "", self._currentanalysiskw)
            self._addRawResult(_results['Title1'],
                               values={val:_results},
                               override=False)

    def zeroValueDefaultInstrumentResults(self, column_name, result, line):
        result = str(result)
        if result.startswith('--') or result == '' or result == 'ND':
            return 0.0

        try:
            result = float(result)
            if result < 0.0:
                result  = 0.0
        except ValueError:
            self.err(
                "No valid number ${result} in column (${column_name})",
                mapping={"result": result,
                         "column_name": column_name},
                numline=self._numline, line=line)
            return
        return result

class GCMSTQ8030GCMSMSImporter(AnalysisResultsImporter):

    def __init__(self, parser, context, idsearchcriteria, override,
                 allowed_ar_states=None, allowed_analysis_states=None,
                 instrument_uid='', form=None):
        AnalysisResultsImporter.__init__(self, parser, context, idsearchcriteria,
                                         override, allowed_ar_states,
                                         allowed_analysis_states,
                                         instrument_uid,form)
