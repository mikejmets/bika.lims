ID Server
=========

The ID Server in Bika LIMS provides IDs for content items base of the given format specification. The format string is constructed in the same way as a python format() method based predefined variables per content type. The only variable available to all type is 'seq'. Currently, seq can be constructed either using number generator or a counter of existing items. For generated IDs, one can specifypoint at which the format string will be split to create the generator key. For counter IDs, one must specify context and the type of counter which is either the number of backreferences or the number of contained objects.

Configuration Settings:
* format:
  - a python format string constructed from predefined variables like sampleId, client, sampleType.
  - special variable 'seq' must be positioned last in the format string
* sequence type: [generated|counter]
* context: if type counter, provides context the counting function
* counter type: [backreference|contained]
* counter reference: a parameter to the counting function
* prefix: default prefix if none provided in format string
* split length: the number of parts to be included in the prefix

ToDo:
* validation of format strings

Running this test from the buildout directory::

    bin/test test_textual_doctests -t IDServer


Test Setup
----------

Needed Imports::

    >>> import transaction
    >>> from DateTime import DateTime
    >>> from plone import api as ploneapi

    >>> from bika.lims import api
    >>> from bika.lims.utils.analysisrequest import create_analysisrequest

Functional Helpers::

    >>> def start_server():
    ...     from Testing.ZopeTestCase.utils import startZServer
    ...     ip, port = startZServer()
    ...     return "http://{}:{}/{}".format(ip, port, portal.id)

    >>> def timestamp(format="%Y-%m-%d"):
    ...     return DateTime().strftime(format)

    >>> def timestamp(format="%Y-%m-%d"):
    ...     return DateTime().strftime(format)

Variables::

    >>> date_now = timestamp()
    >>> year = date_now.split('-')[0][2:]
    >>> sample_date = DateTime(2017, 1, 31)
    >>> portal = self.portal
    >>> request = self.request
    >>> bika_setup = portal.bika_setup
    >>> bika_sampletypes = bika_setup.bika_sampletypes
    >>> bika_samplepoints = bika_setup.bika_samplepoints
    >>> bika_analysiscategories = bika_setup.bika_analysiscategories
    >>> bika_analysisservices = bika_setup.bika_analysisservices
    >>> bika_labcontacts = bika_setup.bika_labcontacts
    >>> bika_storagelocations = bika_setup.bika_storagelocations
    >>> bika_samplingdeviations = bika_setup.bika_samplingdeviations
    >>> bika_sampleconditions = bika_setup.bika_sampleconditions
    >>> bika_containers = bika_setup.bika_containers
    >>> portal_url = portal.absolute_url()
    >>> bika_setup_url = portal_url + "/bika_setup"
    >>> browser = self.getBrowser()
    >>> current_user = ploneapi.user.get_current()


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

Set up `ID Server` configuration::

    >>> values = [
    ...            {'form': '{sampleType}{year}-{seq:04d}',
    ...             'portal_type': 'Sample',
    ...             'prefix': 'sample',
    ...             'sequence_type': 'generated',
    ...             'split_length': 1,
    ...             'value': ''},
    ...            {'context': 'sample',
    ...             'counter_reference': 'AnalysisRequestSample',
    ...             'counter_type': 'backreference',
    ...             'form': '{sampleId}-R{seq:d}',
    ...             'portal_type': 'AnalysisRequest',
    ...             'sequence_type': 'counter',
    ...             'value': ''},
    ...            {'context': 'sample',
    ...             'counter_reference': 'SamplePartition',
    ...             'counter_type': 'contained',
    ...             'form': '{sampleId}-P{seq:d}',
    ...             'portal_type': 'SamplePartition',
    ...             'sequence_type': 'counter',
    ...             'value': ''},
    ...            {'form': 'BÖ-{year}-{seq:04d}',
    ...             'portal_type': 'Batch',
    ...             'prefix': 'batch',
    ...             'sequence_type': 'generated',
    ...             'split_length': 1,
    ...             'value': ''},
    ...          ]

    >>> bika_setup.setIDFormatting(values)

An `AnalysisRequest` can be created::

    >>> values = {
    ...           'Client': client,
    ...           'Contact': contact,
    ...           'SamplingDate': sample_date,
    ...           'DateSampled': sample_date,
    ...           'SampleType': sampletype
    ...          }

    >>> ploneapi.user.grant_roles(user=current_user,roles = ['Sampler', 'LabClerk'])
    >>> transaction.commit()
    >>> service_uids = [analysisservice.UID()]
    >>> ar = create_analysisrequest(client, request, values, service_uids)
    >>> ar
    <AnalysisRequest at /plone/clients/client-1/water17-0001-R1>

