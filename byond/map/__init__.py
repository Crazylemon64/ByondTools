# This file suffers from obesity
"""
Map Interface Module

Copyright 2013 Rob "N3X15" Nelson <nexis@7chan.org>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""
from __future__ import print_function
import os, itertools, sys, numpy, logging, hashlib

from byond.map.format import GetMapFormat
from byond.DMI import DMI
from byond.directions import SOUTH, IMAGE_INDICES
from byond.basetypes import Atom, BYONDString, BYONDValue, BYONDFileRef
from byond.color import BYOND2RGBA
# from byond.objtree import ObjectTree

from builtins import range

# Cache
_icons = {}
_dmis = {}

# LoadMapFormats()

class LocationIterator(object):
    def __init__(self, _map):
        self.map = _map
        self.x = -1
        self.y = 0
        self.z = 0

        self.max_z = len(self.map.zLevels)

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        self.x += 1

        zLev = self.map.zLevels[self.z]

        if self.x >= zLev.width:
            self.y += 1
            self.x = 0

        if self.y >= zLev.height:
            self.z += 1
            self.y = 0

        if self.z >= self.max_z:
            raise StopIteration

        t = self.map.GetTileAt(self.x, self.y, self.z)
        # print('{} = {}'.format((self.x,self.y,self.z),str(t)))
        return t

class TileIterator(object):
    def __init__(self, _map):
        self.map = _map
        self.pos = -1
        self.max = len(self.map.tiles)

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        self.pos += 1

        if self.pos >= self.max:
            raise StopIteration

        t = self.map.tiles[self.pos]
        #print('#{} = {}'.format(self.pos,str(t)))
        return t

class AtomIterator(object):
    def __init__(self, _map):
        self.map = _map
        self.pos = -1
        self.max = len(self.map.instances)

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        self.pos += 1

        if self.pos >= self.max:
            raise StopIteration

        t = self.map.instances[self.pos]
        # print('#{} = {}'.format(self.pos,str(t)))
        return t

class Tile(object):
    def __init__(self, _map, master=False):
        # : Map's copy of the tile, used for tracking.
        self.master = master
        self.coords = (0, 0, 0)
        self.origID = ''
        self.ID = -1
        self.instances = []
        self.locations = []
        self.frame = None
        self.unselected_frame = None
        self.areaSelected = True
        self.log = logging.getLogger(__name__ + '.Tile')
        self.map = _map
        self._hash = None
        self.orig_hash = None

    def __str__(self):
        return self._serialize()

    def _serialize(self):
        return ','.join([str(i) for i in self.GetAtoms()])

    def __ne__(self, tile):
        return not self.__eq__(tile)

    def __eq__(self, other):
        return other and ((other._hash and self._hash and self._hash == other._hash) or (len(self.instances) == len(other.instances) and self.instances == other.instances))
        # else:
        #    return all(self.instances[i] == other.instances[i] for i in range(len(self.instances)))


    def UpdateHash(self, no_map_update=False):
        if self._hash is None:
            # Why MD5?  Because the shorter the string, the faster the comparison.
            self._hash = hashlib.md5(str(self).encode(encoding='utf_8')).hexdigest()
            if not no_map_update:
                self.ID=self.map.UpdateTile(self)
                if self.ID==-1:
                    raise Error('self.ID == -1')

    def InvalidateHash(self):
        if self._hash is not None:
            self.orig_hash = self._hash
        self._hash = None

    def GetHash(self):
        self.UpdateHash()
        return self._hash

    def RemoveAtom(self, atom, hash=True):
        '''
        :param Atom atom:
            Atom to remove.  Raises ValueError if not found.
        '''
        if atom is None: return
        self.instances.remove(atom.ID)
        self.InvalidateHash()
        if hash: self.UpdateHash()

    def AppendAtom(self, atom, hash=True):
        '''
        :param Atom atom:
            Atom to add.
        '''
        if atom is None: return
        atom.UpdateMap(self.map)
        self.instances.append(atom.ID)
        self.InvalidateHash()
        if hash: self.UpdateHash()

    def CountAtom(self, atom):
        '''
        :param Atom atom:
            Atom to count.
        :return int: Count of atoms
        '''
        return self.instances.count(atom.ID)

    def copy(self, origID=False):
        tile = self.map.CreateTile()
        tile.ID = self.ID
        tile.instances = [x for x in self.instances]

        if origID:
            tile.origID = self.origID

        if not self._hash:
            self.UpdateHash(no_map_update=True)
        tile._hash = self._hash

        return tile

    def GetAtoms(self):
        atoms = []
        for id in self.instances:
            if id is None:
                continue
            a = self.map.GetInstance(id)
            if a is None:
                self.log.debug('Unknown instance ID {}!'.format(id))
                continue
            atoms += [a]
        return atoms

    def SortAtoms(self):
        return sorted(self.GetAtoms(), reverse=True)

    def GetAtom(self, idx):
        return self.map.GetInstance(self.instances[idx])

    def GetInstances(self):
        return self.instances

    def rmLocation(self, coord, autoclean=True):
        if coord in self.locations:
            self.locations.remove(coord)
        if autoclean and len(self.locations) == 0:
            self.map.tiles[self.ID] = None  # Mark ready for recovery
            self.map._tile_idmap.pop(self.GetHash(), None)

    def addLocation(self, coord):
        if coord not in self.locations:
            self.locations.append(coord)

class MapLayer(object):
    def __init__(self, z, _map, height=255, width=255):
        self.initial_load=False
        self.map = _map
        self.min = (0, 0)
        self.max = (height - 1, width - 1)
        self.tiles = None
        self.Resize(height, width)
        self.z = z


    def GetTile(self, x, y):
        # return self.tiles[y][x]
        t = self.map.GetTileByID(self.tiles[x, y])
        t.coords = (x, y, self.z)
        return t

    def SetTile(self, x, y, tile):
        '''
        :param x int:
        :param y int:
        :param tile Tile:
        '''

        '''
        if not self.initial_load:
            # Remove old tile.
            oldid = self.tiles[x, y]
            if oldid < len(self.map.instances):
                t = self.map.tiles[oldid]
                if t: t.rmLocation((x, y, self.z))
        '''

        # Set new tile.
        if not self.initial_load:
            tile.ID=self.map.UpdateTile(tile)
        self.tiles[x, y] = tile.ID
        #self.map.tiles[tile.ID].addLocation((x, y, self.z))



    def SetTileID(self, x, y, newID):
        '''
        :param x int:
        :param y int:
        :param newID int:
        '''
        if newID is None:
            raise Exception('newID cannot be None')

        t = self.map.tiles[newID]
        if t is None:
            raise KeyError('Unknown tile #{}'.format(newID))

        #self.SetTile(x, y, t)

        '''
        if not self.initial_load:
            # Remove old tile.
            oldid = self.tiles[x, y]
            if oldid < len(self.map.instances):
                t = self.map.tiles[oldid]
                if t: t.rmLocation((x, y, self.z))
        '''

        self.tiles[x, y] = newID
        #self.map.tiles[newID].addLocation((x, y, self.z))

    def Resize(self, height, width):
        self.height = height
        self.width = width

        basetile = self.map.basetile;
        if self.tiles is None:
            self.tiles = numpy.empty((height, width), int)  # object)
            for y in range(height):
                for x in range(width):
                    self.SetTile(x, y, basetile)
        else:
            self.tiles.resize(height, width)

        # self.tiles = [[Tile(self.map) for _ in range(width)] for _ in range(height)]

class Map(object):
    def __init__(self, tree=None, **kwargs):
        self.zLevels = []

        self._instance_idmap = {}  # md5 -> id
        self._tile_idmap = {}  # md5 -> id

        self.basetile = Tile(self)

        self.instances = []  # Atom
        self.tiles = []  # Tile

        self.DMIs = {}
        self.tree = tree
        self.generatedTexAtlas = False
        self.selectedAreas = ()
        self.whitelistTypes = None
        self.forgiving_atom_lookups = kwargs.get('forgiving_atom_lookups', False)

        self.log = logging.getLogger(__name__ + '.Map')

        self.missing_atoms = set()

        self.basetile.UpdateHash();

    def ResetTilestore(self):
        '''For loading maps.  Resets tile data to a pristine state.'''

        self.instances = []  # Atom
        self.tiles = []  # Tile
        self.basetile = None

    def GetTileByID(self, tileID):
        t = self.tiles[tileID]
        if t is None:
            return None
        t = t.copy()
        t.master = False
        return t

    def GetInstance(self, atomID):
        a=None
        try:
            a = self.instances[atomID]
        except IndexError as e:
            self.log.critical('Unable to find instance {}!')
            raise e
        if a is None:
            # print('WARNING: #{0} not found'.format(atomID))
            return None
        a = a.copy()
        # a.master = False
        return a

    def UpdateTile(self, t):
        '''
        Update tile registry.

        :param t Tile:
            Tile to update.
        :return Tile ID:
        '''
        thash = t.GetHash()

        # if t.ID >= 0 and t.ID < len(self.tiles) and self.tiles[t.ID] is not None:
        #    self.tiles[t.ID].rmLocation(t.coords)

        tiles_action = "-"
        '''
        if t in self.tiles:
            t.ID = self.tiles.index(t)
        else:
        '''

        idmap_action = "-"
        if thash not in self._tile_idmap:
            idmap_action = "Added"

            t.ID = len(self.tiles)
            self.tiles += [t.copy()]
            self._tile_idmap[thash] = t.ID
            tiles_action = "Added"
            #print('Assigned ID #{} to tile {}'.format(t.ID,thash))
        elif self._tile_idmap[thash] != t.ID:
            t.ID = self._tile_idmap[thash]
            idmap_action = "Updated"
            #print('Updated tile {1} to ID #{0}'.format(t.ID,thash))

        #print('Updated #{} - Tiles: {}, idmap: {}'.format(t.ID, thash, tiles_action, idmap_action))

        self.tiles[t.ID].addLocation(t.coords)
        return t.ID

    def UpdateAtom(self, a):
        '''
        Update tile registry.

        :param a Atom: Tile to update.
        '''
        thash = a.GetHash()

        if a.ID and len(self.instances) < a.ID and self.instances[a.ID] is not None:
            self.instances[a.ID].rmLocation(self, a.coords)

        if thash not in self._instance_idmap:
            a.ID = len(self.instances)
            self.instances += [a.copy()]
            self._instance_idmap[thash] = a.ID
            #print('Assigned ID #{} to atom {}'.format(a.ID,thash))
        else:
            a.ID = self._instance_idmap[thash]
        if a.coords is not None:
            self.instances[a.ID].addLocation(a.coords)
        return a.ID

    def RemoveAtom(self, a):
        '''
        Remove atom from the entire map.

        :param a Atom: Tile to update.
        '''
        thash = a.GetHash()

        if a.ID and len(self.instances) < a.ID and self.instances[a.ID] is not None:
            self.instances[a.ID].rmLocation(self, a.coords)
            del self.instances[a.ID]

        if thash in self._instance_idmap:
            del self._instance_idmap[thash]

    def CreateZLevel(self, height, width, z= -1):
        zLevel = MapLayer(z if z >= 0 else len(self.zLevels), self, height, width)
        if z >= 0:
            self.zLevels[z] = zLevel
        else:
            self.zLevels.append(zLevel)
        return zLevel

    def Atoms(self):
        '''Iterates over all instances in the map.
        '''
        return AtomIterator(self)

    def Tiles(self):
        '''Iterates over all tiles of the map.
        '''
        return TileIterator(self)

    def Locations(self):
        return LocationIterator(self)

    def Load(self, filename, **kwargs):
        _, ext = os.path.splitext(filename)
        fmt = kwargs.get('format', 'dmm2' if ext == 'dmm2' else 'dmm')
        reader = GetMapFormat(self, fmt)
        reader.Load(filename, **kwargs)

    def Save(self, filename, **kwargs):
        _, ext = os.path.splitext(filename)
        fmt = kwargs.get('format', 'dmm2' if ext == 'dmm2' else 'dmm')
        reader = GetMapFormat(self, fmt)
        reader.Save(filename, **kwargs)

    def writeMap2(self, filename, flags=0):
        self.filename = filename
        tileFlags = 0
        atomFlags = 0
        if flags & Map.WRITE_OLD_IDS:
            tileFlags |= Tile.FLAG_USE_OLD_ID
            atomFlags |= Atom.FLAG_USE_OLD_ID
        padding = len(self.tileTypes[-1].ID2String())
        with open(filename, 'w') as f:
            f.write('// Atom Instances\n')
            for atom in self.instances:
                f.write('{0} = {1}\n'.format(atom.ID, atom.MapSerialize(atomFlags)))
            f.write('// Tiles\n')
            for tile in self.tileTypes:
                f.write('{0}\n'.format(tile.MapSerialize2(tileFlags, padding)))
            f.write('// Layout\n')
            for z in self.zLevels.keys():
                f.write('\n(1,1,{0}) = {{"\n'.format(z))
                zlevel = self.zLevels[z]
                for y in range(zlevel.height):
                    for x in range(zlevel.width):
                        tile = zlevel.GetTileAt(x, y)
                        if flags & Map.WRITE_OLD_IDS:
                            f.write(tile.origID)
                        else:
                            f.write(tile.ID2String(padding))
                    f.write("\n")
                f.write('"}\n')

    def GetTileAt(self, x, y, z):
        '''
        :param int x:
        :param int y:
        :param int z:
        :rtype Tile:
        '''
        if z < len(self.zLevels):
            return self.zLevels[z].GetTile(x, y)

    def CopyTileAt(self, x, y, z):
        '''
        :param int x:
        :param int y:
        :param int z:
        :rtype Tile:
        '''
        return self.GetTileAt(x, y, z).copy()

    def SetTileAt(self, x, y, z, tile):
        '''
        :param int x:
        :param int y:
        :param int z:
        '''
        if z < len(self.zLevels):
            self.zLevels[z].SetTile(x, y, tile)

    def CreateTile(self):
        '''
        :rtype Tile:
        '''
        return Tile(self)

    def getBBoxForAtom(self, x, y, atom, icon):
        icon_width, icon_height = icon.size
        pixel_x = int(atom.getProperty('pixel_x', 0))
        pixel_y = int(atom.getProperty('pixel_y', 0))

        return self.tilePosToBBox(x, y, pixel_x, pixel_y, icon_height, icon_width)

    def tilePosToBBox(self, tile_x, tile_y, pixel_x, pixel_y, icon_height, icon_width):
        # Tile Pos
        X = tile_x * 32
        Y = tile_y * 32

        # pixel offsets
        X += pixel_x
        Y -= pixel_y

        # BYOND coordinates -> PIL coords.
        # BYOND uses LOWER left.
        # PIL uses UPPER left
        X += 0
        Y += 32 - icon_height

        return (
            X,
            Y,
            X + icon_width,
            Y + icon_height
        )

    # So we can read a map without parsing the tree.
    def GetAtom(self, path):
        if self.tree is not None:
            atom = self.tree.GetAtom(path)
            if atom is None and self.forgiving_atom_lookups:
                self.missing_atoms.add(path)
                return Atom(path, '(map)', missing=True)
            return atom
        return Atom(path)
