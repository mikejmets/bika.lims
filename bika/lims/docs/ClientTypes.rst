==========
ClientTypes
==========

Certain client require licences to operate. So one or more licences can be
stored in the client Licenses field based of the client type

Running this test from the buildout directory::

    bin/test test_textual_doctests -t ClientTypes

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



ClientType
==========

A `ClientType` lives in `ClientTypes` folder::

    >>> clienttype = api.create(clienttypes, "ClientType", title="Cultivator")
    >>> clienttype
    <ClientType at /plone/bika_setup/bika_clienttypes/clienttype-1>


Client
======

A `client` lives in the `/clients` folder::

    >>> clients = self.portal.clients
    >>> client = api.create(clients, "Client", Name="RIDING BYTES", ClientID="RB")
    >>> transaction.commit()
    >>> client
    <Client at /plone/clients/client-1>
    >>> client.setLicenses([{'Authority': 'AA', 'LicenseType':clienttype.UID(), 'LicenseID': 'MY ID', 'LicenseNumber': 'RS451'},])
    >>> transaction.commit()
    >>> client_url = client.absolute_url() + '/base_edit'
    >>> browser.open(client_url)
    >>> "edit_form" in browser.contents
    True
    >>> browser.getControl(name='Licenses.LicenseID:records', index=0).value == 'MY ID'
    True
    >>> browser.getControl(name='Licenses.LicenseType:records', index=0).value[0] == clienttype.UID()
    True
