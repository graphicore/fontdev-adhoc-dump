#! /usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
import os

LICENSE_DIRS = ['apache', 'ofl']

def familiesDirsGenerator(sourcesDir):
    for l in LICENSE_DIRS:
        for root, dirs, files in os.walk(os.path.join(sourcesDir, l)):
            dirs.sort()
            for d in sorted(dirs):
                yield os.path.join(l, d)
            del dirs[:]

def getExtension(path):
    basename = os.path.basename(path)
    extensionIndex = basename.rfind('.')
    if extensionIndex == -1:
        return False;
    return basename[extensionIndex:]

def isSourceDir(path):
    extension = getExtension(path)
    return False if not extension \
                    or extension not in ('.ufo', '.sfdir') \
                    else extension

def isSourceFile(path):
    extension = getExtension(path)
    return False if not extension \
                    or extension not in ('.vfb', '.sfd', '.glyphs') \
                    else extension

def familySourceFilesGenerator(sourcesDir, familyDir):
    for root, dirs, files in os.walk(os.path.join(sourcesDir, familyDir)):
        for isDir, collection, isSource in ((True, dirs, isSourceDir), (False, files, isSourceFile)):
            if isDir:
                sourceIndexes = []
                # descent alphabetically
                dirs.sort()
            relRoot = os.path.relpath(root, sourcesDir)
            for i, name in enumerate(collection):
                path = os.path.join(root, name)
                relPath = os.path.join(relRoot, name)
                extension = isSource(path)
                if extension:
                    yield relPath, relRoot, extension
                    if isDir:
                        sourceIndexes.append(i)
            if isDir:
                # remove dirs that are sources themselves
                # so we don't descent into them
                sourceIndexes.reverse()
                for i in sourceIndexes:
                    del collection[i]

def main():
    sourcesDir = sys.argv[1];
    joinLine = ','.join;
    labels = [
                'Family'
              , '# Source Files'
              , '# Source Dirs'
              , 'Source Types'
              , "Source Files"
            ]
    print(joinLine(labels))
    for familyDir in familiesDirsGenerator(sourcesDir):
        #print('Family Directory:', familyDir)
        sourceDirs = set()
        sourceFiles = []
        sourceFormats = set()
        for fileName, sourceDir, extension in familySourceFilesGenerator(sourcesDir, familyDir):
            sourceFiles.append(fileName)
            sourceDirs.add(sourceDir)
            sourceFormats.add(extension)
        line = [
            familyDir
          , '{0}'.format(len(sourceFiles))
            # number sourceDirs, should be one, more than one is ambigous
            # less than one means there are no sources
          , '{0}'.format(len(sourceDirs))
          , '"{0}"'.format(', '.join(sorted(list(sourceFormats)))) # sourceFormats
          , '"{0}"'.format('\n'.join(sourceFiles)) # source files
        ]
        print(joinLine(line))

if __name__ == '__main__':
    main();
