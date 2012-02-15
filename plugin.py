 #!/usr/bin/env python

import os, subprocess, cPickle
from yaml import load

class ModCheck (object):
    """handles checking of modification times to see if we need to
       render the file or not"""

    def __init__ (self, path):
        try:
            self.modData = cPickle.load(open(os.path.join(
                path, "plugins", "renderizer", "moddata"), "rb"))
        except Exception:
            print "Couldn't load moddata"
            self.modData = {}
        self.path = path

    def check (self, path, out, dpi, backend):
        """returns true if the file has been modified since last run,
           false otherwise"""
        key = path, out, dpi, backend
        ret = True
        mtime = os.stat(path).st_mtime
        if key in self.modData:
            if mtime <= self.modData[key]:
                ret = False
        self.modData[key] = mtime
        return ret

    def save (self):
        cPickle.dump(self.modData, open(os.path.join(
            self.path, "plugins", "renderizer", "moddata"), 'wb'))

def launch (command):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate("")
    code = proc.returncode
    if code != 0:
        print unicode(err, errors='ignore')
        raise Exception('Command failed, check output')

def illustrator (infile, outfile, output, config):
    """Render an image with illustrator"""
    print 'Rendering', infile, 'to', outfile, 'at dpi', output['dpi'], 'with Illustrator.'
    if 'srcdpi' not in output:
        output['srcdpi'] = 72
    if 'scaling' not in output:
        output['scaling'] = (float(output['dpi']) / float(output['srcdpi'])) * 100.0
    command = [
        "osascript",
        config['project_dir'] + "/plugins/renderizer/illustrator-render",
        infile,
        outfile,
        str(output['scaling'])
    ]
    launch(command)

def inkscape (infile, outfile, output, config):
    """Render an image with inkscape"""
    print 'Rendering', infile, 'to', outfile, 'at dpi', output['dpi'], 'with Inkscape.'
    command = [
        "inkscape",
        "-d",
        str(output['dpi']),
        "-e",
        outfile,
        infile
    ]
    launch(command)

def compile (config):
    """invoked by Titanium's build scripts, runs the compilation process"""
    test = load(file('images.yaml', 'r'))
    config['project_dir'] = config['project_dir'].encode('ascii', 'ignore')
    modCheck = ModCheck(config['project_dir'])

    backends = {}
    backends['illustrator'] = illustrator
    backends['inkscape'] = inkscape

    for name, desc in test.items():
        print 'Rendering group', name
        if desc['backend'] not in backends:
            raise Exception("invalid backend")

        for output in desc['output']:
            # ensure the output directory exists
            try:
                os.makedirs(os.path.join(
                    config['project_dir'],
                    output['path']
                ))
            except os.error:
                pass

            # render each image
            for image in desc['images']:
                if 'rename' in output:
                    filename = os.path.join(
                        config['project_dir'],
                        output['path'],
                        output['rename']
                    )
                else:
                    filename = os.path.join(
                        config['project_dir'],
                        output['path'],
                        os.path.splitext(os.path.basename(image))[0]
                    )
                    if 'append' in output:
                        filename += output['append']
                    filename += ".png"

                image = os.path.join(config['project_dir'], "images", image)
                if modCheck.check(image, filename, output['dpi'], desc['backend']):
                    backends[desc['backend']](image, filename, output, config)
                else:
                    print image, 'not modified, not rendering'

    modCheck.save()

if __name__ == '__main__':
    config = {}
    config['project_dir'] = os.getcwd()
    compile(config)
