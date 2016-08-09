

# @formatter:off
COLORS = {
    'aqua':    '#00FFFF',
    'black':   '#000000',
    'blue':    '#0000FF',
    'brown':   '#A52A2A',
    'cyan':    '#00FFFF',
    'fuchsia': '#FF00FF',
    'gold':    '#FFD700',
    'gray':    '#808080',
    'green':   '#008000',
    'grey':    '#808080',
    'lime':    '#00FF00',
    'magenta': '#FF00FF',
    'maroon':  '#800000',
    'navy':    '#000080',
    'olive':   '#808000',
    'purple':  '#800080',
    'red':     '#FF0000',
    'silver':  '#C0C0C0',
    'teal':    '#008080',
    'white':   '#FFFFFF',
    'yellow':  '#FFFF00'
}
# @formatter:on

_COLOR_LOOKUP = {}

def BYOND2RGBA(colorstring, alpha=255):
    colorstring = colorstring.strip()
    if colorstring == None or colorstring == '':
        return (255, 255, 255, 255) # Edge cases of BYOND2RGBA being passed an incorrect value
    if colorstring[0] == '#':
        colorstring = colorstring[1:]
        r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
        r, g, b = [int(n, 16) for n in (r, g, b)]
        return (r, g, b, alpha)
    elif colorstring.startswith('rgb('):
        r, g, b = [int(n.strip()) for n in colorstring[4:-1].split(',')]
        return (r, g, b, alpha)
    else:
        return _COLOR_LOOKUP[colorstring]

for name, color in COLORS.items():
    _COLOR_LOOKUP[name] = BYOND2RGBA(color)
