from xml.etree.ElementTree import ElementTree
import shutil, os, subprocess
from PIL import Image

def setVisibility (svgPath, vis, inputName=None):
  """Hides the specified layer in some svg file, or, if layer=None, hides all
  layers"""
  document = ElementTree()
  document.parse(svgPath)
  root = document.getroot()
  for elem in root.iter("{http://www.w3.org/2000/svg}g"):
    layerName = elem.get("{http://www.inkscape.org/namespaces/inkscape}label")
    layerId = elem.get("id")
    if layerName == inputName or inputName == None:
      if vis:
        elem.set('style', '')
        elem.set('display', '')
      else:
        elem.set('style', 'display:none')
        elem.set('display', 'none')
  document.write(svgPath)

def launch (command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate("")
    code = proc.returncode
    if code != 0:
        print unicode(err, errors='ignore')
        raise Exception('Command failed, check output')

def inkscape (infile, outfile, outputConfig, pluginConfig):
    """Render an image with inkscape"""
    print 'Rendering', infile, 'to', outfile, 'at dpi', outputConfig['dpi'], 'with Inkscape.'
    command = [
        "inkscape",
        "-d",
        str(outputConfig['dpi']),
        "-e",
        outfile,
        infile
    ]
    launch(command)

class plugin:
  
  def __init__ (self, desc):
    """Initialized for each 'group' that is being rendered.  Handed the 'desc'
    object, which is the full output description (ie, this group's decoded
    yaml data)."""
    pass

  def beforeRender (self, sourceImage, tempFilename, outputConfig, pluginConfig):
    """Called before rendering every image"""
    # Copy sourceImage to temporary svg location
    shutil.copyfile(sourceImage, sourceImage + '.tmp9.svg')

    # Hide all layers in temp svg file
    setVisibility(sourceImage + '.tmp9.svg', False)

    # Show 9patch layer in temp svg 
    setVisibility(sourceImage + '.tmp9.svg', True, '9patch')

    # Render svg file to temp png
    inkscape(
      sourceImage + '.tmp9.svg', 
      tempFilename + '.tmp9.png', 
      outputConfig, 
      pluginConfig
    )

    # delete temp svg file
    os.remove(sourceImage + '.tmp9.svg')

    # hide 9patch lines in source png
    setVisibility(sourceImage, False, '9patch')

  def afterRender (
    self, 
    sourceImage, 
    tempFilename, 
    outputConfig, 
    pluginConfig, 
    computedFilename
  ):

    """Called after rendering every image.  Can return a new computedFilename"""

    # Open rendered png
    rendered = Image.open(tempFilename)

    # Open temporary png
    ninepatchpng = Image.open(tempFilename + '.tmp9.png')
    ninepatchPixels = ninepatchpng.load()

    # Make a new png 2px wider and 2px longer
    newrendered = Image.new(
      "RGBA", 
      (rendered.size[0] + 2, rendered.size[1] + 2), 
      (255, 255, 255, 0)
    )
    newrenderedPixels = newrendered.load()

    # Draw ninepatch lines onto new png
    for x in range(0, ninepatchpng.size[0]):
      # If this pixel in the ninepatch reference image is opaque, we need to fill
      # it in in our new image
      if ninepatchPixels[x, 0][3] == 255: 
        newrenderedPixels[x + 1, 0] = (0, 0, 0, 255)

      # Do the other side (ie, the ninepatch data that implies padding)
      if ninepatchPixels[x, ninepatchpng.size[1] - 1][3] == 255: 
        newrenderedPixels[x + 1, newrendered.size[1] - 1] = (0, 0, 0, 255)

    for y in range(0, ninepatchpng.size[1]):
      # If this pixel in the ninepatch reference image is opaque, we need to fill
      # it in in our new image
      if ninepatchPixels[0, y] == (0, 0, 0, 255):
        newrenderedPixels[0, y + 1] = (0, 0, 0, 255)

      # Do the other side (ie, the ninepatch data that implies padding)
      if ninepatchPixels[ninepatchpng.size[0] - 1, y][3] == 255: 
        newrenderedPixels[newrendered.size[0] - 1, y + 1] = (0, 0, 0, 255)

    # Paste rendered png onto new png
    newrendered.paste(rendered, (1,1))

    # Write new png to tempFilename
    newrendered.save(tempFilename)

    # show 9patch lines in source png
    setVisibility(sourceImage, True, '9patch')

