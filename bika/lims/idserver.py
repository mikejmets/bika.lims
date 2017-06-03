# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from AccessControl import ModuleSecurityInfo, allow_module
from DateTime import DateTime
from Products.Archetypes.public import DisplayList
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.TranslationServiceTool import TranslationServiceTool
from bika.lims.browser import BrowserView
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import t
from bika.lims import interfaces
from bika.lims import logger
from bika.lims.idserver2 import INumberGenerator
from plone.i18n.normalizer.interfaces import IFileNameNormalizer
from plone.i18n.normalizer.interfaces import IIDNormalizer
from zope.component import getUtility
from zope.interface import providedBy
import copy,re,urllib
import plone.protect
import transaction
from Products.ATContentTypes.utils import DT2dt

class IDServerUnavailable(Exception):
    pass

def idserver_generate_id(context, prefix, batch_size = None):
    """ Generate a new id using external ID server.
    """
    plone = context.portal_url.getPortalObject()
    url = context.bika_setup.getIDServerURL()

    try:
        if batch_size:
            # GET
            f = urllib.urlopen('%s/%s/%s?%s' % (
                    url,
                    plone.getId(),
                    prefix,
                    urllib.urlencode({'batch_size': batch_size}))
                    )
        else:
            f = urllib.urlopen('%s/%s/%s'%(url, plone.getId(), prefix))
        new_id = f.read()
        f.close()
    except:
        from sys import exc_info
        info = exc_info()
        import zLOG; zLOG.LOG('INFO', 0, '', 'generate_id raised exception: %s, %s \n ID server URL: %s' % (info[0], info[1], url))
        raise IDServerUnavailable(_('ID Server unavailable'))

    return new_id
    
def generateUniqueId(context):
    """ Generate pretty content IDs.
        - context is used to find portal_type; in case there is no
          prefix specified for the type, the normalized portal_type is
          used as a prefix instead.
    """

    def getLastARNumber(context):
        ARs = context.getBackReferences("AnalysisRequestSample")
        prefix = context.getSampleType().getPrefix()
        ar_ids = []
        for AR in ARs:
            try:
                ar_prefix = AR.getId().split('-')[2]
            except IndexError, e:
                continue
            if ar_prefix == prefix:
                ar_ids.append(AR.id)
        ar_ids = sorted(ar_ids)
        try:
            last_ar_number = int(AR.getId().split('-')[-1])
        except:
            return 0
        return last_ar_number
    fn_normalize = getUtility(IFileNameNormalizer).normalize
    id_normalize = getUtility(IIDNormalizer).normalize
    number_generator = getUtility(INumberGenerator)

    #Get from config from view
    config_map = {
            'AnalysisRequest': '{sampleId}-R{seq:02d}',
            'SamplePartition': '{sampleId}-P{seq:02d}',
            'Sample': '{clientId}-{sampleDate:%Y%m%d}-{sampleType}-{seq:03d}',
            }
    # Analysis Request IDs
    print context.portal_type
    if context.portal_type == "AnalysisRequest":
        variable_map = {
                'AnalysisRequest': {
                    'vars': {
                        'sampleId': context.getSample().getId(),
                        },
                    'sequence': 'AR',
                    }
                }
        ar_number = getLastARNumber(context.getSample())
        #ar_number = len(context.aq_parent.objectValues('AnalysisRequest'))
        variables = variable_map[context.portal_type]['vars']
        variables['seq'] = ar_number+1
        result = config_map[context.portal_type].format(**variables)
        return result

    elif context.portal_type == "SamplePartition":
        variable_map = {
                'SamplePartition': {
                    'vars': {
                        'sampleId': context.getSample().getId(),
                        },
                    'sequence': 'SP',
                    }
                }
        ar_number = len(context.aq_parent.objectValues('SamplePartition'))
        variables = variable_map[context.portal_type]['vars']
        variables['seq'] = ar_number+1
        result = config_map[context.portal_type].format(**variables)
        return result

    elif context.portal_type == "Sample":
        variable_map = {
            'Sample': {
                'vars': {
                    'clientId': context.aq_parent.getClientID(),
                    'sampleDate': DT2dt(context.getSamplingDate()),
                    'sampleType': context.getSampleType().getPrefix(),
                    },
                'sequence': 'Sample',
                }
            }
        var_map = variable_map[context.portal_type]
        variables = var_map['vars']
        prefix_config = '-'.join(
                config_map[context.portal_type].split('-')[:-1])
        prefix = prefix_config.format(**variables)
        #sequence_start = context.bika_setup.getSampleIDSequenceStart()
        # If sequence_start is greater than new_id. Set
        # sequence_start as new_id. (Jira LIMS-280)
        new_seq = number_generator(key=prefix)
        #if sequence_start > int(new_seq):
        #    new_seq = str(sequence_start)
        variables['seq'] = new_seq + 1
        result = config_map[context.portal_type].format(**variables)
        return result

    # no prefix; use portal_type # no year inserted here
    # use "IID" normalizer, because we want portal_type to be lowercased.
    prefix = id_normalize(context.portal_type);
    new_id = next_id(prefix)
    return ('%s' + separator + '%s') % (prefix, new_id)

def renameAfterCreation(obj):
    # Can't rename without a subtransaction commit when using portal_factory
    transaction.savepoint(optimistic=True)
    # The id returned should be normalized already
    new_id = generateUniqueId(obj)
    obj.aq_inner.aq_parent.manage_renameObject(obj.id, new_id)
    return new_id
