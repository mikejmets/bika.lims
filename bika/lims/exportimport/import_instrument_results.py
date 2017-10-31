import logging
import json
import cStringIO
import os
import smtplib
from plone import api as ploneapi
from bika.lims.browser import BrowserView
from bika.lims.utils import tmpID
from bika.lims import api
from bika.lims.exportimport import instruments
from collective.taskqueue.interfaces import ITaskQueue
from Products.CMFPlone.utils import _createObjectByType
from Products.CMFCore.utils import getToolByName
from zope.component import getUtility
from zope.publisher.browser import FileUpload

logger = logging.getLogger("bika.lims.exportimport.import_instrument_results")

class FileToUpload(object):
    def __init__(self, file, filename):
        self.file = file
        self.headers = {}
        self.filename = filename

class ImportInstrumentResultsView(BrowserView):

    def import_instrument_results(self):
        """ 
        """
        logger.info('Inside import_instrument_results')
        request = self.request
        bsc = api.get_tool("bika_setup_catalog")
        analysts_folder = os.environ.get('INSTRUMENT_RESULTS_IMPORTER', '')
        errors = []
        archive = []
        if not os.path.isdir(analysts_folder):
            logger.info('Instrument Result Folder not found: {}'.format(analysts_folder))
            return 'Folder: {} not found'.format(analysts_folder)
        exims = []
        all_instruments = instruments.__all__
        for exim_id in instruments.__all__:
            exim = instruments.getExim(exim_id)
            exims.append((exim_id, exim.title))
        exims.sort(lambda x, y: cmp(x[1].lower(), y[1].lower()))

        analysts = api.get_users_by_roles('Analyst')
        instruments_catalog = bsc(portal_type='Instrument',
                          inactive_state='active',
                          sort_on="sortable_title",
                          sort_order="ascending")
        for analyst_folder in os.listdir(analysts_folder):
            # get analyst folder
            analyst_filepath = os.path.join(analysts_folder, analyst_folder)
            # Get the analyst user
            self.user = None
            for analyst in analysts:
                if analyst_folder == analyst.getUserName():
                    self.user =  analyst_folder
                    email_analyst = analyst
            if not self.user:
                msg = 'User {} found is not an Analyst'.format(analyst_filepath)
                errors.append(msg)
                continue

            for instrument in  os.listdir(analyst_filepath):
                # get instrument
                instrument_model = None
                for myinstrument in instruments_catalog:
                    if myinstrument.Title == instrument:
                        instrument_model = myinstrument.getObject().getModel()
                        break
                if not instrument_model:
                    msg = 'Instrument: {} on path {} Not Found'.format(
                                                            instrument_model,
                                                            analyst_filepath)
                    errors.append(msg)
                    continue
                myimporter = []
                exim = [i for i in exims if i[1] == instrument_model]
                if len(exim) > 0:
                    myimporter = exim[0]
                    import_importer = myimporter[0]
                else:
                    msg = 'Instrument Importer with {} model not found'.format(instrument_model)
                    errors.append(msg)
                    continue
                if import_importer == 'shimadzu.gcms.tq8030':
                    from bika.lims.exportimport.instruments.shimadzu.gcms.tq8030 import Import
                elif import_importer == 'shimadzu.gcms.qp2010se':
                    from bika.lims.exportimport.instruments.shimadzu.gcms.qp2010se import Import
                elif import_importer == 'shimadzu.icpe.multitype':
                    from bika.lims.exportimport.instruments.shimadzu.icpe.multitype import Import
                elif import_importer == 'shimadzu.nexera.LC2040C':
                    from bika.lims.exportimport.instruments.shimadzu.nexera.LC2040C import Import
                elif import_importer == 'shimadzu.nexera.LCMS8050':
                    from bika.lims.exportimport.instruments.shimadzu.nexera.CMS8050 import Import
                elif import_importer == 'agilent.masshunter.masshunter':
                    from bika.lims.exportimport.instruments.agilent.masshunter.masshunter import Import

                instrument_path = os.path.join(analyst_filepath, instrument)
                archives_dir = '%s/archives' % instrument_path
                if not os.path.exists(archives_dir):
                    os.makedirs(archives_dir)
                wip_dir = '%s/wip' % instrument_path
                if not os.path.exists(wip_dir):
                    os.makedirs(wip_dir)
                for fname in os.listdir(instrument_path):
                    if fname == 'archives':
                        continue
                    current_file = os.path.join(instrument_path,fname)
                    if os.path.isfile(current_file):
                        temp_file = '{}/{}'.format(wip_dir, fname)
                        try:
                            os.rename(current_file, temp_file)
                        except Exception, e:
                            os.remove(temp_file)
                            os.rename(current_file, temp_file)
                        data = open(temp_file, 'r').read()
                        file = FileUpload(FileToUpload(cStringIO.StringIO(data),fname))

                        request.form = dict(submitted=True,
                                            artoapply='received_tobeverified',
                                            override='nooverride',
                                            file=file,
                                            sample='requestid',
                                            instrument='',
                                            advancetostate = 'submit',
                                            analyst=self.user,
                                            )
                        context = self.portal
                        try:
                            if '2-dimen' in fname.lower():
                                from bika.lims.exportimport.instruments.generic.genericthreecols import Import as GenericImport
                                results = GenericImport(context, request)
                            else:
                                results = Import(context, request)
                        except Exception, e:
                            errors.append(e)
                        archive_file = '{}/{}'.format(archives_dir, fname)
                        try:
                            os.rename(temp_file, archive_file)
                        except Exception, e:
                            os.remove(archive_file)
                            os.rename(temp_file, archive_file)

                        report = json.loads(results)
                        result_to_return = []
                        if len(report['log']) > 0:
                            result_to_return.append('Log:')
                            for l in report['log']:
                                result_to_return.append(l)
                        if len(report['errors']) > 0:
                            result_to_return.append('Errors:')
                            for e in report['errors']:
                                result_to_return.append(e)
                        if len(report['warns']) > 0:
                            result_to_return.append('Warnings:')
                            for w in report['warns']:
                                result_to_return.append(w)
                        message = '\n '.join(result_to_return)
                        self._email_analyst(email_analyst, message)

                # Avoid having Import from multiple module at the same time
                if 'Import' in globals():
                    del Import

        logger.info('Instrument Results Importer Done')
        if len(errors):
            self._email_analyst(email_analyst, message)
        return ('Done', errors)

    def _email_errors(self, errors):
        message = '\n'.join(errors)
        mail_template = """
Dear Sys Admin,

Instrument Results Importer has completed with the following errors:
{message}

Cheers
Bika LIMS
"""
        portal = ploneapi.portal.get()
        mail_host = ploneapi.portal.get_tool(name='MailHost')
        from_email= mail_host.email_from_address
        to_email = from_email
        subject = 'Instrument Results Import Errors'
        mail_text = mail_template.format(message=message)
        try:
            logger.info('Email Errors complete: %s' % to_email)
            return mail_host.send(
                        mail_text, to_email, from_email,
                        subject=subject, charset="utf-8", immediate=True)
        except smtplib.SMTPRecipientsRefused:
            raise smtplib.SMTPRecipientsRefused('Recipient address rejected by server')

    def _email_analyst(self, member, message):
        mail_template = """
Dear {name},

Instrument Results Importer has completed with the following messages:
{message}

Cheers
Bika LIMS
"""
        portal = ploneapi.portal.get()
        mail_host = ploneapi.portal.get_tool(name='MailHost')
        from_email= mail_host.email_from_address
        to_email = member.getProperty('email')
        subject = 'Instrument Results Import'
        mail_text = mail_template.format(
                        name=member.getProperty('fullname'),
                        message=message)
        try:
            logger.info('Email Analyst complete: %s' % to_email)
            return mail_host.send(
                        mail_text, to_email, from_email,
                        subject=subject, charset="utf-8", immediate=True)
        except smtplib.SMTPRecipientsRefused:
            raise smtplib.SMTPRecipientsRefused('Recipient address rejected by server')
