 #!/usr/bin/env python

import os, subprocess, inspect, yaml

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

def compile (pluginConfig):
    """invoked by Titanium's build scripts, runs the compilation process"""

    # hacky crap to get directory of currently running script file
    pluginConfig['script_dir'] = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    print os.path.realpath(__file__)
    print pluginConfig

    # try to load images.yaml in a few different places
    try:
        test = yaml.load(file('images.yaml', 'r'))
    except Exception:
        pass

    try:
        test = yaml.load(file('../images.yaml', 'r'))
    except Exception:
        pass

    try:
        test = yaml.load(file(os.path.join(pluginConfig['script_dir'] + 'images.yaml', 'r')))
    except Exception:
        pass

    if test == None:
        raise Exception('images.yaml file not found!')

    modCheck = ModCheck()

    backends = {}
    backends['illustrator'] = illustrator
    backends['inkscape'] = inkscape

    for name, desc in test.items():
        print 'Rendering group', name

        for outputConfig in desc['output']:

            # validation
            if 'backend' not in outputConfig:
                raise Exception(
                    "You must specify a render backend for output number " +
                    str(desc['output'].index(outputConfig)) + " in image group "
                    + name
                )

            if outputConfig['backend'] not in backends :
                raise Exception(
                    "Invalid backend " + outputConfig['backend'] +
                    "specified in image group " + name
                )

            # ensure the outputConfig directory exists
            try:
                os.makedirs(os.path.join(
                    pluginConfig['project_dir'],
                    outputConfig['path']
                ))
            except os.error:
                pass

            # render each sourceImage
            for sourceImage in desc['images']:

                # handle rename property
                if 'rename' in outputConfig:
                    computedFilename = os.path.join(
                        pluginConfig['project_dir'],
                        outputConfig['path'],
                        outputConfig['rename']
                    )
                    tempFilename = os.path.join(
                        pluginConfig['project_dir'],
                        "build/images",
                        outputConfig['path'],
                        outputConfig['rename']
                    )

                # compute filename
                else:
                    computedFilename = os.path.join(
                        pluginConfig['project_dir'],
                        outputConfig['path'],
                        os.path.splitext(os.path.basename(sourceImage))[0]
                    )

                    tempFilename = os.path.join(
                        pluginConfig['project_dir'],
                        "build/images",
                        outputConfig['path'],
                        os.path.splitext(os.path.basename(sourceImage))[0]
                    )

                    # handle append property
                    if 'append' in outputConfig:
                        computedFilename += outputConfig['append']
                        tempFilename += outputConfig['append']
                    computedFilename += ".png"
                    tempFilename += ".png"

                # generate path of source image
                sourceImage = os.path.join(
                    pluginConfig['project_dir'],
                    "images",
                    sourceImage
                )

                # check to see if we need to re-render the image; if so, render
                if not modCheck.check(sourceImage, computedFilename, outputConfig):
                    print sourceImage, 'not modified, not rendering'
                    continue

                # check these other properties provided to us in outputConfig
                # when called by titanium build system
                properties = [
                    'simtype',
                    'devicefamily',
                    'platform',
                    'deploytype',
                    'command'
                ]
                if not checkProps(properties, pluginConfig, outputConfig):
                    continue

                # if we've gotten to this point, we're ready to render
                renderBackend = backends[outputConfig['backend']]
                renderBackend(
                    sourceImage,
                    computedFilename,
                    outputConfig,
                    pluginConfig
                )

if __name__ == '__main__':
    config = {}
    # assume we were run in the project directory if we weren't run from
    # titanium
    config['project_dir'] = os.getcwd()
    compile(config)

