import collections, hashlib

from .basetypes import PropertyFlags

class Atom(object):
    '''
    An atom is, in simple terms, what BYOND considers a class.
        Not quite true - the REAL base of BYOND inheritence is /datum, but
        I'll need to restructure this

    :param string path:
        The absolute path of this atom.  ex: */obj/item/weapon/gun*
    :param string filename:
        The file this atom originated from.
    :param int line:
        The line in the aforementioned file.
    '''

    # : Prints all inherited properties, not just the ones that are mapSpecified.
    FLAG_INHERITED_PROPERTIES = 1

    # : writeMap2 prints old_ids instead of the actual IID.
    FLAG_USE_OLD_ID = 2

    def __init__(self, path, filename='', line=0, **kwargs):
        global TURF_LAYER, AREA_LAYER, OBJ_LAYER, MOB_LAYER

        # : Absolute path of this atom
        self.path = path

        # : Vars of this atom, including inherited vars.
        self.properties = collections.OrderedDict()

        # : List of var names that were specified by the map, if atom was loaded from a :class:`byond.map.Map`.
        self.mapSpecified = []

        # : Child atoms and procs.
        self.children = {}

        # : The parent of this atom.
        self.parent = None

        # : The file this atom originated from.
        self.filename = filename

        # : Line from the originating file.
        self.line = line

        # : Instance ID (maps only).  Used internally, do NOT change.
        self.ID = None

        # : Instance ID that was read from the map.
        self.old_id = None

        # : Used internally.
        self.ob_inherited = False

        # : Loaded from map, but missing in the code. (Maps only)
        self.missing = kwargs.get('missing', False)

        # if not self.missing and path == '/area/engine/engineering':
        #    raise Exception('God damnit')

        self._hash = None

        # : Coords
        self.coords = None

        # : Used for masters to track instance locations.
        self.locations = []

    def rmLocation(self, map, coord, autoclean=True):
        if coord in self.locations:
            self.locations.remove(coord)
        if autoclean and len(self.locations) == 0:
            map.instances[self.ID] = None  # Mark ready for recovery
            map._instance_idmap.pop(self.GetHash(), None)

    def addLocation(self, coord):
        self.locations.append(coord)

    def UpdateHash(self, no_map_update=False):
        if self._hash is None:
            self._hash = hashlib.md5(str(self).encode(encoding='utf_8')).hexdigest()

    def UpdateMap(self, map):
        self.UpdateHash()
        map.UpdateAtom(self)

    def InvalidateHash(self):
        self._hash = None

    def GetHash(self):
        self.UpdateHash()
        return self._hash

    def copy(self, toNewMap=False):
        '''
        Make a copy of this atom, without dangling references.

        :returns byond.basetypes.Atom
        '''
        new_node = Atom(self.path, self.filename, self.line, missing=self.missing)
        new_node.properties = self.properties.copy()
        new_node.mapSpecified = self.mapSpecified
        if not toNewMap:
            new_node.ID = self.ID
            new_node.old_id = self.old_id
        new_node.UpdateHash()
        # new_node.parent = self.parent
        return new_node

    def getProperty(self, index, default=None):
        '''
        Get the value of the specified property.

        :param string index:
            The name of the var we want.
        :param mixed default:
            Default value, if the var cannot be found.
        :returns:
            The desired value.
        '''
        prop = self.properties.get(index, None)
        if prop == None:
            return default
        elif prop == 'null':
            return None
        return prop.value

    def setProperty(self, index, value, flags=0):
        '''
        Set the value of a property.

        In the event the property cannot be found, a new property is added.

        This function will attempt to convert python types to BYOND types.
        Hints can be provided in the form of PropertyFlags given to *flags*.

        :param string index:
            The name of the var desired.
        :param mixed value:
            The new value.
        :param int flags:
            Changes value assignment behavior.

            +------------------------------------+------------------------------------------------+
            | Flag                               | Effect                                         |
            +====================================+================================================+
            | :attr:`PropertyFlag.MAP_SPECIFIED` | Adds the property to *mapSpecified*, if needed.|
            +------------------------------------+------------------------------------------------+
            | :attr:`PropertyFlag.STRING`        | Forces conversion of value to a BYONDString.   |
            +------------------------------------+------------------------------------------------+
            | :attr:`PropertyFlag.FILEREF`       | Forces conversion of value to a BYONDFileRef.  |
            +------------------------------------+------------------------------------------------+
            | :attr:`PropertyFlag.VALUE`         | Forces conversion of value to a BYONDValue.    |
            +------------------------------------+------------------------------------------------+

        :returns:
            The desired value.
        '''
        if flags & PropertyFlags.MAP_SPECIFIED:
            if index not in self.mapSpecified:
                self.mapSpecified += [index]
        if flags & PropertyFlags.VALUE:
            self.properties[index] = BYONDValue(value)
        elif isinstance(value, str) or flags & PropertyFlags.STRING:
            if flags & PropertyFlags.STRING:
                value = str(value)
            self.properties[index] = BYONDString(value)
        elif flags & PropertyFlags.FILEREF:
            if flags & PropertyFlags.FILEREF:
                value = str(value)
            self.properties[index] = BYONDFileRef(value)
        else:
            self.properties[index] = BYONDValue(value)

        self.UpdateHash()

    def InheritProperties(self):
        if self.ob_inherited: return
        # debugInheritance=self.path in ('/area','/obj','/mob','/atom/movable','/atom')
        if self.parent:
            if not self.parent.ob_inherited:
                self.parent.InheritProperties()
            for key in sorted(self.parent.properties.keys()):
                value = self.parent.properties[key].copy()
                if key not in self.properties:
                    self.properties[key] = value
                    self.properties[key].inherited = True
                    # if debugInheritance:print('  {0}[{2}] -> {1}'.format(self.parent.path,self.path,key))
        # assert 'name' in self.properties
        self.ob_inherited = True
        for k in viewkeys(self.children):
            self.children[k].InheritProperties()

    def __ne__(self, atom):
        return not self.__eq__(atom)

    def __eq__(self, atom):
        if atom == None:
            return False
        # if self.mapSpecified != atom.mapSpecified:
        #    return False
        if self.path != atom.path:
            return False
        return self.properties == atom.properties

    def handle_math(self, expr):
        if isinstance(expr, str):
            return eval_expr(expr)
        return expr

    def __lt__(self, other):
        if 'layer' not in self.properties or 'layer' not in other.properties:
            return False
        myLayer = 0
        otherLayer = 0
        try:
            myLayer = self.handle_math(self.getProperty('layer', myLayer))
        except ValueError:
            print('Failed to parse {0} as float.'.format(self.properties['layer'].value))
            pass
        try:
            otherLayer = self.handle_math(other.getProperty('layer', otherLayer))
        except ValueError:
            print('Failed to parse {0} as float.'.format(other.properties['layer'].value))
            pass
        return myLayer > otherLayer

    def __gt__(self, other):
        if 'layer' not in self.properties or 'layer' not in other.properties:
            return False
        myLayer = 0
        otherLayer = 0
        try:
            myLayer = self.handle_math(self.getProperty('layer', myLayer))
        except ValueError:
            print('Failed to parse {0} as float.'.format(self.properties['layer'].value))
            pass
        try:
            otherLayer = self.handle_math(other.getProperty('layer', otherLayer))
        except ValueError:
            print('Failed to parse {0} as float.'.format(other.properties['layer'].value))
            pass
        return myLayer < otherLayer

    def __str__(self):
        atomContents = []
        for key, val in self.properties.items():
            atomContents += ['{0}={1}'.format(key, val)]
        return '{}{{{}}}'.format(self.path, ';'.join(atomContents))

    def dumpPropInfo(self, name):
        o = '{0}: '.format(name)
        if name not in self.properties:
            return o + 'None'
        return o + repr(self.properties[name])

    def _DumpCode(self):
        divider = '//' + ((len(self.path) + 2) * '/') + '\n'
        o = divider
        o += '// ' + self.path + '\n'
        o += divider

        o += self.path + '\n'

        # o += '\t//{0} properties total\n'.format(len(self.properties))
        written=[]
        for name in sorted(self.properties.keys()):
            prop = self.properties[name]
            if prop.inherited: continue
            _type = prop.type
            if not _type.endswith('/'):
                _type += '/'
            prefix = ''
            if prop.declaration:
                prefix = 'var'
            if not prop.declaration:  # and _type == '/':
                _type = ''
            o += '\t{prefix}{type}{name}'.format(prefix=prefix, type=_type, name=name)
            if prop.value is not None:
                o += ' = {value}'.format(value=str(prop))
            o += '\n'

        # o += '\n'
        # o += '\t//{0} children total\n'.format(len(self.children))
        procs = ''
        children = ''
        written=[]
        for ck in sorted(self.children.keys()):
            if ck in written:
                continue
            written.append(ck)
            #co = '\n// ck='+repr(ck)
            co = '\n'
            co += self.children[ck]._DumpCode()
            if isinstance(self.children[ck], Proc):
                procs += co
            else:
                children += co
        o += procs + children
        return o

    def DumpCode(self):
        return self._DumpCode()
