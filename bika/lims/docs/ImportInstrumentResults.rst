==========
CientTypes
==========

ImportInstrumentResults runs throught a series of folders which has the
following structure 
InstrumentsResults
    Analyst1
        InstrumentName1
            filename.txt
            2-dimension.csv
        InstrumentName2
            filename.txt
   Analyts2
        InstrumentName1
        filename.txt
It searches for the files inside an instrument and imports the results on that
file.

Running this test from the buildout directory::

    bin/test test_textual_doctests -t ImportInstrumentResults

Test Setup
==========
Needed Imports::

    >>> import os
    >>> import transaction
    >>> from plone import api as ploneapi
    >>> from zope.lifecycleevent import modified
    >>> from DateTime import DateTime
    >>> from plone import api as ploneapi
    >>> from bika.lims import api
    >>> from bika.lims.utils.analysisrequest import create_analysisrequest
    >>> def timestamp(format="%Y-%m-%d"):
    ...     return DateTime().strftime(format)

Variables::

    >>> date_now = timestamp()
    >>> portal = self.portal
    >>> current_user = ploneapi.user.get_current()
    >>> ploneapi.user.grant_roles(user=current_user,roles = ['Analyst'])
    >>> transaction.commit()
    >>> request = self.request
    >>> browser = self.getBrowser()
    >>> bika_setup = portal.bika_setup
    >>> bika_sampletypes = bika_setup.bika_sampletypes
    >>> bika_samplepoints = bika_setup.bika_samplepoints
    >>> bika_analysiscategories = bika_setup.bika_analysiscategories
    >>> bika_analysisservices = bika_setup.bika_analysisservices
    >>> bika_labcontacts = bika_setup.bika_labcontacts
    >>> bika_storagelocations = bika_setup.bika_storagelocations
    >>> bika_samplingdeviations = bika_setup.bika_samplingdeviations
    >>> bika_sampleconditions = bika_setup.bika_sampleconditions
    >>> portal_url = portal.absolute_url()
    >>> bika_setup_url = portal_url + "/bika_setup"


Instruments
===========

All instruments live in the `/bika_setup/bika_instruments` folder::

    >>> instruments = bika_setup.bika_instruments
    >>> instrument1 = api.create(instruments, "Instrument", title="Instrument-1", ResultImporterId='shimadzu.gcms.tq8030')
    >>> instrument2 = api.create(instruments, "Instrument", title="Instrument-2", ResultImporterId='shimadzu.nexera.LC2040C')
    >>> transaction.commit()

Analysis Requests (AR)
----------------------

An `AnalysisRequest` can only be created inside a `Client`::

    >>> clients = self.portal.clients
    >>> client = api.create(clients, "Client", Name="RIDING BYTES", ClientID="RB")
    >>> client
    <Client at /plone/clients/client-1>

To create a new AR, a `Contact` is needed::

    >>> contact = api.create(client, "Contact", Firstname="Ramon", Surname="Bartl")
    >>> contact
    <Contact at /plone/clients/client-1/contact-1>

A `SampleType` defines how long the sample can be retained, the minimum volume
needed, if it is hazardous or not, the point where the sample was taken etc.::

    >>> sampletype = api.create(bika_sampletypes, "SampleType", Prefix="water", MinimumVolume="100 ml")
    >>> sampletype
    <SampleType at /plone/bika_setup/bika_sampletypes/sampletype-1>

A `SamplePoint` defines the location, where a `Sample` was taken::

    >>> samplepoint = api.create(bika_samplepoints, "SamplePoint", title="Lake of Constance")
    >>> samplepoint
    <SamplePoint at /plone/bika_setup/bika_samplepoints/samplepoint-1>

An `AnalysisCategory` categorizes different `AnalysisServices`::

    >>> analysiscategory = api.create(bika_analysiscategories, "AnalysisCategory", title="Water")
    >>> analysiscategory
    <AnalysisCategory at /plone/bika_setup/bika_analysiscategories/analysiscategory-1>

An `AnalysisService` defines a analysis service offered by the laboratory::

    >>> analysisservice = api.create(bika_analysisservices, "AnalysisService", title="PH", ShortTitle="ph", Category=analysiscategory, Keyword="PH")
    >>> analysisservice
    <AnalysisService at /plone/bika_setup/bika_analysisservices/analysisservice-1>

    >>> calcium = api.create(bika_analysisservices, "AnalysisService", title="Calcium", ShortTitle="Ca", Category=analysiscategory, Keyword="Ca")
    >>> calcium
    <AnalysisService at /plone/bika_setup/bika_analysisservices/analysisservice-2>

