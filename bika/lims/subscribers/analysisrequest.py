# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

def ObjectInitializedEventHandler(instance, event):

    if instance.portal_type != "AnalysisRequest":
        return

    priority = instance.getPriority()
    if priority:
        return

    instance.setDefaultPriority()
    samplingDate = instance.getSamplingDate()
    if samplingDate and samplingDate._tz != samplingDate.localZone():
        samplingDate._tz = samplingDate.localZone()
        instance.setSamplingDate(samplingDate)
    return

def ARModifiedEventHandler(instance, event):

    if instance.portal_type != "AnalysisRequest":
        return

    samplingDate = instance.getSamplingDate()
    if samplingDate and samplingDate._tz != samplingDate.localZone():
        samplingDate._tz = samplingDate.localZone()
        instance.setSamplingDate(samplingDate)

    dateSampled = instance.getDateSampled()
    if dateSampled and dateSampled._tz != dateSampled.localZone():
        dateSampled._tz = dateSampled.localZone()
        instance.setDateSampled(dateSampled)
    return
