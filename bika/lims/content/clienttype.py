# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from plone.supermodel import model
from plone.dexterity.content import Container, Item
from zope.interface import implements
from bika.lims import bikaMessageFactory as _

class IClientType(model.Schema):
    """ A Type of Client.
    """

class ClientType(Item):
    implements(IClientType)
    pass
