#! /usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import json
import re

import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)


LICENSE_DIRS = ['apache', 'ofl']
META_JSON = 'METADATA.json'

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

def readMetaData(sourcesDir, familyDir):
    path = os.path.join(sourcesDir, familyDir, META_JSON)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except IOError:
        return None

def iterToCell(data, separator='\n'):
    return separator.join(sorted(list(data)))


# Some common mismatches that otherwise qualify as "URL" but are known
# not to be URLS of designers. I.e. this removes the noise.
not_urls = set([
    'http://www.apache.org/licenses/LICENSE-2.0.html'
  , 'http://scripts.sil.org/OFL'
  , 'OFL.txt'
  , 'v1.1.'
])

def getMetaData(sourcesDir, familyDir):
    meta = readMetaData(sourcesDir, familyDir)
    if meta is None:
        return ['', '', '', '']
    copyrights = set()
    urls = set()
    emails = set()

    regex_mail_raw = r'[\w\.\-\_]+@[\w\-\_\.]+\.+[A-Za-z]{2,4}';
    regex_mail = re.compile(regex_mail_raw)
    # This could be better but seems to be suffcient for our data
    regex_url_raw = r'(?:http[s]?://|(?:[a-zA-Z][a-zA-Z0-9]+)[\.])(?:[a-zA-Z0-9/\-_\.~]{2,})'
    # Match emails and later remove all matches that contain an @
    # this is much easier than trying not to match emails
    # especially because we allow very lax url schemes here, like: "mydomain.com"
    regex_url = re.compile('(?:{0})|(?:{1})'.format(regex_mail_raw, regex_url_raw))

    fonts = meta.get('fonts', [])
    for font in fonts:
        copyright = font.get('copyright', '')
        copyrights.add(copyright)
        urls.update(url for url in re.findall(regex_url, copyright) if '@' not in url)
        emails.update(re.findall(regex_mail, copyright))

    urls = urls - not_urls

    return [
        meta.get('name', '')
      , len(fonts)
      , meta.get('designer', '')
      , iterToCell(emails)
      , iterToCell(urls)
      , iterToCell(copyrights)
      , meta.get('dateAdded', '')
    ]

def makeFamilyLine(sourcesDir, familyDir):
    sourceDirs = set()
    sourceFiles = []
    sourceFormats = set()
    for fileName, sourceDir, extension in familySourceFilesGenerator(sourcesDir, familyDir):
        sourceFiles.append(fileName)
        sourceDirs.add(sourceDir)
        sourceFormats.add(extension)
    line = [
        familyDir
      , len(sourceFiles)
        # number sourceDirs, should be one, more than one is ambigous
        # less than one means there are no sources
      , len(sourceDirs)
      , iterToCell(sourceFormats, separator=', ') # sourceFormats
      , iterToCell(sourceFiles) # source files
    ]

    line += getMetaData(sourcesDir, familyDir)
    return line



def main():
    sourcesDir = sys.argv[1];
    formatCell = lambda s: '"{0}"'.format('{0}'.format(s).replace('"', '""'));
    joinCells = ','.join;
    labels = [
                'Family Dir'
              , '# Source Files'
              , '# Source Dirs'
              , 'Source Types'
              , 'Source Files'
              # from getMetaData
              , 'Family Name'
              , '# Fonts'
              , 'Designer'
              , 'Emails'
              , 'URLs'
              , 'Copyrights'
              , 'Date Added'
        ]
    print(joinCells(labels))
    for familyDir in familiesDirsGenerator(sourcesDir):
        line = makeFamilyLine(sourcesDir, familyDir)
        print(joinCells(map(formatCell, line)))

if __name__ == '__main__':
    main();
