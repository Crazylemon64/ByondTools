from __future__ import print_function

import logging

from PIL import Image
from builtins import range

from byond.errors import RenderError
from byond.directions import NORTH,SOUTH,EAST,WEST,IMAGE_INDICES

from .images import tint_image



def RenderToMapTile(tile, passnum, basedir, renderflags, **kwargs):
    """
    TODO: Add a resolution argument for higher res tilesets
    args:
        tile: A map tile from byond.map
        passnum:
        basedir:
        renderflags:
    kwargs:
        render_types:
        skip_alpha:
    """
    resolution = (96,96)
    img = Image.new('RGBA', resolution)
    tile.offset = (32, 32)
    foundAPixelOffset = False
    render_types = kwargs.get('render_types', ())
    skip_alpha = kwargs.get('skip_alpha', False)
    # for atom in sorted(tile.GetAtoms(), reverse=True):
    # This code is used in the Map Renderer too
    renderer = AtomRenderer(basedir)
    for atom in tile.SortAtoms():
        if len(render_types) > 0:
            found = False
            for path in render_types:
                if atom.path.startswith(path):
                    found = True
            if not found:
                continue

        # Ignore /areas.  They look like ass.
        if atom.path.startswith('/area'):
            if not (renderflags & MapRenderFlags.RENDER_AREAS):
                continue

        # We're going to turn space black for smaller images.
        if atom.path == '/turf/space':
            if not (renderflags & MapRenderFlags.RENDER_STARS):
                continue

        c_frame, isPixOffset = renderer.renderAtom(atom, resolution = (96,96), skip_alpha = skip_alpha)

        foundAPixelOffset |= isPixOffset
        if passnum == 0 and isPixOffset:
            return # Something something second pass
        img.paste(c_frame, (32 + pixel_x, 32 - pixel_y), c_frame)  # Add to the top of the stack.

    if passnum == 1 and not foundAPixelOffset:
        return None
    if not tile.areaSelected:
        # Fade out unselected tiles.
        bands = list(img.split())
        # Excluding alpha band
        for i in range(3):
            bands[i] = bands[i].point(lambda x: x * 0.4)
        img = Image.merge(img.mode, bands)

    return img

class MapRenderFlags(object):
    RENDER_STARS = 1
    RENDER_AREAS = 2

class AtomRenderer(object):
    """
    An object used to render multiple BYOND atoms.
    This exists to be able to conveniently cache image and dmi dat
    """
    def __init__(self, dmi_basepath):
        """
        Makes an instance of the AtomRenderer
        Args:
            dmi_basepath: A string to the base directory of the dmi files you wish to use
        """
        self._icons = {}
        self._dmis = {}
        self.dmi_basepath = dmi_basepath
        self.log = logging.getLogger(__name__)

    def renderAtom(self, atom, resolution = (96,96), skip_alpha = False):
        """
        Returns tuple of the following, in order:
            icon of the given atom.
            whether a pixel offset was found or not (prolly needs to go)
        args:
            atom: The atom to render
            resolution: The icon size to paste to. 3x default res because
                of large icons
        """
        aid = atom.ID
        pixel_offset_found = False

        if 'icon' not in atom.properties:
            self.log.critical('UNKNOWN ICON IN {0} (atom #{1})'.format(tile.origID, aid))
            self.log.info(atom.MapSerialize())
            self.log.info(atom.MapSerialize(Atom.FLAG_INHERITED_PROPERTIES))
            raise RenderError

        dmi_file = atom.properties['icon'].value

        if 'icon_state' not in atom.properties:
            # Grab default icon_state ('') if we can't find the one defined.
            atom.properties['icon_state'] = BYONDString("")

        state = atom.properties['icon_state'].value

        direction = SOUTH
        if 'dir' in atom.properties:
            try:
                direction = int(atom.properties['dir'].value)
            except ValueError:
                self.log.critical('FAILED TO READ dir = ' + repr(atom.properties['dir'].value))
                raise RenderError

        icon_key = '{0}|{1}|{2}'.format(dmi_file, state, direction)
        frame = None
        pixel_x = 0
        pixel_y = 0
        if icon_key in self._icons:
            frame, pixel_x, pixel_y = self._icons[icon_key]
        else:
            dmi_path = os.path.join(self.dmi_basepath, dmi_file)
            dmi = None
            if dmi_path in self._dmis:
                dmi = self._dmis[dmi_path]
            else:
                try:
                    dmi = DMI(dmi_path)
                    dmi.loadAll()
                    self._dmis[dmi_path] = dmi
                except Exception as e:
                    self.log.critical(str(e))
                    for prop in ['icon', 'icon_state', 'dir']:
                        self.log.info('\t{0}'.format(atom.dumpPropInfo(prop)))
                    pass
            if dmi.img is None:
                self.log.warning('Unable to open {0}!'.format(dmi_path))
                raise RenderError

            if dmi.img.mode not in ('RGBA', 'P'):
                logging.warn('{} is mode {}!'.format(dmi_file, dmi.img.mode))

            if direction not in IMAGE_INDICES:
                logging.warn('Unrecognized direction {} on atom {} in tile {}!'.format(direction, atom.MapSerialize(), self.origID))
                direction = SOUTH  # DreamMaker property editor shows dir = 2.  WTF?

            frame = dmi.getFrame(state, direction, 0)
            if frame == None:
                # Get the error/default state.
                frame = dmi.getFrame("", direction, 0)

            if frame == None:
                frame = Image('RGBA', resolution, (0,0,0,1))

            if frame.mode != 'RGBA':
                frame = frame.convert("RGBA")

            pixel_x = 0
            if 'pixel_x' in atom.properties:
                pixel_x = int(atom.properties['pixel_x'].value)

            pixel_y = 0
            if 'pixel_y' in atom.properties:
                pixel_y = int(atom.properties['pixel_y'].value)

            self._icons[icon_key] = (frame, pixel_x, pixel_y)

        # Handle BYOND alpha and coloring
        c_frame = frame
        alpha = int(atom.getProperty('alpha', 255))
        if skip_alpha:
            alpha = 255
        color = atom.getProperty('color', '#FFFFFF')
        if alpha != 255 or color != '#FFFFFF':
            c_frame = tint_image(frame, BYOND2RGBA(color, alpha))
        if pixel_x != 0 or pixel_y != 0:
            pixel_offset_found = True
        return c_frame, pixel_offset_found

