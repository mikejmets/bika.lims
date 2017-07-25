===============
UnitConversions
===============

Analyses results are recorded in a given unit. Unit conversion allow for the reporting of a result in one or alternative units. Unit conversion are created a setup data that can be used on Reportig Units in Analysis Services.

Running this test from the buildout directory::

    bin/test test_textual_doctests -t UnitConversions

Test Setup
==========
Needed Imports::

    >>> import transaction
    >>> from plone import api as ploneapi
    >>> from zope.lifecycleevent import modified

    >>> from bika.lims import api
    >>> from bika.lims.utils.analysisrequest import create_analysisrequest


Variables::

    >>> portal = self.portal
    >>> bika_setup = portal.bika_setup
    >>> clienttypes = bika_setup.bika_clienttypes
    >>> portal_url = portal.absolute_url()
    >>> browser = self.getBrowser()
    >>> current_user = ploneapi.user.get_current()
    >>> ploneapi.user.grant_roles(user=current_user,roles = ['Manager'])
    >>> transaction.commit()



Client
======

A `client` lives in the `/clients` folder::

    >>> clients = self.portal.clients
    >>> client = api.create(clients, "Client", Name="RIDING BYTES", ClientID="RB")
    >>> transaction.commit()
    >>> client
    <Client at /plone/clients/client-1>
    >>> transaction.commit()

A `UnitConversion` lives in `/bika_setup/bika_unitconversions` folder.::

    >>> unitconversions = self.portal.bika_setup.bika_unitconversions
    >>> unitconv = api.create(unitconversions, "UnitConversion", title="mg/L", converted_unit="%", formula="Value * 100", description="mg/L to percentage")
    >>> transaction.commit()
    >>> unitconv
    <UnitConversion at /plone/bika_setup/bika_unitconversions/unitconversion-1>

A `SampleType` lives in `/bika_setup/bika_sampletypes` folder.::

    >>> sampletypes = self.portal.bika_setup.bika_sampletypes
    >>> stype = api.create(sampletypes, 'SampleType', title='Food')
    >>> transaction.commit()
    >>> stype
    <SampleType at /plone/bika_setup/bika_sampletypes/sampletype-1>

A `AnalysisService` lives in `/bika_setup/bika_analysisservices` folder.::

    >>> services = self.portal.bika_setup.bika_analysisservices
    >>> aserv = api.create(services, 'AnalysisService', title='Ca')
    >>> aserv.setUnitConversions([{'SampleType': stype.UID(), 'unit': unitconv.UID()},])
    >>> transaction.commit()
    >>> aserv
    <AnalysisService at /plone/bika_setup/bika_analysisservices/analysisservice-1>

