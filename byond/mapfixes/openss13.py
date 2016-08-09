'''
Fixes to bring old OpenSS13 builds up to date.
'''

from .base import Matcher, MapFix, RenameProperty, DeclareDependencies, ChangeType
from byond.basetypes import BYONDString, BYONDValue, Atom, PropertyFlags
from byond.directions import *

DeclareDependencies('openss13', ['ss13'])

ATMOSBASE = '/obj/machinery/atmospherics'



@MapFix('openss13')
class RemoveOpenSS13Vars(Matcher):
    VARS_TO_REMOVE=('r_access','access_level','engine_access','lab_access','air_access','poison','allowed','freq','o2tanks','pltanks','poison','r_air','r_engine','r_lab','registered')
    def __init__(self):
        self.removed=[]
        
    def Matches(self, atom):
        for key in atom.mapSpecified:
            if key in self.VARS_TO_REMOVE:
                return True
        return False
    
    def Fix(self, atom):
        self.removed=[]
        for key in atom.mapSpecified:
            if key in self.VARS_TO_REMOVE:
                atom.mapSpecified.remove(key)
                del atom.properties[key]
                self.removed.append(key)
        return atom
    
    def __str__(self):
        if len(self.removed) == 0:
            return 'Remove Old OpenSS13 variables'
        return 'Removed old OpenSS13 variables: ' + ', '.join(self.removed)

@MapFix('openss13')
class RemoveIcon(Matcher):

    def __init__(self):
        pass

    def Matches(self, atom):
        return 'icon' in atom.mapSpecified

    def Fix(self, atom):
        atom.mapSpecified.remove('icon')
        return atom

    def __str__(self):
        return 'Remove broken icon variable (openss13)'
