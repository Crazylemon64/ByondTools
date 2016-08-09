from PIL import Image, ImageChops

# From StackOverflow
def trim(im):
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)

# Bytes
def tint_image(image, tint_color):
    return ImageChops.multiply(image, Image.new('RGBA', image.size, tint_color))
