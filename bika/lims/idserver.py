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
    
def generateUniqueId(context, parent=False):
    """ Generate pretty content IDs.
        - context is used to find portal_type; in case there is no
          prefix specified for the type, the normalized portal_type is
          used as a prefix instead.
    """

    prefixes = context.bika_setup.getPrefixes()
    year = context.bika_setup.getYearInPrefix() and \
        DateTime().strftime("%Y")[2:] or ''
    separator = '-'
    for e in prefixes:
        if 'separator' not in e:
            e['separator'] = ''
        if e['portal_type'] == context.portal_type:
            separator = e['separator']

    if context.bika_setup.getExternalIDServer():
        # if using external server
        for d in prefixes:
            # Sample ID comes from SampleType
            if context.portal_type == "Sample":
                prefix = context.getSampleType().getPrefix()
                padding = context.bika_setup.getSampleIDPadding()
                new_id = str(idserver_generate_id(context, "%s%s-" % (prefix, year)))
                if padding:
                    new_id = new_id.zfill(int(padding))
                return ('%s%s' + separator + '%s') % (prefix, year, new_id)
            elif d['portal_type'] == context.portal_type:
                prefix = d['prefix']
                padding = d['padding']
                new_id = str(idserver_generate_id(context, "%s%s-" % (prefix, year)))
                if padding:
                    new_id = new_id.zfill(int(padding))
                return ('%s%s' + separator + '%s') % (prefix, year, new_id)
        # no prefix; use portal_type
        # year is not inserted here
        # portal_type is be normalized to lowercase
        npt = id_normalize(context.portal_type)
        new_id = str(idserver_generate_id(context, npt + "-"))
        return ('%s' + separator + '%s') % (npt, new_id)

    #TODO #Get from config from view
    config_map = {
        'AnalysisRequest': {
            #'form': '{sampleId}-R{seq:02d}',
            'form': '{sampleId}-R{seq:d}',
            'sequence': {
                'type': 'counter', #[generated|counter]
                'context': 'sample',
                'backreference': 'AnalysisRequestSample',
                },
            },
        'SamplePartition': {
            #'form': '{sampleId}-P{seq:02d}',
            'form': '{sampleId}-P{seq:d}',
            'sequence': {
                'type': 'counter', #[generated|counter]
                'context': 'sample',
                'contained': 'SamplePartition',
                },
            },
        'Sample': {
            #'form': '{clientId}-{sampleDate:%Y%m%d}-{sampleType}-{seq:03d}',
            'form': '{sampleType}{year}-{seq:04d}',
            'sequence': {
                'prefix': 'sample',
                'type': 'generated', #[generated|counter]
                'split_length': 1,
                },
            },
        }

    def getLastCounter(context, seq_config):
        if seq_config.get('backreference', False):
            return len(context.getBackReferences(seq_config['backreference']))-1
        elif seq_config.get('contained', False):
            return len(context.objectItems(seq_config['contained']))-1
        else:
            raise RuntimeError('ID Server: missing values in configuration')

    number_generator = getUtility(INumberGenerator)

    # Analysis Request IDs
    config = config_map.get(context.portal_type, {})
    if context.portal_type == "AnalysisRequest":
        variables_map = {
                        'sampleId': context.getSample().getId(),
                        'sample': context.getSample(),
                }
    elif context.portal_type == "SamplePartition":
        variables_map = {
                        'sampleId': context.aq_parent.getId(),
                        'sample': context.aq_parent,
                }
    elif context.portal_type == "Sample" and parent:
        config = config_map['SamplePartition'] #Override
        variables_map = {
                        'sampleId': context.getId(),
                        'sample': context,
                }
    elif context.portal_type == "Sample":
        variables_map = {
                    'clientId': context.aq_parent.getClientID(),
                    'sampleDate': DT2dt(context.getSamplingDate()),
                    'sampleType': context.getSampleType().getPrefix(),
                    'year': context.bika_setup.getYearInPrefix() and \
                            DateTime().strftime("%Y")[2:] or ''
            }
    else:
        config = {
            'form': '%s-{seq}' % context.portal_type.lower(),
            'sequence': {
                'type': 'generated', #[generated|counter]
                'prefix': '%s' % context.portal_type.lower(),
                },
            }
        variables_map = {}

    #Actual id construction starts here
    form = config['form']
    seq = config['sequence']
    if seq['type'] == 'counter':
        new_seq = getLastCounter(
                        context=variables_map[seq['context']], 
                        seq_config=seq)
    elif seq['type'] == 'generated':
        if seq.get('split_length', None) == 0:
            prefix_config = '-'.join(form.split('-')[:-1])
            prefix = prefix_config.format(**variables_map)
        elif seq.get('split_length', None) > 0:
            prefix_config = '-'.join(form.split('-')[:seq['split_length']])
            prefix = prefix_config.format(**variables_map)
        else:
            prefix = seq['prefix']
        new_seq = number_generator(key=prefix)
    variables_map['seq'] = new_seq + 1
    result = form.format(**variables_map)
    return result


def renameAfterCreation(obj):
    # Can't rename without a subtransaction commit when using portal_factory
    transaction.savepoint(optimistic=True)
    # The id returned should be normalized already
    new_id = generateUniqueId(obj)
    obj.aq_inner.aq_parent.manage_renameObject(obj.id, new_id)
    return new_id
