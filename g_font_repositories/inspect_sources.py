#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)
import os
import json
import re

LICENSE_DIRS = ['apache', 'ofl']
META_JSON = 'METADATA.json'
DESCRIPTION_FILE = 'DESCRIPTION.en_us.html'

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

class NoMetaDataError(Exception):
    pass

def readMetaData(sourcesDir, familyDir):
    path = os.path.join(sourcesDir, familyDir, META_JSON)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except IOError as e:
        raise NoMetaDataError('No meta data with error: {0}'.format(e))

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


_regex_copyright = re.compile(
    r'copyright (?:\(c\)|©) ?([0-9]+[0-9, ]+[0-9]+), ?([a-z]+ [a-z]+)'
  , flags=re.IGNORECASE
)
_regex_rfn = re.compile(
    r'.*(Reserved Font Name.+)'
)
def parseCopyrightNameYear(copyright):
    copyrightName = copyrightYear = None
    match = _regex_copyright.match(copyright)
    if match:
        copyrightYear, copyrightName = match.groups()

    RFN = _regex_rfn.match(copyright)
    if RFN:
        # also add a proper separator to it, some Copyright string omit the comma.
        print ('RFN', *RFN.groups())
        RFN = ', with {0}'.format(RFN.group(1))
        if RFN.endswith('.'):
            RFN = RFN[:-1]
    return copyrightName , copyrightYear, RFN

def getDescription(sourcesDir, familyDir):
    path = os.path.join(sourcesDir, familyDir, DESCRIPTION_FILE)
    try:
        with open(path, 'r') as f:
            data = f.read()
    except e:
        raise e
        return None
    return data

_regex_mail_raw = r'[\w\.\-\_]+@[\w\-\_\.]+\.+[A-Za-z]{2,4}';
_regex_mail = re.compile(_regex_mail_raw)
# This could be better but seems to be suffcient for our data
_regex_url_raw = r'(?:http[s]?://|(?:[a-zA-Z][a-zA-Z0-9]+)[\.])(?:[a-zA-Z0-9/\-_\.~]{2,})'
# Match emails and later remove all matches that contain an @
# this is much easier than trying not to match emails
# especially because we allow very lax url schemes here, like: "mydomain.com"
_regex_url = re.compile('(?:{0})|(?:{1})'.format(_regex_mail_raw, _regex_url_raw))
def getMetaData(sourcesDir, familyDir):
    """ Try to extract useful data from METADATA.json """
    meta = readMetaData(sourcesDir, familyDir)
    copyrights = set()
    urls = set()
    emails = set()

    fonts = meta.get('fonts', [])
    for font in fonts:
        copyright = font.get('copyright', '')
        copyrights.add(copyright)
        urls.update(url for url in re.findall(_regex_url, copyright) if '@' not in url)
        emails.update(re.findall(_regex_mail, copyright))

    urls = urls - not_urls

    if copyrights:
        # is it sufficient to take just the first copyright?
        # our target consumes only one!
        copyright = list(copyrights)[0]
        copyrightName, copyrightYear, RFN = parseCopyrightNameYear(copyright)
        emails_list = sorted(emails, lambda mail: copyright.index(mail))
        copyrightEmail = emails_list[0] if len(emails_list) else ''

    description = getDescription(sourcesDir, familyDir)

    return {
        'name': meta.get('name', None)
      , 'number_fonts': len(fonts)
      , 'designer': meta.get('designer', None)
      , 'emails': emails
      , 'urls': urls
      , 'copyrights': copyrights
      , 'dateAdded': meta.get('dateAdded', None)

      , 'copyrightName': copyrightName
      , 'copyrightYear': copyrightYear
      , 'copyrightEmail': emails_list[0] if len(emails_list) else ''
      , 'RFN': RFN
      , 'description': description
    }


def getMetaDataLine(sourcesDir, familyDir):
    try:
        meta = getMetaData
    except NoMetaDataError:
        return ['', '', '', '', '', '', '',]
    metaData = getMetaData(sourcesDir, familyDir)
    return [
        metaData['name'] or ''
      , len(fonts)
      , metaData['designer'] or ''
      , iterToCell(emails)
      , iterToCell(urls)
      , iterToCell(copyrights)
      , metaData['dateAdded'] or ''
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

    line += getMetaDataLine(sourcesDir, familyDir)
    return line



def main(args):
    sourcesDir = args[0];
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
    main(sys.argv[1:]);
