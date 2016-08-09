'''
Map Rendering module

This splits out a lot of things from the map management module, to keep image code
separate from map parsing code

Also hopefully I won't put everything in the __init__.py file
'''
from .images import trim, tint_image
from .render import RenderToMapTile, MapRenderFlags