class MapRenderer(object):
    """
    An object that can take a map and produce images for it.
    """
    def __init__(self, map):
        self.map = map
        self.generatedTexAtlas = False
        self.log = logging.getLogger(__name__)

    def generateTexAtlas(self, basedir, renderflags=0):
        if self.generatedTexAtlas:
            return
        self.log.info('--- Generating texture atlas...')
        self._icons = {}
        self._dmis = {}
        self.generatedTexAtlas = True
        # Not sure if tileTypes belongs in the map class or the renderer class
        for tid in range(len(self.tileTypes)):
            tile = self.tileTypes[tid]
            img = Image.new('RGBA', (96, 96))
            tile.offset = (32, 32)
            tile.areaSelected = True
            tile.render_deferred = False
            for atom in sorted(tile.GetAtoms(), reverse=True):
                # This code looks like it could be brought into its own function
                aid = atom.id
                # Ignore /areas.  They look like ass.
                if atom.path.startswith('/area'):
                    if not (renderflags & MapRenderFlags.RENDER_AREAS):
                        continue

                # We're going to turn space black for smaller images.
                if atom.path == '/turf/space':
                    if not (renderflags & MapRenderFlags.RENDER_STARS):
                        continue

                if 'icon' not in atom.properties:
                    self.log.critical('CRITICAL: UNKNOWN ICON IN {0} (atom #{1})'.format(tile.origID, aid))
                    self.log.info(atom.MapSerialize())
                    self.log.info(atom.MapSerialize(Atom.FLAG_INHERITED_PROPERTIES))
                    continue

                dmi_file = atom.properties['icon'].value

                if 'icon_state' not in atom.properties:
                    # Grab default icon_state ('') if we can't find the one defined.
                    atom.properties['icon_state'] = BYONDString("")

                state = atom.properties['icon_state'].value

                direction = SOUTH
                if 'dir' in atom.properties:
                    try:
                        direction = int(atom.properties['dir'].value)
                    except ValueError:
                        self.log.critical('FAILED TO READ dir = ' + repr(atom.properties['dir'].value))
                        continue

                icon_key = '{0}:{1}[{2}]'.format(dmi_file, state, direction)
                frame = None
                pixel_x = 0
                pixel_y = 0
                if icon_key in self._icons:
                    frame, pixel_x, pixel_y = self._icons[icon_key]
                else:
                    dmi_path = os.path.join(basedir, dmi_file)
                    dmi = None
                    if dmi_path in self._dmis:
                        dmi = self._dmis[dmi_path]
                    else:
                        try:
                            dmi = self.loadDMI(dmi_path)
                            self._dmis[dmi_path] = dmi
                        except Exception as e:
                            self.log.critical(str(e))
                            for prop in ['icon', 'icon_state', 'dir']:
                                self.log.info('\t{0}'.format(atom.dumpPropInfo(prop)))
                            pass

                    if dmi.img is None:
                        self.log.warn('Unable to open {0}!'.format(dmi_path))
                        continue

                    if dmi.img.mode not in ('RGBA', 'P'):
                        self.log.warn('{} is mode {}!'.format(dmi_file, dmi.img.mode))

                    if direction not in IMAGE_INDICES:
                        self.log.warn('Unrecognized direction {} on atom {} in tile {}!'.format(direction, atom.MapSerialize(), tile.origID))
                        direction = SOUTH  # DreamMaker property editor shows dir = 2.  WTF?

                    frame = dmi.getFrame(state, direction, 0)
                    if frame == None:
                        # Get the error/default state.
                        frame = dmi.getFrame("", direction, 0)

                    if frame == None:
                        continue

                    if frame.mode != 'RGBA':
                        frame = frame.convert("RGBA")

                    pixel_x = 0
                    if 'pixel_x' in atom.properties:
                        pixel_x = int(atom.properties['pixel_x'].value)

                    pixel_y = 0
                    if 'pixel_y' in atom.properties:
                        pixel_y = int(atom.properties['pixel_y'].value)

                    self._icons[icon_key] = (frame, pixel_x, pixel_y)
                img.paste(frame, (32 + pixel_x, 32 - pixel_y), frame)  # Add to the top of the stack.
                if pixel_x != 0 or pixel_y != 0:
                    tile.render_deferred = True
            tile.frame = img

            # Fade out unselected tiles.
            bands = list(img.split())
            # Excluding alpha band
            for i in range(3):
                bands[i] = bands[i].point(lambda x: x * 0.4)
            tile.unselected_frame = Image.merge(img.mode, bands)

            self.tileTypes[tid] = tile


    def generateImage(self, filename_tpl, basedir='.', renderflags=0, z=None, **kwargs):
        '''
        Instead of generating on a tile-by-tile basis, this creates a large canvas and places
        each atom on it after sorting layers.  This resolves the pixel_(x,y) problem.
        args:
            filename_tpl:
            basedir:
            renderflags:
            z:
        kwargs:
            area:
            render_types:
            skip_alpha:
        '''
        if z is None:
            for z in range(len(map.zLevels)):
                self.generateImage(filename_tpl, basedir, renderflags, z, **kwargs)
            return
        map.selectedAreas = ()
        skip_alpha = False
        render_types = ()
        if 'area' in kwargs:
            map.selectedAreas = kwargs['area']
        if 'render_types' in kwargs:
            render_types = kwargs['render_types']
        if 'skip_alpha' in kwargs:
            skip_alpha = kwargs['skip_alpha']

        self.log.info('Checking z-level {0}...'.format(z))
        instancePositions = {}
        for y in range(map.zLevels[z].height):
            for x in range(map.zLevels[z].width):
                t = map.zLevels[z].GetTile(x, y)
                # print('*** {},{}'.format(x,y))
                if t is None:
                    continue
                if len(self.selectedAreas) > 0:
                    renderThis = True
                    for atom in t.GetAtoms():
                        if atom.path.startswith('/area'):
                            if  atom.path not in self.selectedAreas:
                                renderThis = False
                    if not renderThis: continue
                for atom in t.GetAtoms():
                    if atom is None: continue
                    iid = atom.ID
                    if atom.path.startswith('/area'):
                        if  atom.path not in self.selectedAreas:
                            continue

                    # Check for render restrictions
                    if len(render_types) > 0:
                        found = False
                        for path in render_types:
                            if atom.path.startswith(path):
                                found = True
                        if not found:
                            continue

                    # Ignore /areas.  They look like ass.
                    if atom.path.startswith('/area'):
                        if not (renderflags & MapRenderFlags.RENDER_AREAS):
                            continue

                    # We're going to turn space black for smaller images.
                    if atom.path == '/turf/space':
                        if not (renderflags & MapRenderFlags.RENDER_STARS):
                            continue

                    if iid not in instancePositions:
                        instancePositions[iid] = []

                    # pixel offsets
                    '''
                    pixel_x = int(atom.getProperty('pixel_x', 0))
                    pixel_y = int(atom.getProperty('pixel_y', 0))
                    t_o_x = int(round(pixel_x / 32))
                    t_o_y = int(round(pixel_y / 32))
                    pos = (x + t_o_x, y + t_o_y)
                    '''
                    pos = (x, y)

                    instancePositions[iid].append(pos)

                    t=None

        if len(instancePositions) == 0:
            return

        self.log.info(' Rendering...')
        levelAtoms = []
        for iid in instancePositions:
            levelAtoms += [map.GetInstance(iid)]

        pic = Image.new('RGBA', ((map.zLevels[z].width + 2) * 32, (map.zLevels[z].height + 2) * 32), "black")

        # Bounding box, used for cropping.
        bbox = [99999, 99999, 0, 0]

        # Replace {z} with current z-level.
        filename = filename_tpl.replace('{z}', str(z))

        pastes = 0
        for atom in sorted(levelAtoms, reverse=True):
            if atom.ID not in instancePositions:
                levelAtoms.remove(atom)
                continue
            icon = self.renderAtom(atom, basedir, skip_alpha)
            if icon is None:
                levelAtoms.remove(atom)
                continue
            for x, y in instancePositions[atom.ID]:
                new_bb = self.getBBoxForAtom(x, y, atom, icon)
                # print('{0},{1} = {2}'.format(x, y, new_bb))
                # Adjust cropping bounds
                if new_bb[0] < bbox[0]:
                    bbox[0] = new_bb[0]
                if new_bb[1] < bbox[1]:
                    bbox[1] = new_bb[1]
                if new_bb[2] > bbox[2]:
                    bbox[2] = new_bb[2]
                if new_bb[3] > bbox[3]:
                    bbox[3] = new_bb[3]
                pic.paste(icon, new_bb, icon)
                pastes += 1
            icon=None # Cleanup
            levelAtoms.remove(atom)

        levelAtoms = None
        instancePositions = None

        if len(self.selectedAreas) == 0:
            # Autocrop (only works if NOT rendering stars or areas)
            #pic = trim(pic) # FIXME: MemoryError on /vg/.
            pic=pic # Hack
        else:
            # if nSelAreas == 0:
            #    continue
            pic = pic.crop(bbox)

        if pic is not None:
            # Saev
            filedir = os.path.dirname(os.path.abspath(filename))
            if not os.path.isdir(filedir):
                os.makedirs(filedir)
            self.log.info(' -> {} ({}x{}) - {} objects'.format(filename, pic.size[0], pic.size[1], pastes))
            pic.save(filename, 'PNG')



    def renderAtom(self, atom, basedir, skip_alpha=False):
        if 'icon' not in atom.properties:
            logging.critical('UNKNOWN ICON IN ATOM #{0} ({1})'.format(atom.ID, atom.path))
            logging.info(atom.MapSerialize())
            logging.info(atom.MapSerialize(Atom.FLAG_INHERITED_PROPERTIES))
            return None
        # else:
        #    logging.info('Icon found for #{}.'.format(atom.ID))

        dmi_file = atom.properties['icon'].value

        if dmi_file is None:
            return None

        # Grab default icon_state ('') if we can't find the one defined.
        state = atom.getProperty('icon_state', '')

        direction = SOUTH
        if 'dir' in atom.properties:
            try:
                direction = int(atom.properties['dir'].value)
            except ValueError:
                logging.critical('FAILED TO READ dir = ' + repr(atom.properties['dir'].value))
                return None

        icon_key = '{0}|{1}|{2}'.format(dmi_file, state, direction)
        frame = None
        pixel_x = 0
        pixel_y = 0
        if icon_key in _icons:
            frame, pixel_x, pixel_y = _icons[icon_key]
        else:
            dmi_path = os.path.join(basedir, dmi_file)
            dmi = None
            if dmi_path in _dmis:
                dmi = _dmis[dmi_path]
            else:
                try:
                    dmi = DMI(dmi_path)
                    dmi.loadAll()
                    _dmis[dmi_path] = dmi
                except Exception as e:
                    self.log.critical(str(e))
                    for prop in ['icon', 'icon_state', 'dir']:
                        self.log.info('\t{0}'.format(atom.dumpPropInfo(prop)))
                    pass
            if dmi.img is None:
                logging.warning('Unable to open {0}!'.format(dmi_path))
                return None

            if dmi.img.mode not in ('RGBA', 'P'):
                logging.warn('{} is mode {}!'.format(dmi_file, dmi.img.mode))

            if direction not in IMAGE_INDICES:
                logging.warn('Unrecognized direction {} on atom {}!'.format(direction, str(atom)))
                direction = SOUTH  # DreamMaker property editor shows dir = 2.  WTF?

            frame = dmi.getFrame(state, direction, 0)
            if frame == None:
                # Get the error/default state.
                frame = dmi.getFrame("", direction, 0)

            if frame == None:
                return None

            if frame.mode != 'RGBA':
                frame = frame.convert("RGBA")

            pixel_x = 0
            if 'pixel_x' in atom.properties:
                pixel_x = int(atom.properties['pixel_x'].value)

            pixel_y = 0
            if 'pixel_y' in atom.properties:
                pixel_y = int(atom.properties['pixel_y'].value)

            _icons[icon_key] = (frame, pixel_x, pixel_y)

        # Handle BYOND alpha and coloring
        c_frame = frame
        alpha = int(atom.getProperty('alpha', 255))
        if skip_alpha:
            alpha = 255
        color = atom.getProperty('color', '#FFFFFF')
        if alpha != 255 or color != '#FFFFFF':
            c_frame = tint_image(frame, BYOND2RGBA(color, alpha))
        return c_frame
