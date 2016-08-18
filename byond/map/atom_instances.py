import collections

class AtomMapInstance(object):
    """
    An instance of an atom being loaded into a map.
    Used to separate an Atom in code from an Atom with given
    attributes being loaded onto a map
    """

#
# "special" functions (init, str, eq...)
#

    def __init__(self, path, filename='', line=0, **kwargs):
        """
        :kparam bool missing:
            Set if this is found in a map, but missing in code
        """
        #: Loaded from map, but missing in the code. (Maps only)
        self.missing = kwargs.get('missing', False)

        #: The path of our instance
        self.path = path

        #: Instance ID (maps only).  Used internally, do NOT change.
        self.ID = None

        #: Instance ID that was read from the map.
        self.old_id = None

        #: List of var names that were specified by the map, if atom was loaded from a :class:`byond.map.Map`.
        self.mapSpecified = []

        #: Used for masters to track instance locations.
        self.locations = []

        #: Used to differentiate from other atom map instances
        self._hash = None

        #: Vars of this atom instance and their value
        self.properties = collections.OrderedDict()

        #: Coords
        self.coords = None

        #TODO: Load in our properties from the "Atom" class once the code has been
        # read from our codebase


    def __str__(self):
        return self.serialize(self.mapSpecified if len(self.mapSpecified) > 0 else None)

#
# MAPPING STUFF
#

    def addLocation(self, coord):
        """
        This adds a `coord` to the locations array, whatever that means

        :param ??? coord:
            A coordinate(?) to add to the `locations` array
        """
        self.locations.append(coord)


    def rmLocation(self, map, coord, autoclean=True):
        """
        This has something to do with mapping - it also removes the atom from
        the map if autoclean is set

        :param Map map:
            A map to remove this atom from
        :param ??? coord:
            A coordinate to remove from the `locations` array
        """
        if coord in self.locations:
            self.locations.remove(coord)
        if autoclean and len(self.locations) == 0:
            map.instances[self.ID] = None  # Mark ready for recovery
            map._instance_idmap.pop(self.GetHash(), None)

    def UpdateMap(self, map):
        self.UpdateHash()
        map.UpdateAtom(self)

    def copy(self, toNewMap=False):
        '''
        Make a copy of this atom map instance, without dangling references.

        :returns byond.map.atom_instances.AtomMapInstance
        '''
        new_node = __class__(self.path, self.filename, self.line, missing = self.missing)
        new_node.properties = self.properties.copy()
        new_node.UpdateHash()
        # new_node.parent = self.parent
        new_node.mapSpecified = self.mapSpecified
        if not toNewMap:
            new_node.ID = self.ID
            new_node.old_id = self.old_id
        return new_node

    def serialize(self, propkeys=None):
        atomContents = []
        for key, val in self.properties.items():
            if propkeys is None or key in propkeys:
                atomContents += ['{0}={1}'.format(key,val)]
        return '{}{{{}}}'.format(self.path, ';'.join(atomContents))


#
# HASHING STUFF
#

    def GetHash(self):
        self.UpdateHash()
        return self._hash

    def UpdateHash(self, no_map_update=False):
        if self._hash is None:
            self._hash = hashlib.md5(str(self).encode(encoding='utf_8')).hexdigest()

    def InvalidateHash(self):
        self._hash = None
