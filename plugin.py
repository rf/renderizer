 #!/usr/bin/env python

import os, subprocess, inspect, yaml, shutil, sys, glob

class ModCheck (object):
    """handles checking of modification times to see if we need to
       render the file or not"""

    def __init__ (self):
        self.modData = {}

    def check (self, sourceImage, computedFilename, outputConfig):
        """returns true if the source file has a greater modification date than
           the destination file, which would mean we need to re-render that
           destination file"""

        # if we haven't already stated this file, stat this file
        if sourceImage not in self.modData:
            self.modData[sourceImage] = os.stat(sourceImage).st_mtime

        srcModTime = self.modData[sourceImage]
        try:
            destModTime = os.stat(computedFilename).st_mtime
        except Exception:
            destModTime = 0
        if srcModTime > destModTime:
            return True
        else:
            return False

def launch (command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate("")
    code = proc.returncode
    if code != 0:
        print unicode(err, errors='ignore')
        raise Exception('Command failed, check output')

def illustrator (infile, outfile, outputConfig, pluginConfig):
    """Render an image with illustrator"""
    print 'Rendering', infile, 'to', outfile, 'at dpi', outputConfig['dpi'], 'with Illustrator.'

    if 'srcdpi' not in outputConfig:
        outputConfig['srcdpi'] = 72
    if 'scaling' not in outputConfig:
        dpi = float(outputConfig['dpi'])
        srcdpi = float(outputConfig['srcdpi'])
        outputConfig['scaling'] = (dpi / srcdpi) * 100.0

    command = [
        "osascript",
        pluginConfig['script_dir'] + "/illustrator-render",
        infile,
        outfile,
        str(outputConfig['scaling'])
    ]
    launch(command)

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

def checkProps (names, pluginConfig, outputConfig):
    """Checks to see if properties names[i] in pluginConfig is in the corresponding
       array / is the corresponding string in outputConfig, if name is even in
       outputConfig.  Returns True if everything matches, false otherwise"""
    for name in names:
        if name in pluginConfig and name in outputConfig:
            if type(outputConfig[name]) != list:
                outputConfig[name] = [outputConfig[name]]
            if pluginConfig[name] not in outputConfig[name]:
                return False
    return True

# list of ti build props to check
TiBuildProps = [
    'simtype',
    'devicefamily',
    'platform',
    'deploytype',
    'command'
]

def compile (pluginConfig):
    """invoked by Titanium's build scripts, runs the compilation process"""

    # hacky crap to get directory of currently running script file
    pluginConfig['script_dir'] = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    sys.path.insert(0, pluginConfig['script_dir'])

    # try to load images.yaml in a few different places
    locations = [
        'images.yaml',
        '../images.yaml',
        os.path.join(pluginConfig['script_dir'], 'images.yaml'),
        os.path.join(pluginConfig['project_dir'], 'images.yaml')
    ]

    for location in locations:
        try:
            test = yaml.load(open(location, 'r'))
            # Save the correct path to images.yaml
            yaml_path = location
            break
        except Exception:
            pass
    else:
        raise Exception('images.yaml file not found!')

    modCheck = ModCheck()

    backends = {}
    backends['illustrator'] = illustrator
    backends['inkscape'] = inkscape

    for name, desc in test.items():
        print 'Rendering group', name

        # Load up renderizer plugins for this backend
        plugins = []
        if 'plugins' in desc:
            for plugin in desc['plugins']:
                module = __import__(plugin)
                plugins.append(module.plugin(desc))

        # Explode image paths
        replacers = []
        for line in desc['images']:
            if '*' in line or '?' in line or '[' in line:
                replacers.append(line)
        for line in replacers:
            desc['images'].remove(line)
            desc['images'].extend(glob.glob(os.path.join(pluginConfig['project_dir'], 'images', line)))

        for outputConfig in desc['output']:

            # validation
            if 'backend' not in desc:
                raise Exception(
                    "You must specify a render backend for output number " +
                    str(desc['output'].index(outputConfig)) + " in image group "
                    + name
                )

            if desc['backend'] not in backends :
                raise Exception(
                    "Invalid backend " + outputConfig['backend'] +
                    "specified in image group " + name
                )

            groupMatchesTiProps = False

            # check properties on the group itself; if these don't match we set
            # groupMatchesTiProps to false.  This will cause the output files
            # for this group to be removed, thereby cleaning the output
            # directory of links which dont match the current build
            # configuration
            if checkProps(TiBuildProps, pluginConfig, desc):
                groupMatchesTiProps = True

            # ensure the outputConfig directory exists
            try:
                os.makedirs(os.path.join(
                    pluginConfig['project_dir'],
                    outputConfig['path']
                ))
            except os.error:
                pass

            # ensure build directory exists
            try:
                os.makedirs(os.path.join(
                    pluginConfig['project_dir'],
                    'build', 'images',
                    outputConfig['path']
                ))
            except os.error:
                pass

            # render each sourceImage
            for sourceImage in desc['images']:

                # handle `rename` and `append` properties
                if 'rename' in outputConfig:
                    basename = outputConfig['rename']
                else:
                    basename = os.path.splitext(os.path.basename(sourceImage))[0]
                    if 'append' in outputConfig:
                        basename += outputConfig['append']
                    if 'prepend' in outputConfig:
                        basename = outputConfig['prepend'] + basename
                    basename += '.png'

                # compute filename and temp filename
                computedFilename = os.path.join(
                    pluginConfig['project_dir'],
                    outputConfig['path'],
                    basename
                )

                tempFilename = os.path.join(
                    pluginConfig['project_dir'],
                    'build', 'images',
                    outputConfig['path'],
                    basename
                )

                # generate path of source image
                sourceImage = os.path.join(
                    pluginConfig['project_dir'],
                    "images",
                    sourceImage
                )

                # check to see if we need to re-render the image; if so, render
                if not modCheck.check(sourceImage, tempFilename, outputConfig):
                    print sourceImage, 'not modified, not rendering'
                else:
                    # if we've gotten to this point, we're ready to render
                    renderBackend = backends[desc['backend']]

                    # loop over renderizer plugins, call the beforeRender function
                    for plugin in plugins:
                        plugin.beforeRender(sourceImage, tempFilename, outputConfig, pluginConfig)

                    renderBackend(
                        sourceImage,
                        tempFilename,
                        outputConfig,
                        pluginConfig
                    )

                    for plugin in plugins:
                        ret = plugin.afterRender(sourceImage, tempFilename, outputConfig, pluginConfig, computedFilename)
                        if ret != None:
                            computedFilename = ret

                # remove the output file; it will be replaced with a symlink to
                # the rendered image, if applicable
                try:
                    os.remove(computedFilename)
                except:
                    pass

                # replace the output file with a symlink to the rendered image
                # in build/images/, if the property check suceeds
                if checkProps(TiBuildProps, pluginConfig, outputConfig) and groupMatchesTiProps:
                    os.symlink(tempFilename, computedFilename)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform')
    args = parser.parse_args()
    config = {'platform': args.platform}
    # assume we were run in the project directory if we weren't run from
    # titanium
    config['project_dir'] = os.getcwd()
    compile(config)

