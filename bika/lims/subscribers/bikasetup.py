# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions
from bika.lims.numbergenerator import INumberGenerator
from bika.lims.permissions import ManageWorksheets
from bika.lims.permissions import AddClient, EditClient, ManageClients
from zope.component import getUtility

def BikaSetupModifiedEventHandler(instance, event):
    """ Event fired when BikaSetup object gets modified.
        Applies security and permission rules
    """

    if instance.portal_type != "BikaSetup":
        print("How does this happen: type is %s should be BikaSetup" % instance.portal_type)
        return

    # Security
    portal = getToolByName(instance, 'portal_url').getPortalObject()
    mp = portal.manage_permission
    if instance.getRestrictWorksheetManagement() == True \
        or instance.getRestrictWorksheetUsersAccess() == True:
        # Only LabManagers are able to create worksheets.
        mp(ManageWorksheets, ['Manager', 'LabManager'],1)
    else:
        # LabManagers, Lab Clerks and Analysts can create worksheets
        mp(ManageWorksheets, ['Manager', 'LabManager', 'LabClerk', 'Analyst'],1)


    # Allow to labclerks to add/edit clients?
    roles = ['Manager', 'LabManager']
    if instance.getAllowClerksToEditClients() == True:
        # LabClerks must be able to Add/Edit Clients
        roles += ['LabClerk']

    mp(AddClient, roles, 1)
    mp(EditClient, roles, 1)
    # Set permissions at object level
    for obj in portal.clients.objectValues():
        mp = obj.manage_permission
        mp(AddClient, roles, 0)
        mp(EditClient, roles, 0)
        mp(permissions.ModifyPortalContent, roles, 0)
        obj.reindexObject()

    #number_generator = getUtility(INumberGenerator)
    #for rec in instance.getIDFormatting():
    #    if 'seed' in rec:
    #        if 'prefix' in rec and 'context' not in rec:
    #            new_seq = number_generator.set_seed(key=rec['prefix'], seed=rec['seed'])
    #        elif 'context' in rec:
    #            new_seq = number_generator.set_seed(key=rec['context'], seed=rec['seed'])
    #        #index = instance.getIDFormatting().index(rec)
    #        #del instance.getIDFormatting()[index]['seed']
    #        import pdb; pdb.set_trace()
    #        del rec['seed']
