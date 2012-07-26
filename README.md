# renderizer

Renderizer is a Titanium build plugin which can automate rendering of image
resources at different resolutions for different platforms.  It reads in a
YAML config file which specifies output directories, DPIs, and lists of images
to render.

Included is a simple applescript for automating Adobe Illustrator.  Renderizer
is capable of using either Inkscape or Illustrator as the render backend.

Renderizer will look for an `images.yaml` file in your project directory (ie,
next to the Resources and plugins folders).  It looks like this:

```YAML
icons:
   backend: illustrator

   output:
      - path: Resources/images/ipod
        dpi: 72

      - path: Resources/images/ipod
        dpi: 144
        append: '@2x'

      - path: Resources/images/ipad
        dpi: 82

   images:
      - icons/foo.ai
      - icons/bar.ai
      - icons/baz.ai
      - icons/foobar.ai

androidui:
   backend: illustrator
   platform: android

   output:
      - path: Resources/images/android
        dpi: 90

   images:
      - navbar.ai
      - background.ai

appicons:
   backend: inkscape
   platform: ios        # these images won't be put down on android

   output:
      - path: Resources/iphone
        dpi: 72

      - path: Resources/iphone
        dpi: 144
        append: '@2x'

      - path: Resources/iphone
        dpi: 91
        append: '-72'

      - path: Resources/iphone
        dpi: 36
        append: '-Small'

      - path: Resources/iphone
        dpi: 73
        append: '-Small@2x'

      - path: Resources/iphone
        dpi: 63
        append: '-Small-50'

      - path: Resources/iphone
        dpi: 647
        rename: iTunesArtwork

   images:
      - Icon.svg
```

`icons` and `androidui` are arbitrary group names.  Any top level property in
the YAML file is assumed to be a group name.  Images are rendered to png files
and are placed in the path specified.

The `append` property is, as one would
expect, appended to the end of the filename.  The `rename` property will force
_each_ image to be renamed to the name specified, so it's really only useful
if you're rendering a single image.

Images are assumed to be in an `images` directory in your project directory.

Since Illustrator accepts a 'scaling' property for rendering and not a DPI,
it is assumed your files were created with a DPI of 72.  If they weren't,
use the 'srcdpi' to specify the source dpi.

If you create `images/Icon.svg` at 57x57 *points* in inkscape, the above group
called `appicons`
will render all of the icons needed by Apple for app submission.

For more information on DPIs see the
[wiki](https://github.com/russfrank/renderizer/wiki).

To install the plugin, make a `plugins` directory in your project directory.
CD into it, then:

```sh
git clone git@github.com:russfrank/renderizer.git
```

Then, add to your `<plugins>` section in your `tiapp.xml`:

```xml
<plugins>
   <plugin version="0.0">renderizer</plugin>
</plugins>
```

Now, your images will be rendered whenever you build your project.  Images are
only re-rendered when their modification date has changed.  So, touch an image
source if you need it re-rendered.

Images are only dropped down if the Titanium properties specified in the group / output rule
match.  So, if you specify that a group is ios only, it will only be put down
for ios builds.  Images are rendered into build/images and then symlinked into the
destination directory.

Renderizer requires PyYAML, so if you don't already have this installed you'll
have to install it:

```
easy_install PyYaml
```

You can also run the rendering process manually by running the plugin.py from your
project directory:

```
python plugins/renderizer/plugin.py
```

# Plugin plugins & 9patch

I recently added support for plugins within the plugin.  These have hooks for
before each render and after each render.  This way, you can make some
custom modifications to images before or after rendering.

If you'd like to write your own plugins I've included an `example_plugin.py`
file which should get you started.  They're just python classes with a couple
of methods.

Included is a 9patch plugin (9patch.py).  To use it, you must be using the
**inkscape** backend.  Make an svg with a layer called **9patch**.  Then, draw
the 9patch lines on the sides of the image with large black rectangles on this
**9patch** layer. Should look something like this

![inkscape screenshot](https://github.com/russfrank/renderizer/inkscapeshot.png)

Then, with an `images.yaml` like this

```yaml
android_default_9patch_portrait:
  backend: inkscape
  plugins: [9patch]

  output:

    - path: platform/android/res/drawable-normal-port-mdpi/
      dpi: 40
      rename: 'background.9.png'

    - path: platform/android/res/drawable-normal-port-hdpi/
      dpi: 72
      rename: 'background.9.png'

    - path: platform/android/res/drawable-normal-port-xhdpi/
      dpi: 120
      rename: 'background.9.png'

    - path: platform/android/res/drawable-xlarge-port-mdpi/
      dpi: 120
      rename: 'background.9.png'

    - path: platform/android/res/drawable-large-port-mdpi/
      dpi: 70
      rename: 'background.9.png'

  images:
    - android/Default-portrait.9.svg
```

you'll get 9patched images for each dpi specified.

This plugin actually renders just the 9patch lines to a temporary png file.
Then, it examines the border and draws black areas of the 9patch temporary png
to your rendered png.  The result is that you can render for multiple
resolutions and have 9patch images for every resolution.

# License

MIT.
