from Acquisition import aq_inner
from Acquisition import aq_parent
from Products.CMFCore.utils import getToolByName
from bika.lims.interfaces import IIdServer
from bika.lims import logger

def upgrade(tool):
    """Upgrade to 3.2
    """

    portal = aq_parent(aq_inner(tool))
    siteman = portal.getSiteManager()

    ### update commonly affected tools
    setup = portal.portal_setup
    setup.runImportStepFromProfile('profile-bika.lims:default', 'typeinfo')
    setup.runImportStepFromProfile('profile-bika.lims:default', 'workflow')
    setup.runImportStepFromProfile('profile-bika.lims:default', 'workflow-csv')
    workflow = getToolByName(portal, 'portal_workflow')
    workflow.updateRoleMappings()
    setup.runAllImportStepsFromProfile('profile-Products.DataGridField:default')

    return True

