# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

import transaction
from Acquisition import aq_inner
from Acquisition import aq_parent
from bika.lims import logger
from bika.lims.idserver2 import INumberGenerator
from Products.ATContentTypes.utils import DT2dt
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType
from zope.component import getUtility


def upgrade(tool):
    """Upgrade step to prepare for refactored ID Server
    """
    portal = aq_parent(aq_inner(tool))

    qi = portal.portal_quickinstaller
    ufrom = qi.upgradeInfo('bika.lims')['installedVersion']
    logger.info("Upgrading Bika LIMS: %s -> %s" % (ufrom, '3.3.1.0'))

    setup = portal.portal_setup
    # Sync the empty number generator with existing content
    prepare_number_generator(portal)

    return True


def prepare_number_generator(portal):
    bsc = portal.bika_setup_catalog
    number_generator = getUtility(INumberGenerator)

    setup_data_brains = bsc()
    data_dict = {}
    for brain in setup_data_brains:
        if brain.portal_type not in data_dict:
            data_dict[brain.portal_type] = []
        data_dict[brain.portal_type].append(brain)

    dict_keys = data_dict.keys()
    special_cases = ('Sample', 'SamplePartition', 'AnalysisRequest')
    for key in special_cases:
        if key in dict_keys:
            dict_keys.remove(key)

    for key in dict_keys:
        for i in data_dict[key]:
            dummy = number_generator(key.lower())

    
    #Special Cases
    #Sample
    pc = portal.portal_catalog
    #TODO thiscould be made generic with a default config in plce
    #TODO get from bika_setup 
    config = {
            'form': '{clientId}-{sampleDate:%Y%m%d}-{sampleType}-{seq:03d}',
            'sequence': {
                'prefix': 'sample',
                'type': 'generated', #[generated|counter]
                'split_length': 2,
                },
            }
    form = config['form']
    seq = config['sequence']

    sample_brains = pc(portal_type='Sample')
    for brain in sample_brains:
        context = brain.getObject()
        variables_map = {
                    'clientId': context.aq_parent.getClientID(),
                    'sampleDate': DT2dt(context.getSamplingDate()),
                    'sampleType': context.getSampleType().getPrefix(),
            }
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
            import pdb; pdb.set_trace()
            new_seq = number_generator(key=prefix)

