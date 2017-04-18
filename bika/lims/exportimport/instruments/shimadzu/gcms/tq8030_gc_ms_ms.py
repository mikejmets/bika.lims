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
import zope
import zope.event
from bika.lims.exportimport.instruments.resultsimport import InstrumentCSVResultsFileParser,\
    AnalysisResultsImporter
import traceback

title = "Shimadzu GCMS-TQ8030 GC/MS/MS"


def Import(context, request):
    """ Read Shimadzu GCMS-TQ8030 GC/MS/MS analysis results
    """
    infile = request.form['amhq_file']
    fileformat = request.form['amhq_format']
    artoapply = request.form['amhq_artoapply']
    override = request.form['amhq_override']
    sample = request.form.get('amhq_sample', 'requestid')
    instrument = request.form.get('amhq_instrument', None)
    errors = []
    logs = []

    # Load the most suitable parser according to file extension/options/etc...
    parser = None
    if not hasattr(infile, 'filename'):
        errors.append(_("No file selected"))
    elif fileformat == 'csv':
        parser = GCMSTQ8030GCMSMSCSVParser(infile)
    else:
        errors.append(t(_("Unrecognized file format ${fileformat}",
                          mapping={"fileformat": fileformat})))

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

    HEADERTABLE_KEY = 'Header'
    HEADERKEY_FILENAME = 'Data File Name'
    HEADERKEY_OUTPUTDATE = 'Output Date'
    HEADERKEY_OUTPUTTIME = 'Output Time'
    QUANTITATIONRESULTS_KEY = 'MS Quantitative Results'
    QUANTITATIONRESULTS_NUMBEROFIDS = '# of IDs'
    QUANTITATIONRESULTS_NUMERICHEADERS = ('Mass', 'Ret.Time', 'Start Time', 
            'End Time',	'A/H', 'Area','Height' 'Conc.', 'Peak#', 
            'Std.Ret.Time', '3rd', '2nd', '1st', 'Constant', 'Ref.Ion Area', 
            'Ref.Ion Height', 'Ref.Ion Set Ratio', 'Ref.Ion Ratio', 'Recovery',
            'SI', 'Ref.Ion1 m/z', 'Ref.Ion1 Area', 'Ref.Ion1 Height', 
            'Ref.Ion1 Set Ratio', 'Ref.Ion1 Ratio', 'Ref.Ion2 m/z', 
            'Ref.Ion2 Area', 'Ref.Ion2 Height', 'Ref.Ion2 Set Ratio',
            'Ref.Ion2 Ratio', 'Ref.Ion3 m/z', 'Ref.Ion3 Area', 
            'Ref.Ion3 Height',	'Ref.Ion3 Set Ratio', 'Ref.Ion3 Ratio',
            'Ref.Ion4 m/z', 'Ref.Ion4 Area', 'Ref.Ion4 Height', 
            'Ref.Ion4 Set Ratio', 'Ref.Ion4 Ratio', 'Ref.Ion5 m/z', 
            'Ref.Ion5 Area', 'Ref.Ion5 Height', 'Ref.Ion5 Set Ratio',
            'Ref.Ion5 Ratio', 'Ret. Index', 'S/N', 'Threshold',
            )
    QUANTITATIONRESULTS_COMPOUNDCOLUMN = 'Compound'
    COMMAS = ','

    def __init__(self, csv):
        InstrumentCSVResultsFileParser.__init__(self, csv)
        self._end_header = False
        #self._end_sequencetable = False
        #self._sequences = []
        self._sequencesheader = []
        self._quantitationresultsheader = []
        self._numline = 0

    def getAttachmentFileType(self):
        return "Agilent's Masshunter Quant CSV"

    def _parseline(self, line):
        if self._end_header == False:
            return self.parse_headerline(line)
        elif self._end_sequencetable == False:
            return self.parse_sequencetableline(line)
        else:
            return self.parse_quantitationesultsline(line)

    def parse_headerline(self, line):
        """ Parses header lines

            Header example:
            Batch Info,2013-03-20T07:11:09.9053262-07:00,2013-03-20T07:12:55.5280967-07:00,2013-03-20T07:11:07.1047817-07:00,,,,,,,,,,,,,,
            Batch Data Path,D:\MassHunter\Data\130129\QuantResults\130129LS.batch.bin,,,,,,,,,,,,,,,,
            Analysis Time,3/20/2013 7:11 AM,Analyst Name,Administrator,,,,,,,,,,,,,,
            Report Time,3/20/2013 7:12 AM,Reporter Name,Administrator,,,,,,,,,,,,,,
            Last Calib Update,3/20/2013 7:11 AM,Batch State,Processed,,,,,,,,,,,,,,
            ,,,,,,,,,,,,,,,,,



            Data File Name,C:\GCMSsolution\Data\October\1-16-02249-001_CD_10172016_2.qgd
            Output Date,10/18/2016
            Output Time,12:04:11 PM
            ,,
        """
        if self._end_header == True:
            # Header already processed
            return 0

        if line.startswith(self.SEQUENCETABLE_KEY):
            self._end_header = True
            if len(self._header) == 0:
                self.err("No header found", numline=self._numline)
                return -1
            return 0

        splitted = [token.strip() for token in line.split(',')]

        # Batch Info,2013-03-20T07:11:09.9053262-07:00,2013-03-20T07:12:55.5280967-07:00,2013-03-20T07:11:07.1047817-07:00,,,,,,,,,,,,,,
        if splitted[0] == self.HEADERKEY_BATCHINFO:
            if self.HEADERKEY_BATCHINFO in self._header:
                self.warn("Header Batch Info already found. Discarding",
                          numline=self._numline, line=line)
                return 0

            self._header[self.HEADERKEY_BATCHINFO] = []
            for i in range(len(splitted) - 1):
                if splitted[i + 1]:
                    self._header[self.HEADERKEY_BATCHINFO].append(splitted[i + 1])

        # Batch Data Path,D:\MassHunter\Data\130129\QuantResults\130129LS.batch.bin,,,,,,,,,,,,,,,,
        elif splitted[0] == self.HEADERKEY_BATCHDATAPATH:
            if self.HEADERKEY_BATCHDATAPATH in self._header:
                self.warn("Header Batch Data Path already found. Discarding",
                          numline=self._numline, line=line)
                return 0;

            if splitted[1]:
                self._header[self.HEADERKEY_BATCHDATAPATH] = splitted[1]
            else:
                self.warn("Batch Data Path not found or empty",
                          numline=self._numline, line=line)

        # Analysis Time,3/20/2013 7:11 AM,Analyst Name,Administrator,,,,,,,,,,,,,,
        elif splitted[0] == self.HEADERKEY_ANALYSISTIME:
            if splitted[1]:
                try:
                    d = datetime.strptime(splitted[1], "%m/%d/%Y %I:%M %p")
                    self._header[self.HEADERKEY_ANALYSISTIME] = d
                except ValueError:
                    self.err("Invalid Analysis Time format",
                             numline=self._numline, line=line)
            else:
                self.warn("Analysis Time not found or empty",
                          numline=self._numline, line=line)

            if splitted[2] and splitted[2] == self.HEADERKEY_ANALYSTNAME:
                if splitted[3]:
                    self._header[self.HEADERKEY_ANALYSTNAME] = splitted[3]
                else:
                    self.warn("Analyst Name not found or empty",
                              numline=self._numline, line=line)
            else:
                self.err("Analyst Name not found",
                         numline=self._numline, line=line)

        # Report Time,3/20/2013 7:12 AM,Reporter Name,Administrator,,,,,,,,,,,,,,
        elif splitted[0] == self.HEADERKEY_REPORTTIME:
            if splitted[1]:
                try:
                    d = datetime.strptime(splitted[1], "%m/%d/%Y %I:%M %p")
                    self._header[self.HEADERKEY_REPORTTIME] = d
                except ValueError:
                    self.err("Invalid Report Time format",
                         numline=self._numline, line=line)
            else:
                self.warn("Report time not found or empty",
                          numline=self._numline, line=line)


            if splitted[2] and splitted[2] == self.HEADERKEY_REPORTERNAME:
                if splitted[3]:
                    self._header[self.HEADERKEY_REPORTERNAME] = splitted[3]
                else:
                    self.warn("Reporter Name not found or empty",
                              numline=self._numline, line=line)

            else:
                self.err("Reporter Name not found",
                         numline=self._numline, line=line)


        # Last Calib Update,3/20/2013 7:11 AM,Batch State,Processed,,,,,,,,,,,,,,
        elif splitted[0] == self.HEADERKEY_LASTCALIBRATION:
            if splitted[1]:
                try:
                    d = datetime.strptime(splitted[1], "%m/%d/%Y %I:%M %p")
                    self._header[self.HEADERKEY_LASTCALIBRATION] = d
                except ValueError:
                    self.err("Invalid Last Calibration time format",
                             numline=self._numline, line=line)

            else:
                self.warn("Last Calibration time not found or empty",
                          numline=self._numline, line=line)


            if splitted[2] and splitted[2] == self.HEADERKEY_BATCHSTATE:
                if splitted[3]:
                    self._header[self.HEADERKEY_BATCHSTATE] = splitted[3]
                else:
                    self.warn("Batch state not found or empty",
                              numline=self._numline, line=line)

            else:
                self.err("Batch state not found",
                         numline=self._numline, line=line)


        return 0


    def parse_quantitationesultsline(self, line):
        """ Parses quantitation result lines

            Quantitation results example:
            Quantitation Results,,,,,,,,,,,,,,,,,
            Target Compound,25-OH D3+PTAD+MA,,,,,,,,,,,,,,,,
            Data File,Compound,ISTD,Resp,ISTD Resp,Resp Ratio, Final Conc,Exp Conc,Accuracy,,,,,,,,,
            prerunrespchk.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,5816,274638,0.0212,0.9145,,,,,,,,,,,
            DSS_Nist_L1.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,6103,139562,0.0437,1.6912,,,,,,,,,,,
            DSS_Nist_L2.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,11339,135726,0.0835,3.0510,,,,,,,,,,,
            DSS_Nist_L3.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,15871,141710,0.1120,4.0144,,,,,,,,,,,
            mid_respchk.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,4699,242798,0.0194,0.8514,,,,,,,,,,,
            DSS_Nist_L3-r002.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,15659,129490,0.1209,4.3157,,,,,,,,,,,
            UTAK_DS_L1-r001.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,29846,132264,0.2257,7.7965,,,,,,,,,,,
            UTAK_DS_L1-r002.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,28696,141614,0.2026,7.0387,,,,,,,,,,,
            post_respchk.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,5022,231748,0.0217,0.9315,,,,,,,,,,,
            ,,,,,,,,,,,,,,,,,
            Target Compound,25-OH D2+PTAD+MA,,,,,,,,,,,,,,,,
            Data File,Compound,ISTD,Resp,ISTD Resp,Resp Ratio, Final Conc,Exp Conc,Accuracy,,,,,,,,,
            prerunrespchk.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,6222,274638,0.0227,0.8835,,,,,,,,,,,
            DSS_Nist_L1.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,1252,139562,0.0090,0.7909,,,,,,,,,,,
            DSS_Nist_L2.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,3937,135726,0.0290,0.9265,,,,,,,,,,,
            DSS_Nist_L3.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,826,141710,0.0058,0.7697,,,,,,,,,,,
            mid_respchk.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,7864,242798,0.0324,0.9493,,,,,,,,,,,
            DSS_Nist_L3-r002.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,853,129490,0.0066,0.7748,,,,,,,,,,,
            UTAK_DS_L1-r001.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,127496,132264,0.9639,7.1558,,,,,,,,,,,
            UTAK_DS_L1-r002.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,135738,141614,0.9585,7.1201,,,,,,,,,,,
            post_respchk.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,6567,231748,0.0283,0.9219,,,,,,,,,,,
            ,,,,,,,,,,,,,,,,,
        """

        # Quantitation Results,,,,,,,,,,,,,,,,,
        # prerunrespchk.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,5816,274638,0.0212,0.9145,,,,,,,,,,,
        # mid_respchk.d,25-OH D3+PTAD+MA,25-OH D3d3+PTAD+MA,4699,242798,0.0194,0.8514,,,,,,,,,,,
        # post_respchk.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,6567,231748,0.0283,0.9219,,,,,,,,,,,
        # ,,,,,,,,,,,,,,,,,
        if line.startswith(self.QUANTITATIONRESULTS_KEY) \
            or line.startswith(self.QUANTITATIONRESULTS_PRERUN) \
            or line.startswith(self.QUANTITATIONRESULTS_MIDRUN) \
            or line.startswith(self.QUANTITATIONRESULTS_POSTRUN) \
            or line.startswith(self.COMMAS):

            # Nothing to do, continue
            return 0

        # Data File,Compound,ISTD,Resp,ISTD Resp,Resp Ratio, Final Conc,Exp Conc,Accuracy,,,,,,,,,
        if line.startswith(self.QUANTITATIONRESULTS_HEADER_DATAFILE):
            self._quantitationresultsheader = [token.strip() for token in line.split(',') if token.strip()]
            return 0

        # Target Compound,25-OH D3+PTAD+MA,,,,,,,,,,,,,,,,
        if line.startswith(self.QUANTITATIONRESULTS_TARGETCOMPOUND):
            # New set of Quantitation Results
            splitted = [token.strip() for token in line.split(',')]
            if not splitted[1]:
                self.warn("No Target Compound found",
                          numline=self._numline, line=line)
            return 0

        # DSS_Nist_L1.d,25-OH D2+PTAD+MA,25-OH D3d3+PTAD+MA,1252,139562,0.0090,0.7909,,,,,,,,,,,
        splitted = [token.strip() for token in line.split(',')]
        quantitation = {}
        for colname in self._quantitationresultsheader:
            quantitation[colname] = ''

        for i in range(len(splitted)):
            token = splitted[i]
            if i < len(self._quantitationresultsheader):
                colname = self._quantitationresultsheader[i]
                if token and colname in self.QUANTITATIONRESULTS_NUMERICHEADERS:
                    try:
                        quantitation[colname] = float(token)
                    except ValueError:
                        self.warn(
                            "No valid number ${token} in column ${index} (${column_name})",
                            mapping={"token": token,
                                     "index": str(i + 1),
                                     "column_name": colname},
                            numline=self._numline, line=line)
                        quantitation[colname] = token
                else:
                    quantitation[colname] = token
            elif token:
                self.err("Orphan value in column ${index} (${token})",
                         mapping={"index": str(i+1),
                                  "token": token},
                         numline=self._numline, line=line)

        if self.QUANTITATIONRESULTS_COMPOUNDCOLUMN in quantitation:
            compound = quantitation[self.QUANTITATIONRESULTS_COMPOUNDCOLUMN]

            # Look for sequence matches and populate rawdata
            datafile = quantitation.get(self.QUANTITATIONRESULTS_HEADER_DATAFILE, '')
            if not datafile:
                self.err("No Data File found for quantitation result",
                         numline=self._numline, line=line)

            else:
                seqs = [sequence for sequence in self._sequences \
                        if sequence.get('Data File', '') == datafile]
                if len(seqs) == 0:
                    self.err("No sample found for quantitative result ${data_file}",
                             mapping={"data_file": datafile},
                             numline=self._numline, line=line)
                elif len(seqs) > 1:
                    self.err("More than one sequence found for quantitative result: ${data_file}",
                             mapping={"data_file": datafile},
                             numline=self._numline, line=line)
                else:
                    objid = seqs[0].get(self.SEQUENCETABLE_HEADER_SAMPLENAME, '')
                    if objid:
                        quantitation['DefaultResult'] = 'Final Conc'
                        quantitation['Remarks'] = _("Autoimport")
                        rows = self.getRawResults().get(objid, [])
                        raw = rows[0] if len(rows) > 0 else {}
                        raw[compound] = quantitation
                        self._addRawResult(objid, raw, True)
                    else:
                        self.err("No valid sequence for ${data_file}",
                                 mapping={"data_file": datafile},
                                 numline=self._numline, line=line)
        else:
            self.err("Value for column '${column}' not found",
                     mapping={"column": self.QUANTITATIONRESULTS_COMPOUNDCOLUMN},
                     numline=self._numline, line=line)


class GCMSTQ8030GCMSMSImporter(AnalysisResultsImporter):

    def __init__(self, parser, context, idsearchcriteria, override,
                 allowed_ar_states=None, allowed_analysis_states=None,
                 instrument_uid=''):
        AnalysisResultsImporter.__init__(self, parser, context, idsearchcriteria,
                                         override, allowed_ar_states,
                                         allowed_analysis_states,
                                         instrument_uid)
