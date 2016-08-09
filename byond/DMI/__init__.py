from __future__ import print_function, absolute_import
import sys, os, glob, string, traceback, fnmatch, math, shutil, collections

from PIL import Image, PngImagePlugin
import logging
# Py 2/3 bridge imports
from builtins import range
from future.utils import viewitems

from byond.DMIH import *
from .State import State

class DMILoadFlags(object):
    NoImages = 1
    NoPostProcessing = 2


class DMI(object):
    MovementTag = '\t'
    def __init__(self, filename):
        self.filename = filename
        self.version = ''
        self.states = collections.OrderedDict()  # {}
        self.icon_width = 32
        self.icon_height = 32
        self.pixels = None
        self.size = ()
        self.statelist = 'LOLNONE'
        self.max_x = -1
        self.max_y = -1
        self.img = None

    def make(self, makefile):
        print('>>> Compiling %s -> %s' % (makefile, self.filename))
        h = DMIH()
        h.parse(makefile)
        for node in h.tokens:
            if type(node) is Variable:
                if node.name == 'height':
                    self.icon_height = node.value
                elif node.name == 'weight':
                    self.icon_width = node.value
            elif type(node) is directives.State:
                self.states[node.state.key()] = node.state
            elif type(node) is directives.Import:
                if node.ftype == 'dmi':
                    dmi = DMI(node.filedef)
                    dmi.extractTo("_tmp/" + os.path.basename(node.filedef))
                    for name in dmi.states:
                        self.states[name] = dmi.states[name]

    def save(self, to, **kwargs):
        if len(self.states) == 0:
            return  # Nope.
        # Now build the manifest
        manifest = '#BEGIN DMI'
        manifest += '\nversion = 4.0'
        manifest += '\n\twidth = {0}'.format(self.icon_width)
        manifest += '\n\theight = {0}'.format(self.icon_height)

        frames = []
        fdata = []

        # Sort by name because I'm autistic like that.
        ordered = self.states
        if kwargs.get('sort', True):
            ordered = sorted(self.states.keys())

        for name in ordered:
            if len(self.states[name].icons) > 0:
                manifest += self.states[name].genManifest()
                numIcons = self.states[name].numIcons()
                lenIcons = len(self.states[name].icons)
                if numIcons != lenIcons:
                    logging.warn('numIcons={0}, len(icons)={1} in state {2}!'.format(numIcons, lenIcons, name))
                # frames += self.states[name].icons
                # frames.extend(self.states[name].icons)
                for i in range(len(self.states[name].icons)):
                    fdata += ['{}[{}]'.format(self.states[name].name, i)]
                    frames += [self.states[name].icons[i]]
            else:
                logging.warn('State {0} has 0 icons.'.format(name))
        manifest += '\n#END DMI'

        # print(manifest)

        # Next bit borrowed from DMIDE.
        icons_per_row = math.ceil(math.sqrt(len(frames)))
        rows = icons_per_row

        if len(frames) > icons_per_row * rows:
            rows += 1

        sheet = Image.new('RGBA', (int((icons_per_row + 1) * self.icon_width), int(rows * self.icon_height)))

        x = 0
        y = 0
        # for frame in frames:
        # print('per_row={0}, rows={1}, size={2}'.format(icons_per_row,rows,sheet.size))
        for f in range(len(frames)):
            frame = frames[f]
            icon = frame
            if isinstance(frame, str):
                icon = Image.open(frame, 'r')
            box = (x * self.icon_width, y * self.icon_height)
            # print('{0} -> ({1},{2}) {3} {4}'.format(f,x,y,box,fdata[f]))
            sheet.paste(icon, box, icon)
            x += 1
            if x > icons_per_row:
                y += 1
                x = 0

        # More borrowed from DMIDE:
        # undocumented class
        meta = PngImagePlugin.PngInfo()

        # copy metadata into new object
        reserved = ('interlace', 'gamma', 'dpi', 'transparency', 'aspect')
        for k, v in sheet.info.items():
                if k in reserved: continue
                meta.add_text(k, v, 1)

        # Only need one - Rob
        meta.add_text(b'Description', manifest.encode('ascii'), 1)

        # and save
        sheet.save(to, 'PNG', pnginfo=meta)
        # with open(to+'.txt','w') as f:
        #    f.write(manifest)
        # logging.info('>>> {0} states saved to {1}'.format(len(frames), to))

    def getDMIH(self):
        o = '# DMI Header 1.0 - Generated by DMI.py'
        o += self.genDMIHLine('width', self.icon_width, -1)
        o += self.genDMIHLine('height', self.icon_height, -1)

        for s in sorted(self.states):
            o += self.states[s].genDMIH()

        return o

    def genDMIHLine(self, name, value, default):
        if value != default:
            if type(value) is list:
                value = ','.join(value)
            return '\n{0} = {1}'.format(name, value)
        return ''

    def extractTo(self, dest, suppress_post_process=False):
        flags = 0
        if(suppress_post_process):
            flags |= DMILoadFlags.NoPostProcessing
        # print('>>> Loading %s...' % self.filename)
        self.loadAll(flags)
        # print('>>> Extracting %s...' % self.filename)
        self.extractAllStates(dest, flags)

    def getFrame(self, state, direction, frame, movement=False):
        state = State.MakeKey(state,movement=movement)
        if state not in self.states:
            return None
        return self.states[state].getFrame(direction, frame)

    def setFrame(self, state, direction, frame, img, movement=False):
        state = State.MakeKey(state,movement=movement)
        if state not in self.states:
            self.states[state] = State(state)
        return self.states[state].setFrame(direction, frame, img)

    def getHeader(self):
        img = Image.open(self.filename)
        if(b'Description' not in img.info):
            raise Exception("DMI Description is not in the information headers!")
        return img.info[b'Description'].decode('ascii')

    def setHeader(self, newHeader, dest):
        img = Image.open(self.filename)

        # More borrowed from DMIDE:
        # undocumented class
        meta = PngImagePlugin.PngInfo()

        # copy metadata into new object
        reserved = ('interlace', 'gamma', 'dpi', 'transparency', 'aspect', 'icc_profile')
        for k, v in img.info.items():
                if k in reserved: continue
                # print(k, v)
                meta.add_text(k, v, 1)

        # Only need one - Rob
        meta.add_text(b'Description', newHeader.encode('ascii'), 1)

        # and save
        img.save(dest + '.tmp', 'PNG', pnginfo=meta)
        shutil.move(dest + '.tmp', dest)

    def loadMetadata(self, flags=0):
        self.load(flags | DMILoadFlags.NoImages)

    def loadAll(self, flags=0):
        self.load(flags)

    def load(self, flags):
        self.img = Image.open(self.filename)

        # This is a stupid hack to work around BYOND generating indexed PNGs with unspecified transparency.
        # Uncorrected, this will result in PIL(low) trying to read the colors as alpha.
        if self.img.mode == 'P':
            # If there's no transparency, set it to black.
            if 'transparency' not in self.img.info:
                logging.warn('({0}): Indexed PNG does not specify transparency! Setting black as transparency. self.img.info = {1}'.format(self.filename, repr(self.img.info)))
                self.img.info['transparency'] = 0

            # Always use RGBA, it causes less problems.
            self.img = self.img.convert('RGBA')

        self.size = self.img.size

        # Sanity
        if(b'Description' not in self.img.info):
            raise Exception("DMI Description is not in the information headers!")

        # Load pixels from image
        self.pixels = self.img.load()

        # Load DMI header
        desc = self.img.info[b'Description'].decode('ascii')
        """
version = 4.0
        width = 32
        height = 32
state = "fire"
        dirs = 4
        frames = 1
state = "fire2"
        dirs = 1
        frames = 1
state = "void"
        dirs = 4
        frames = 4
        delay = 2,2,2,2
state = "void2"
        dirs = 1
        frames = 4
        delay = 2,2,2,2
        """
        state = None
        x = 0
        y = 0
        self.statelist = desc
        ii = 0
        for line in desc.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                continue
            if '=' in line:
                (key, value) = line.split(' = ')
                key = key.strip()
                value = value.strip().replace('"', '')
                if key == 'version':
                    self.version = value
                elif key == 'width':
                    self.icon_width = int(value)
                    self.max_x = self.img.size[0] / self.icon_width
                elif key == 'height':
                    self.icon_height = int(value)
                    self.max_y = self.img.size[1] / self.icon_height
                    # print(('%s: {sz: %s,h: %d, w: %d, m_x: %d, m_y: %d}'%(self.filename,repr(img.size),self.icon_height,self.icon_width,self.max_x,self.max_y)))
                elif key == 'state':
                    if state != None:
                        # print(" + %s" % (state.ToString()))
                        if(self.icon_width == 0 or self.icon_height == 0):
                            if(len(self.states) > 0):
                                raise SystemError("Width and height for each cell are not available.")
                            else:
                                self.icon_width = self.img.size[0]
                                self.max_x = 1
                                self.icon_height = self.img.size[1]
                                self.max_y = 1
                        elif(self.max_x == -1 or self.max_y == -1):
                            self.max_x = self.img.size[0] / self.icon_width
                            self.max_y = self.img.size[1] / self.icon_width
                        for _ in range(state.numIcons()):
                            state.positions += [(x, y)]
                            if (flags & DMILoadFlags.NoImages) == 0:
                                state.icons += [self.loadIconAt(x, y)]
                            x += 1
                            # print('%s[%d:%d] x=%d, max_x=%d' % (self.filename,ii,i,x,self.max_x))
                            if(x >= self.max_x):
                                x = 0
                                y += 1
                        self.states[state.key()] = state
                        # if not suppress_post_process:
                        #    self.states[state.name].postProcess()
                        ii += 1
                    state = State(value)
                elif key == 'dirs':
                    state.dirs = int(value)
                elif key == 'frames':
                    state.frames = int(value)
                elif key == 'loop':
                    state.loop = int(value)
                elif key == 'rewind':
                    state.rewind = int(value)
                elif key == 'movement':
                    state.movement = int(value)
                elif key == 'delay':
                    state.delay = value.split(',')
                elif key == 'hotspot':
                    state.hotspot = value
                else:
                    logging.critical('Unknown key ' + key + ' (value=' + value + ')!')
                    sys.exit()

        self.states[state.name] = state
        for _ in range(state.numIcons()):
            self.states[state.name].icons += [self.loadIconAt(x, y)]
            x += 1
            if(x >= self.max_x):
                x = 0
                y += 1

    def extractAllStates(self, dest, flags=0):
        for _, state in viewitems(self.states):
            # state = State()
            for i in range(len(state.positions)):
                x, y = state.positions[i]
                self.extractIconAt(state, dest, x, y, i)

                if (flags & DMILoadFlags.NoPostProcessing) == 0:
                    self.states[state.name].postProcess()
                if dest is not None:
                    outfolder = os.path.join(dest, os.path.basename(self.filename))
                    nfn = self.filename.replace('.dmi', '.dmih')
                    valid_chars = "-_.()[] %s%s" % (string.ascii_letters, string.digits)
                    nfn = ''.join(c for c in nfn if c in valid_chars)
                    nfn = os.path.join(outfolder, nfn)
                    with open(nfn, 'w') as dmih:
                        dmih.write(self.getDMIH())

    def loadIconAt(self, sx, sy):
        if(self.icon_width == 0 or self.icon_height == 0):
            raise SystemError('Image is {}x{}, an invalid size.'.format(self.icon_height, self.icon_width))
        # print("  X (%d,%d)"%(sx*self.icon_width,sy*self.icon_height))
        icon = Image.new(self.img.mode, (self.icon_width, self.icon_height))

        newpix = icon.load()
        for y in range(self.icon_height):
            for x in range(self.icon_width):
                _x = x + (sx * self.icon_width)
                _y = y + (sy * self.icon_height)
                try:
                    pixel = self.pixels[_x, _y]
                    if pixel[3] == 0: continue
                    newpix[x, y] = pixel
                except IndexError:
                    print("!!! Received IndexError in %s <%d,%d> = <%d,%d> + (<%d,%d> * <%d,%d>), max=<%d,%d> halting." % (self.filename, _x, _y, x, y, sx, sy, self.icon_width, self.icon_height, self.max_x, self.max_y))
                    print('%s: {sz: %s,h: %d, w: %d, m_x: %d, m_y: %d}' % (self.filename, repr(self.img.size), self.icon_height, self.icon_width, self.max_x, self.max_y))
                    print('# of cells: %d' % len(self.states))
                    print('Image h/w: %s' % repr(self.size))
                    print('--STATES:--')
                    print(self.statelist)
                    sys.exit(1)
        return icon

    def extractIconAt(self, state, dest, sx, sy, i=0):
        icon = self.loadIconAt(sx, sy)
        outfolder = os.path.join(dest, os.path.basename(self.filename))
        if not os.path.isdir(outfolder):
            os.makedirs(outfolder)
        nfn = "{}[{}].png".format(state.name, i)
        valid_chars = "-_.()[] %s%s" % (string.ascii_letters, string.digits)
        nfn = ''.join(c for c in nfn if c in valid_chars)
        nfn = os.path.join(outfolder, nfn)
        if os.path.isfile(nfn):
            os.remove(nfn)
        try:
            icon.save(nfn)
        except SystemError as e:
            print("Received SystemError, halting: %s" % traceback.format_exc(e))
            print('{ih=%d,iw=%d,state=%s,dest=%s,sx=%d,sy=%d,i=%d}' % (self.icon_height, self.icon_width, state.ToString(), dest, sx, sy, i))
            sys.exit(1)
        return nfn
