==========
CientTypes
==========

Certain client require licences to operater. So a licences can be stored in the client
based of the client type

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

    >>> def create(container, portal_type, title=None):
    ...     # Creates a content in a container and manually calls processForm
    ...     title = title is None and "Test {}".format(portal_type) or title
    ...     _ = container.invokeFactory(portal_type, id="tmpID", title=title)
    ...     obj = container.get(_)
    ...     obj.processForm()
    ...     modified(obj)  # notify explicitly for the test
    ...     transaction.commit()  # somehow the created method did not appear until I added this
    ...     return obj


Variables::

    >>> portal = self.portal
    >>> bika_setup = portal.bika_setup
    >>> clienttypes = bika_setup.bika_clienttypes
    >>> portal_url = portal.absolute_url()
    >>> browser = self.getBrowser()


ClientDepartment
----------------

A `ClientDepartment` lives in `ClientDepartments` folder::

    >>> clienttype = ploneapi.content.create(clienttypes, "ClientType", title="Cultivator")
    >>> clienttype
    <ClientType at /plone/bika_setup/bika_clienttypes/cultivator>

Client
======

A `client` lives in the `/clients` folder::

    >>> clients = portal.clients
    >>> client1 = create(clients, "Client", title="Client-1")
    >>> client_url = client1.absolute_url() + '/edit'
    >>> browser.open(client_url)
    >>> browser.getLink('Licences').click()
    >>> browser.getControl('ClientType').value = 'Cultivator'
    >>> import pdb; pdb.set_trace()
    >>> browser.getControl('Surname').value = 'Contact'
    >>> browser.getControl('Test Department').selected = True
    >>> browser.getControl(name='form.button.save').click()
    >>> 'Changes saved' and 'Test Department' in browser.contents
    True
    >>> browser.getControl('Test Department')
    <ItemControl name='Department' type='select' optionValue='test-department' selected=True>

