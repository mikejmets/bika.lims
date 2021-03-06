# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims.config import INSTRUMENT_IMPORT_AUTO_OPTIONS
from bika.lims.utils import t
from bika.lims.browser import BrowserView
from bika.lims.content.instrument import getDataInterfaces
from bika.lims.exportimport import instruments
from bika.lims.exportimport.load_setup_data import LoadSetupData
from bika.lims.interfaces import ISetupDataSetList
from plone.app.layout.globals.interfaces import IViewView
from Products.Archetypes.public import DisplayList
from Products.CMFCore.utils import getToolByName
from zope.interface import implements
from pkg_resources import *
from zope.component import getAdapters

import plone


class SetupDataSetList:

    implements(ISetupDataSetList)

    def __init__(self, context):
        self.context = context

    def __call__(self, projectname="bika.lims"):
        datasets = []
        for f in resource_listdir(projectname, 'setupdata'):
            fn = f+".xlsx"
            try:
                if fn in resource_listdir(projectname, 'setupdata/%s' % f):
                    datasets.append({"projectname": projectname, "dataset": f})
            except OSError:
                pass
        return datasets


class ImportView(BrowserView):

    """
    """
    implements(IViewView)
    template = ViewPageTemplateFile("import.pt")

    def __init__(self, context, request):
        super(ImportView, self).__init__(context, request)

        self.icon = ""
        self.title = self.context.translate(_("Import"))
        self.description = self.context.translate(_("Select a data interface"))

        request.set('disable_border', 1)

    def import_form(self):
        """This is a trick to allow non-robot tests to access the import form
        without javascript.
        """
        exim = self.request.get('exim')
        if exim:
            exim = exim.replace(".", "/")
            import os.path
            instrpath = os.path.join("exportimport", "instruments")
            templates_dir = resource_filename("bika.lims", instrpath)
            #TODO Serve exim template and  if it does not exits get the default template
            fname = "%s/%s_import.pt" % (templates_dir, exim)
            return ViewPageTemplateFile("instruments/%s_import.pt" % exim)(self)
        else:
            return ""

        if "instrument" in self.request:
            instrument_fn = instrument.replace(".", "/")
            template_fn = resource_filename(bika.lims, join("exportimport/instruments"))
            it = ViewPageTemplateFile("")
            return it()

    def getInstruments(self):
        """Part of the import_form cheat above; stolen from
        ajaxGetImportTemplate
        """
        bsc = getToolByName(self, 'bika_setup_catalog')
        items = [('', '')] + [(o.UID, o.Title) for o in
                               bsc(portal_type = 'Instrument',
                                   inactive_state = 'active')]
        items.sort(lambda x, y: cmp(x[1].lower(), y[1].lower()))
        return DisplayList(list(items))

    def getAnalysisServicesDisplayList(self):
        """Part of the import_form cheat above; stolen from
        ajaxGetImportTemplate
        """
        bsc = getToolByName(self, 'bika_setup_catalog')
        items = [('', '')] + [(o.getObject().Keyword, o.Title) for o in
                                bsc(portal_type = 'AnalysisService',
                                   inactive_state = 'active')]
        items.sort(lambda x, y: cmp(x[1].lower(), y[1].lower()))
        return DisplayList(list(items))


    def getDataInterfaces(self):
        return getDataInterfaces(self.context)

    def getSetupDatas(self):
        datasets = []
        adapters = getAdapters((self.context, ), ISetupDataSetList)
        for name, adapter in adapters:
            datasets.extend(adapter())
        return datasets

    def getProjectName(self):
        adapters = getAdapters((self.context, ), ISetupDataSetList)
        productnames = [name for name, adapter in adapters]
        if len(productnames) == 1:
            productnames[0] = 'bika.lims'
        return productnames[len(productnames) - 1]

    def __call__(self):
        if 'submitted' in self.request:
            if 'setupfile' in self.request.form or \
               'setupexisting' in self.request.form:
                lsd = LoadSetupData(self.context, self.request)
                return lsd()
            else:
                exim = instruments.getExim(self.request['exim'])
                return exim.Import(self.context, self.request)
        else:
            return self.template()


class ajaxGetImportTemplate(BrowserView):

    def __call__(self):
        plone.protect.CheckAuthenticator(self.request)
        exim = self.request.get('exim').replace(".", "/")
        # This was the default template and the instrument below is the only
        # instrument that uses this template
        # To avoid this instrument to break, we'll just give it the template
        # that it is expecting
        # We are moving towards all instruments to use one template
        if exim == 'myself/myinstrument':
            return ViewPageTemplateFile("instruments/instrument.pt")(self)

        # If a specific template for this instrument doesn't exist yet,
        # use the default template for instrument results file import located
        # at bika/lims/exportimport/instruments/default_import.pt
        import os.path
        instrpath = os.path.join("exportimport", "instruments")
        templates_dir = resource_filename("bika.lims", instrpath)
        fname = "%s/%s_import.pt" % (templates_dir, exim)
        if os.path.isfile(fname):
            return ViewPageTemplateFile("instruments/%s_import.pt" % exim)(self)
        else:
            return ViewPageTemplateFile("instruments/default_import.pt")(self)

    def getInstruments(self):
        bsc = getToolByName(self, 'bika_setup_catalog')
        items = [('', '')] + [(o.UID, o.Title) for o in
                               bsc(portal_type = 'Instrument',
                                   inactive_state = 'active')]
        items.sort(lambda x, y: cmp(x[1].lower(), y[1].lower()))
        return DisplayList(list(items))

    def getAnalysisServicesDisplayList(self):
        ''' Returns a Display List with the active Analysis Services
            available. The value is the keyword and the title is the
            text to be displayed.
        '''
        bsc = getToolByName(self, 'bika_setup_catalog')
        items = [('', '')] + [(o.getObject().Keyword, o.Title) for o in
                                bsc(portal_type = 'AnalysisService',
                                   inactive_state = 'active')]
        items.sort(lambda x, y: cmp(x[1].lower(), y[1].lower()))
        return DisplayList(list(items))

    def getAdvanceToState(self):
        """Get States to advance to on an AR Instrument Import
        """
        tr_success_state = api.get_bika_setup().getAutoTransition()
        if len(tr_success_state) ==  0:
            return DisplayList([('', "Don't transition")])
        return INSTRUMENT_IMPORT_AUTO_OPTIONS