Finally, the `AnalysisRequest` can be created::

    >>> values = {
    ...           'Client': client,
    ...           'Contact': contact,
    ...           'SamplingDate': date_now,
    ...           'DateSampled': date_now,
    ...           'SampleType': sampletype
    ...          }

    >>> service_uids = [analysisservice.UID(), calcium.UID()]
    >>> ar1 = create_analysisrequest(client, request, values, service_uids)
    >>> ar1
    <AnalysisRequest at /plone/clients/client-1/water-0001-R01>
    >>> api.do_transition_for(ar1, 'receive')
    <AnalysisRequest at /plone/clients/client-1/water-0001-R01>
    >>> transaction.commit()
    >>> api.get_workflow_status_of(ar1)
    'sample_received'

    >>> values = {
    ...           'Client': client,
    ...           'Contact': contact,
    ...           'SamplingDate': date_now,
    ...           'DateSampled': date_now,
    ...           'SampleType': sampletype
    ...          }

    >>> service_uids = [analysisservice.UID(), calcium.UID()]
    >>> ar2 = create_analysisrequest(client, request, values, service_uids)
    >>> ar2
    <AnalysisRequest at /plone/clients/client-1/water-0002-R01>
    >>> api.do_transition_for(ar2, 'receive')
    <AnalysisRequest at /plone/clients/client-1/water-0002-R01>
    >>> transaction.commit()
    >>> api.get_workflow_status_of(ar2)
    'sample_received'

    >>> values = {
    ...           'Client': client,
    ...           'Contact': contact,
    ...           'SamplingDate': date_now,
    ...           'DateSampled': date_now,
    ...           'SampleType': sampletype
    ...          }

    >>> service_uids = [analysisservice.UID(), calcium.UID()]
    >>> ar3 = create_analysisrequest(client, request, values, service_uids)
    >>> ar3
    <AnalysisRequest at /plone/clients/client-1/water-0003-R01>
    >>> api.do_transition_for(ar3, 'receive')
    <AnalysisRequest at /plone/clients/client-1/water-0003-R01>
    >>> transaction.commit()
    >>> api.get_workflow_status_of(ar3)
    'sample_received'

    >>> results_import_url = portal_url + '/import_instrument_results'
    >>> browser.open(results_import_url)
    >>> contents = browser.contents
    >>> 'Import finished successfully: 1 ARs and 1 results updated' in contents
    True
    >>> browser.contents.count('Import finished successfully: 1 ARs and 2 results updated')
    2

Move back import files::

    >>> this_dir = os.path.dirname(os.path.abspath(__file__))
    >>> analysts_folder = this_dir.replace('docs', 'tests/files/importresult/')

Cleanup, move files back and delete archives and wip folders::

    >>> test_analy1 = os.path.join(analysts_folder, 'test_analyst')
    >>> instr1 = os.path.join(test_analy1, 'Instrument-1')
    >>> instr1_arch = os.path.join(instr1, 'archives')
    >>> current_file = os.path.join(instr1_arch, '2-dimension.csv')
    >>> dest_file = os.path.join(instr1, '2-dimension.csv')
    >>> os.rename(current_file, dest_file)
    >>> '2-dimension.csv' in os.listdir(instr1)
    True
    >>> current_file = os.path.join(instr1_arch, 'TQ-8030.txt')
    >>> dest_file = os.path.join(instr1, 'TQ-8030.txt')
    >>> os.rename(current_file, dest_file)
    >>> 'TQ-8030.txt' in os.listdir(instr1)
    True
    >>> os.rmdir(instr1_arch)
    >>> os.rmdir(os.path.join(instr1, 'wip'))

    >>> instr2 = os.path.join(test_analy1, 'Instrument-2')
    >>> instr2_arch = os.path.join(instr2, 'archives')
    >>> current_file = os.path.join(instr2_arch, 'nexera')
    >>> dest_file = os.path.join(instr2, 'nexera')
    >>> os.rename(current_file, dest_file)
    >>> 'nexera' in os.listdir(instr2)
    True
    >>> os.rmdir(instr2_arch)
    >>> os.rmdir(os.path.join(instr2, 'wip'))
