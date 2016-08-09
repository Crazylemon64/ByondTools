'''
Created on Nov 6, 2013

@author: Rob
'''
from __future__ import print_function, absolute_import

import re, hashlib, collections

from byond.color import COLORS, BYOND2RGBA
from byond.utils import eval_expr

from .byondvalue import BYONDValue

from future.utils import viewkeys

# import logging
AREA_LAYER = 1
TURF_LAYER = 2
OBJ_LAYER = 3
MOB_LAYER = 4
FLY_LAYER = 5

REGEX_TABS = re.compile('^(?P<tabs>\t*)')

class BYONDFileRef(BYONDValue):
    """
    Just to format file references differently.
    """
    def __init__(self, string, filename='', line=0, **kwargs):
        super(BYONDFileRef,self).__init__(string, filename, line, '/icon', **kwargs)

    def __str__(self):
        return "'{0}'".format(self.value)

class BYONDString(BYONDValue):
    """
    Correctly formats strings.
    """
    def __init__(self, string, filename='', line=0, **kwargs):
        super(BYONDString,self).__init__(string, filename, line, '/', **kwargs)

    def __str__(self):
        return '"{0}"'.format(self.value)


class BYONDList(BYONDValue):
    """
    Correctly formats lists (dict/lists).
    """
    def __init__(self, value, filename='', line=0, **kwargs):
        super(BYONDList, self).__init__(value, filename, line, '/', **kwargs)

    def __str__(self):
        vals = []
        if type(self.value) is dict:
            for k,v in self.value.items():
                wk=byond_wrap(k)
                wv=byond_wrap(v)
                vals.append('{} = {}'.format(k,v))
        else:
            vals = self.value
        return 'list({0})'.format(', '.join(vals))


class BYONDNumber(BYONDValue):
    """
    Correctly formats numeric values
    """
    def __init__(self, value, filename='', line=0, **kwargs):
        super(BYONDNumber, self).__init__(value, filename, line, '/', **kwargs)


class PropertyFlags(object):
    '''Collection of flags that affect :func:`Atom.setProperty` behavior.'''

    #: Property being set should be saved to the map
    MAP_SPECIFIED = 1

    #: Property being set should be handled as a string
    STRING = 2

    #: Property being set should be handled as a file reference
    FILEREF = 4

    #: Property being set should be handled as a value
    VALUE = 8

def byond_wrap(value):
    '''Wrap a Python instance with the proper BYONDValue type.
    '''
    T = type(value)
    if T is BYONDValue:
        return value
    if T is str or T is unicode:
        return BYONDString(value)
    elif T is list or T is dict:
        return BYONDList(value)
    else:
        return BYONDValue(value)