Create a second `AnalysisRequest`::

    >>> values = {
    ...           'Client': client,
    ...           'Contact': contact,
    ...           'SamplingDate': sample_date,
    ...           'DateSampled': sample_date,
    ...           'SampleType': sampletype
    ...          }

    >>> service_uids = [analysisservice.UID()]
    >>> ar = create_analysisrequest(client, request, values, service_uids)
    >>> ar
    <AnalysisRequest at /plone/clients/client-1/water17-0002-R1>

Create a third `AnalysisRequest` with existing sample::

    >>> sample = ar.getSample()
    >>> sample
    <Sample at /plone/clients/client-1/water17-0002>
    >>> values = {
    ...           'Client': client,
    ...           'Contact': contact,
    ...           'SampleType': sampletype,
    ...           'Sample': sample,
    ...          }

    >>> service_uids = [analysisservice.UID()]
    >>> ar = create_analysisrequest(client, request, values, service_uids)
    >>> ar
    <AnalysisRequest at /plone/clients/client-1/water17-0002-R2>

Create a forth `Batch`::
    >>> batches = self.portal.batches
    >>> batch = api.create(batches, "Batch", ClientID="RB")
    >>> batch.getId() == "BA-{}-0001".format(year)
    True

Change ID formats and create new `AnalysisRequest`::
    >>> values = [
    ...            {'form': '{clientId}-{samplingDate:%Y%m%d}-{sampleType}-{seq:04d}',
    ...             'portal_type': 'Sample',
    ...             'prefix': 'sample',
    ...             'sequence_type': 'generated',
    ...             'split_length': 2,
    ...             'value': ''},
    ...            {'context': 'sample',
    ...             'counter_reference': 'AnalysisRequestSample',
    ...             'counter_type': 'backreference',
    ...             'form': '{sampleId}-R{seq:03d}',
    ...             'portal_type': 'AnalysisRequest',
    ...             'sequence_type': 'counter',
    ...             'value': ''},
    ...            {'context': 'sample',
    ...             'counter_reference': 'SamplePartition',
    ...             'counter_type': 'contained',
    ...             'form': '{sampleId}-P{seq:d}',
    ...             'portal_type': 'SamplePartition',
    ...             'sequence_type': 'counter',
    ...             'value': ''},
    ...            {'form': 'BÖ-{year}-{seq:04d}',
    ...             'portal_type': 'Batch',
    ...             'prefix': 'batch',
    ...             'sequence_type': 'generated',
    ...             'split_length': 1,
    ...             'value': ''},
    ...          ]

    >>> bika_setup.setIDFormatting(values)

    >>> values = {
    ...           'Client': client,
    ...           'Contact': contact,
    ...           'SamplingDate': sample_date,
    ...           'DateSampled': sample_date,
    ...           'SampleType': sampletype
    ...          }

    >>> service_uids = [analysisservice.UID()]
    >>> ar = create_analysisrequest(client, request, values, service_uids)
    >>> ar
    <AnalysisRequest at /plone/clients/client-1/RB-20170131-water-0001-R001>

Re-seed and create a new `Batch`::
    >>> ploneapi.user.grant_roles(user=current_user,roles = ['Manager'])
    >>> transaction.commit()
    >>> browser.open(portal_url + '/ng_seed?prefix=batch-BA&seed=10')
    >>> batch = api.create(batches, "Batch", ClientID="RB")
    >>> batch.getId() == "BA-{}-0011".format(year)
    True
    >>> transaction.commit()
    >>> browser.open(portal_url + '/ng_flush')
    >>> ar = create_analysisrequest(client, request, values, service_uids)
    >>> ar.getId()
    'RB-20170131-water-0002-R001'
    >>> batch = api.create(batches, "Batch", ClientID="RB")
    >>> batch.getId() == "BA-{}-0012".format(year)
    True

Bika Setup
----------
A `Container` is a bika_setup type that must be tested::

    >>> container = api.create(bika_containers, "Container", Name="Big Jar")
    >>> container
    <Container at /plone/bika_setup/bika_containers/container-1>
    >>> container = api.create(bika_containers, "Container", Name="Small Jar")
    >>> container
    <Container at /plone/bika_setup/bika_containers/container-2>
    >>> transaction.commit()
    >>> browser.open(portal_url + '/ng_flush')
    >>> container = api.create(bika_containers, "Container", Name="Tiny Jar")
    >>> container
    <Container at /plone/bika_setup/bika_containers/container-3>

TODO: Test the case when numbers are exhausted in a sequence!
