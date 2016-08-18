import collections, hashlib

from future.utils import viewkeys

from byond.utils import eval_expr

from .basetypes import PropertyFlags, BYONDValue, BYONDFileRef, BYONDString
from .proc import Proc

class Datum(object):
    '''
    A datum is, in simple terms, what BYOND considers a class.
    If you're wondering why this is so weird, it's because this used to be for
    "atom" and was mungled in with map instance code

    :param string path:
        The absolute path of this datum.  ex: */obj/item/weapon/gun*
    :param string filename:
        The file this datum originated from.
    :param int line:
        The line in the aforementioned file.
    '''

    #: Prints all inherited properties, not just the ones that are mapSpecified.
    FLAG_INHERITED_PROPERTIES = 1

    #: writeMap2 prints old_ids instead of the actual IID.
    FLAG_USE_OLD_ID = 2

    def __init__(self, path, filename='', line=0, **kwargs):
        global TURF_LAYER, AREA_LAYER, OBJ_LAYER, MOB_LAYER

        #: Absolute path of this datum
        self.path = path

        #: Vars of this datum, including inherited vars.
        self.properties = collections.OrderedDict()

        #: Procs of this datum, including inherited procs.
        self.procs = collections.OrderedDict()

        #: Child datums and procs.
        self.children = {}

        #: The parent of this datum.
        self.parent = None

        #: The file this datum originated from.
        self.filename = filename

        #: Line from the originating file.
        self.line = line

        #: Used internally.
        self.ob_inherited = False

        self._hash = None

    def __ne__(self, datum):
        return not self.__eq__(datum)

    def __eq__(self, datum):
        if datum == None:
            return False
        # if self.mapSpecified != datum.mapSpecified:
        #    return False
        if self.path != datum.path:
            return False
        return self.properties == datum.properties


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
        return self.serialize(self.mapSpecified if len(self.mapSpecified) > 0 else None)



    def UpdateHash(self):
        if self._hash is None:
            self._hash = hashlib.md5(str(self).encode(encoding='utf_8')).hexdigest()

    def InvalidateHash(self):
        self._hash = None

    def GetHash(self):
        self.UpdateHash()
        return self._hash

    def copy(self):
        '''
        Make a copy of this datum, without dangling references.

        :returns byond.basetypes.Datum
        '''
        new_node = self.__class__(self.path, self.filename, self.line)
        new_node.properties = self.properties.copy()
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

    def handle_math(self, expr):
        if isinstance(expr, str):
            return eval_expr(expr)
        return expr


    def serialize(self, propkeys=None):
        datumContents = []
        for key, val in self.properties.items():
            if propkeys is None or key in propkeys:
                datumContents += ['{0}={1}'.format(key, val)]
        return '{}{{{}}}'.format(self.path, ';'.join(datumContents))

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
