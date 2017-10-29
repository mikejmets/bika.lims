import logging
import imghdr
import cStringIO
import os
from bika.lims.browser import BrowserView
from bika.lims.utils import tmpID
from bika.lims import api
from bika.lims.exportimport import instruments
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
        bc = getToolByName(self.context, 'bika_catalog')
        bsc = api.get_tool("bika_setup_catalog")
        analysts_folder = os.environ.get('INSTRUMENT_RESULTS_IMPORTER', '')
        errors = []
        archive = []
        result_to_return = []
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
                #myimporter = [i for i in exims if i[1] == instrument_model][0]
                exim = [i for i in exims if i[1] == instrument_model]
                if len(exim) > 0:
                    myimporter = exim[0]
                    import_importer = myimporter[0]
                else:
                    msg = 'Instrument Importer with {} model not found'.format(instrument_model)
                    errors.append(msg)
                if import_importer == 'shimadzu.gcms.tq8030':
                    from bika.lims.exportimport.instruments.shimadzu.gcms.tq8030 import Import
                if import_importer == 'shimadzu.gcms.qp2010se':
                    from bika.lims.exportimport.instruments.shimadzu.gcms.qp2010se import Import
                if import_importer == 'shimadzu.icpe.multitype':
                    from bika.lims.exportimport.instruments.shimadzu.icpe.multitype import Import
                if import_importer == 'shimadzu.nexera.LC2040C':
                    from bika.lims.exportimport.instruments.shimadzu.nexera.LC2040C import Import
                if import_importer == 'shimadzu.nexera.LCMS8050':
                    from bika.lims.exportimport.instruments.shimadzu.nexera.CMS8050 import Import
                if import_importer == 'genericthreecols':
                    from bika.lims.exportimport.instruments.genericthreecols import Import
                if import_importer == 'agilent.masshunter.masshunter':
                    from bika.lims.exportimport.instruments.agilent.masshunter.masshunter import Import

                instrument_path = os.path.join(analyst_filepath, instrument)
                for state_folder in  os.listdir(instrument_path):
                    if state_folder == 'Received and To Be Verified':
                        state_folder_path = os.path.join(
                                                        instrument_path,
                                                        state_folder)
                        for fname in  os.listdir(state_folder_path):
                            path = os.path.dirname(__file__)
                            filename = os.path.join(state_folder_path,fname)
                            if os.path.isfile(filename):
                                data = open(filename, 'r').read()
                                file = FileUpload(FileToUpload(cStringIO.StringIO(data),fname))

                                #exec(import_importer)
                                request.form = dict(submitted=True,
                                                    artoapply='received',
                                                    override='nooverride',
                                                    file=file,
                                                    sample='requestid',
                                                    instrument='',
                                                    advancetostate = '',
                                                    analyst=self.user,
                                                    )
                                context = self.portal
                                results = Import(context, request)
                                import pdb; pdb.set_trace()
                                result_to_return.append(results)
                    if state_folder == 'Submit and transition to be verified':
                        state_folder_path = os.path.join(
                                                        instrument_path,
                                                        state_folder)
                        for fname in  os.listdir(state_folder_path):
                            path = os.path.dirname(__file__)
                            filename = os.path.join(state_folder_path,fname)
                            if os.path.isfile(filename):
                                data = open(filename, 'r').read()
                                file = FileUpload(FileToUpload(cStringIO.StringIO(data),fname))

                                #exec(import_importer)
                                request.form = dict(submitted=True,
                                                    artoapply='received',
                                                    override='nooverride',
                                                    file=file,
                                                    sample='requestid',
                                                    instrument='',
                                                    advancetostate = 'submit',
                                                    analyst=self.user,
                                                    )
                                context = self.portal
                                results = Import(context, request)
                                report = json.loads(results)
                                if len(results[log]) > 0:
                                import pdb; pdb.set_trace()
                                result_to_return.append(results)

        logger.info('Done')
        return ('Done', result_to_return, errors)
