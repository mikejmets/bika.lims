import logging
import json
import cStringIO
import os
import shutil
import smtplib
from plone import api as ploneapi
from bika.lims.browser import BrowserView
from bika.lims.utils import tmpID
from bika.lims import api
from bika.lims.exportimport import instruments
from bika.lims.exportimport.instruments.generic.genericthreecols \
        import Import as GenericImport
from collective.taskqueue.interfaces import ITaskQueue
from Products.CMFPlone.utils import _createObjectByType
from Products.CMFCore.utils import getToolByName
from zope.component import getUtility
from zope.component import queryUtility
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
        #NOTE: This is for running the test
        send_email = True
        messages = []
        if analysts_folder == '':
            send_email = False
            this_dir = os.path.dirname(os.path.abspath(__file__))
            analysts_folder = this_dir.replace('exportimport', 
                                               'tests/files/importresult')

        #TODO: Maybe get all analysts
        errors = []
        archive = []
        if not os.path.isdir(analysts_folder):
            logger.error('Instrument Result Folder not found: {}'.format(analysts_folder))
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
        for folder in os.listdir(analysts_folder):
            # get analyst folder
            analyst_filepath = os.path.join(analysts_folder, folder)
            # Get the analyst user
            analyst_folder = None
            for analyst in analysts:
                if folder == analyst.getUserName():
                    analyst_folder =  folder
                    analyst_email = analyst.getProperty('email')
                    analyst_name = analyst.getProperty('fullname')
            if not analyst_folder:
                msg = 'User {} found is not an Analyst'.format(analyst_filepath)
                errors.append(msg)
                continue

            task_queue = queryUtility(ITaskQueue, name='import-results')
            for instrument in  os.listdir(analyst_filepath):
                # get instrument
                instrument_model = None
                for myinstrument in instruments_catalog:
                    if myinstrument.Title == instrument:
                        ins_obj = myinstrument.getObject()
                        instrument_model = ins_obj.getResultImporterId()
                        break
                if not instrument_model:
                    msg = 'Instrument: {} on path {} Not Found'.format(
                                                            instrument,
                                                            analyst_filepath)
                    errors.append(msg)
                    continue
                myimporter = []
                exim = [i for i in exims if i[0] == instrument_model]
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
                    from bika.lims.exportimport.instruments.shimadzu.nexera.LCMS8050 import Import
                elif import_importer == 'agilent.masshunter.masshunter':
                    from bika.lims.exportimport.instruments.agilent.masshunter.masshunter import Import

                instrument_path = os.path.join(analyst_filepath, instrument)
                archives_dir = os.path.join(instrument_path, 'archives')
                if not os.path.exists(archives_dir):
                    os.makedirs(archives_dir)
                wip_dir = os.path.join(instrument_path, 'wip')
                if not os.path.exists(wip_dir):
                    os.makedirs(wip_dir)
                for fname in os.listdir(instrument_path):
                    if fname == 'archives':
                        continue
                    current_file = os.path.join(instrument_path,fname)
                    if os.path.isfile(current_file):
                        temp_file = os.path.join(wip_dir, fname)
                        try:
                            os.rename(current_file, temp_file)
                        except Exception, e:
                            try:
                                shutil.move(current_file, temp_file)
                            except Exception, e:
                                msg = 'Cannot move file %s to %s (%s)' % (
                                        current_file, temp_file, str(e))
                                errors.append(msg)
                                continue
                        logger.info('Moved file %s to %s' % (current_file, temp_file))
                        if task_queue is not None:
                            path = [i for i in self.context.getPhysicalPath()]
                            path.append('async_import_instrument_result')
                            path = '/'.join(path)
                            params = {
                                    'instrument_path': instrument_path,
                                    'fname': fname,
                                    'analyst_folder': analyst_folder,
                                    'analyst_email': analyst_email,
                                    'analyst_name': analyst_name,
                                    'import_importer': import_importer,
                                    }
                            logger.info('Queue Task: path=%s; params=%s' % (path, params))
                            task_id = task_queue.add(path,
                                    method='POST',
                                    params=params)
                        else:
                            logger.info('No import-results Task Queue found')
                            data = open(temp_file, 'r').read()
                            file = FileUpload(FileToUpload(
                                        cStringIO.StringIO(data),fname))

                            request.form = dict(submitted=True,
                                                artoapply='received_tobeverified',
                                                override='nooverride',
                                                file=file,
                                                sample='requestid',
                                                instrument='',
                                                advancetostate = 'submit',
                                                analyst=analyst_folder,
                                                )
                            context = self.portal
                            try:
                                if '2-dimen' in fname.lower():
                                    results = GenericImport(context, request)
                                else:
                                    results = Import(context, request)
                            except Exception, e:
                                errors.append(e)
                            archive_file = os.path.join(archives_dir, fname)
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
                            if send_email:
                                self._email_analyst(
                                        analyst_email, analyst_name, message)
                            else:
                                messages.append(message)

                # Avoid having Import from multiple module at the same time
                if 'Import' in globals():
                    del Import

        logger.info('Instrument Results Importer Done')
        if len(errors):
            if send_email:
                self._email_errors(errors)
        return ('Done', messages, errors)

    def async_import_instrument_result(self):
        logger.info('Async import instrument result start')
        msgs = []
        errors = []
        request = self.request
        form = self.request.form
        instrument_path = form.get('instrument_path', '')
        if len(instrument_path) == 0:
            msgs.append('No Instrument folder provided')
            self._email_errors(msgs)
            return
        fname = form.get('fname', '')
        if len(fname) == 0:
            msgs.append(
                    'No file name provided on path: {}'.format(
                        instrument_path))
            self._email_errors(msgs)
            return
        result_file = os.path.join(instrument_path, 'wip', fname)
        analyst_folder = form.get('analyst_folder', '')
        if len(analyst_folder) == 0:
            msgs.append('No user/analyst provided')
            self._email_errors(msgs)
            return
        analyst_email = form.get('analyst_email', '')
        if len(analyst_email) == 0:
            msgs.append('No analyst email provided')
            self._email_errors(msgs)
            return
        analyst_name = form.get('analyst_name', '')
        if len(analyst_name) == 0:
            msgs.append('No analsyt name provided')
            self._email_errors(msgs)
            return
        import_importer = form.get('import_importer', '')
        if len(import_importer) == 0:
            msgs.append('Import not provided')
            self._email_errors(msgs)
            return
        if import_importer == 'shimadzu.gcms.tq8030':
            from bika.lims.exportimport.instruments.shimadzu.gcms.tq8030 import Import
        elif import_importer == 'shimadzu.gcms.qp2010se':
            from bika.lims.exportimport.instruments.shimadzu.gcms.qp2010se import Import
        elif import_importer == 'shimadzu.icpe.multitype':
            from bika.lims.exportimport.instruments.shimadzu.icpe.multitype import Import
        elif import_importer == 'shimadzu.nexera.LC2040C':
            from bika.lims.exportimport.instruments.shimadzu.nexera.LC2040C import Import
        elif import_importer == 'shimadzu.nexera.LCMS8050':
            from bika.lims.exportimport.instruments.shimadzu.nexera.LMS8050 import Import
        elif import_importer == 'agilent.masshunter.masshunter':
            from bika.lims.exportimport.instruments.agilent.masshunter.masshunter import Import

        logger.info('Async import instrument result ready')

        try:
            data = open(result_file, 'r').read()
        except Exception, e:
            msgs.append('Could not open results file %s' % result_file)
            self._email_errors(msgs)
            return
        try:
            afile = FileUpload(FileToUpload(cStringIO.StringIO(data),fname))
        except Exception, e:
            msgs.append('Could not upload results file %s' % fname)
            self._email_errors(msgs)
            return

        request.form = dict(submitted=True,
                            artoapply='received_tobeverified',
                            override='nooverride',
                            file=afile,
                            sample='requestid',
                            instrument='',
                            advancetostate = 'submit',
                            analyst=analyst_folder,
                            )
        context = self.portal
        try:
            if '2-dimen' in fname.lower():
                results = GenericImport(context, request)
            else:
                results = Import(context, request)
        except Exception, e:
            errors.append(e)
            logger.error('Async import instrument result import: %s' % errors)
            results = '[]'

        archive_file = os.path.join(instrument_path, 'archives', fname)
        try:
            os.rename(result_file, archive_file)
        except Exception, e:
            try:
                os.remove(archive_file)
                os.rename(result_file, archive_file)
            except:
                logger.error('Async import instrument result: cannot move %s to %s' % (result_file, archive_file))


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
        self._email_analyst(analyst_email, analyst_name, message)
        if 'Import' in globals():
            del Import
        logger.info('Async import instrument result done')

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
        #Exit if mail alread sent
        email_file_name = '/tmp/result_import_email'
        if os.path.exists(email_file_name):
            email_file = open(email_file_name, 'r')
            file_contents = email_file.read()
            email_file.close()
            if mail_text == file_contents:
                logger.info('Skip sys admin error email')
                return
        email_file = open(email_file_name, 'w')
        email_file.write(mail_text)
        email_file.close()
        try:
            logger.info('Email Errors complete: %s' % to_email)
            return mail_host.send(
                        mail_text, to_email, from_email,
                        subject=subject, charset="utf-8", immediate=True)
        except smtplib.SMTPRecipientsRefused:
            raise smtplib.SMTPRecipientsRefused(
                    'Recipient address rejected by server')

    def _email_analyst(self, to_email, name, message):
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
        subject = 'Instrument Results Import'
        mail_text = mail_template.format(
                        name=name,
                        message=message)
        try:
            result = mail_host.send(
                        mail_text, to_email, from_email,
                        subject=subject, charset="utf-8", immediate=True)
            logger.info('Email Analyst complete: %s' % to_email)
            return result
        except smtplib.SMTPRecipientsRefused:
            logger.info('Email Analyst SMTP Error: %s' % to_email)
            raise smtplib.SMTPRecipientsRefused('Recipient address rejected by server')
        except Exception, e:
            logger.info('Email Analyst %s Unknown error: %s' % (to_email, e))
