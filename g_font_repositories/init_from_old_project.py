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
import shutil
import logging
import readline
import argparse
from string import Template
from functools import wraps

from inspect_sources import getMetaData, NoMetaDataError

DESCRIPTION = 'Create a new project directory for an old Google-Font-Directory font.'
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
TEMPLATES = {
    'old2repo': 'old_project_new_repo'
}
EMPTY_DIR_MARKER_FILE = 'empty'
INACTIVE_GIT_IGNORE = '_gitignore'
OLD_DATA_TARGET = 'version-1.000'

LOGGER = 'GFont'

def removeEmptyDirectoryMarkerFiles(log, targetDir):
    log.info('Remove "{0}" empty dir marker files.'.format(EMPTY_DIR_MARKER_FILE))
    for root, dirs, files in os.walk(targetDir):
        for fileName in files:
            if fileName == EMPTY_DIR_MARKER_FILE:
                os.unlink(os.path.join(root, fileName))

def activateGitignoreFiles(log, targetDir):
    log.info('Activate .gitignore files.')
    for root, dirs, files in os.walk(targetDir):
        for fileName in files:
            if fileName == INACTIVE_GIT_IGNORE:
                os.rename(os.path.join(root, fileName), os.path.join(root, '.gitignore'))

def copyTemplate(log, templateKey, targetDir):
    try:
        templateDir = os.path.join(TEMPLATE_DIR, TEMPLATES[templateKey])
        log.info('Copy template {0}'.format(templateDir))
        shutil.copytree(templateDir, targetDir)
    except Exception as e:
        print('The target directory "{0}" can\'t be created with ' \
                    + 'message: {1}'.format(targetDir, e), file=sys.stderr)
        sys.exit(1)

META_DATA_META = (
        ('projectName', 'name', True)
      , ('designerName', 'designer', True)
      , ('authorName', 'copyrightName', True)
      , ('authorEmail', 'copyrightEmail', True)
      , ('copyrightName', 'copyrightName', True)
      , ('copyrightEmail', 'copyrightEmail', True)
      , ('copyrightYear', 'copyrightYear', True)
      , ('RFN', 'RFN', False)
      , ('description', 'description', True)
)

def aquireMetaData(log, sourcesDir, familyDir):
    """
        return a dictionary that may contain the keys in META_DATA_META
    """
    log.info('Aquire meta data')
    try:
        metaData = getMetaData(sourcesDir, familyDir)
    except NoMetaDataError as e:
        log.warn('Can\'t read meta data.', exc_info=True)
        metaData = {}

    result = {}
    # straight copy, map names
    for target_key, source_key, required in META_DATA_META:
        if source_key in metaData and metaData[source_key]:
            result[target_key] = metaData[source_key];
        elif not required:
            result[target_key] = ''
    return result

def validateFilterMetaData(metaData):
    """ We DON'T expect malicious input here.
        This is only checking if all keys exist and if they are not empty.
        I.e. NOT if an email is an email etc.
    """
    result = metaData.copy()
    missing = []
    keys = []
    for k, _, required in META_DATA_META:
        keys.append(k)
        value = result.get(k, '')
        value = value.strip()
        if not value and required:
            if k in result:
                del result[k]
            missing.append(k)
        else:
            # It's stripped and we may apply other transformations in the
            # future.
            result[k] = value

    for k in result.keys():
        if k not in keys:
            del result[k]

    if missing:
        return False, 'Missing data: {0}'.format(', '.join(missing)), result
    return True, None, result

def user_input_wrapper(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        while True:
            try:
                # on EOFError we'll repeat this again
                # unless the user finishes the input or exits the program
                return f(*args, **kwds)
            except EOFError:
                leave = None
                try:
                    leave = raw_input('\nDo you really want to exit ([y]/n)? ').lower().strip()
                except:
                    if not leave or leave in ('y', 'yes'):
                        print ('Bye!')
                        sys.exit(0)
    return wrapper;

@user_input_wrapper
def forceOrQuitOrRepeat(message):
    print('The metadata is invalid with the message:')
    print(message)
    return raw_input('(F)orce, (Q)uit program, ([any key]) to check again: ')

@user_input_wrapper
def userCheckData(metaData):
    """ Let the user check and manipulate the metaData dict.

    The passed instance of metaData is changed in place.
    """
    keys = [(k, '*' if required else ' ') for k, _, required in META_DATA_META]
    keys.sort(key=lambda x: (x[0].lower(), 0 if x[1] == '*' else 1))
    formatKey = '#{0: 3d} {1}{2}: '.format
    print('Please check the Metadata (*=required).')
    showData = True
    while True:
        if showData:
            print('### DATA ###')
            for i, (k, req) in enumerate(keys):
                print('{0}{1}'.format(formatKey(i,k,req), metaData.get(k, '')))
            showData = False;
        print('To change a key enter its index number.')
        answer = raw_input('Does this look good ([y]es/#index)? ')
        if answer.strip().lower() in ('', 'y', 'yes'):
            # this ends the interaction
            return metaData;
        i = None
        try:
            i = int(answer)
        except ValueError:
            # ask again
            continue
        if i is not None and i >= 0 and i < len(keys):
            k, req = keys[i]
            print('Please enter a new value or nothing to keep the old value.')
            metaData[k] = raw_input(formatKey(i, k,req)).strip() or metaData.get(k, '')
            # show updated data again
            showData = True
            continue

def askUser(log, metaData, force):
    result = metaData.copy()
    while True:
        result = userCheckData(result)
        success, message, _ = validateFilterMetaData(metaData)
        if success:
            break
        if not force:
            answer = forceOrQuitOrRepeat(message).lower()
            if answer in ('q', 'quit'):
                print('Bye!')
                sys.exit(0)
            elif answer in ('f', 'force'):
                force = True
        if force:
            break;
        # default: userCheckData again
    return result, force

def checkMetaData(log, metaData, force, allYes):
    if not allYes:
        metaData, force = askUser(log, metaData, force)
    success, message, metaData = validateFilterMetaData(metaData)
    if not success:
        log.warn('Meta-data has problems: {0}.'.format(message))
    if not success:
        if not force:
            log.error('Meta-data is invalid, use --force to allow this to pass.')
            sys.exit(1)
        log.warn('Forcing invalid metadata');
    return metaData;

METADATA_RECEIVERS = (
    'AUTHOR.txt'
  , 'OFL.txt'
  , 'README.md'
  , 'documentation/DESCRIPTION.en_us.html'
)

def applyMetaData(log, metaData, targetDir, force=False):
    log.info('Applying meta-data ...')
    for name in METADATA_RECEIVERS:
        path = os.path.join(targetDir, name);
        log.info(' ... writing {0}'.format(name))
        with open(path, 'r+b') as f:
            template = Template(f.read())
            f.seek(0)
            f.truncate()
            data = template.safe_substitute(metaData)
            f.write(data)

def copyOldFiles(log, sourcesDir, familyDir, targetDir):
    log.info('Copy old files from {1} in {0}'.format(sourcesDir, familyDir))
    source = os.path.join(sourcesDir, familyDir)
    target = os.path.join(targetDir, 'old', OLD_DATA_TARGET)
    try:
        shutil.copytree(source, target)
    except Exception as e:
        # don't fail because of this?
        log.warning('Can\'t copy old files from {0}.'.format(source), exc_info=True)

def init_repository(log, sourcesDir, familyDir, targetDir, force, allYes):
    metaData = aquireMetaData(log, sourcesDir, familyDir)
    # this fails if the directory already exists and exits the program
    metaData = checkMetaData(log, metaData, force, allYes)
    copyTemplate(log, 'old2repo', targetDir)
    removeEmptyDirectoryMarkerFiles(log, targetDir)
    activateGitignoreFiles(log, targetDir)
    copyOldFiles(log, sourcesDir, familyDir, targetDir)
    applyMetaData(log, metaData, targetDir)

def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    # optional
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Silence all logging.')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Execute the command, even if the metadata '
                                                'appears to be invalid.')
    parser.add_argument('-y', '--yes', action='store_true',
                        help='None interactive mode. Answer all questions with yes.')
    # positional
    parser.add_argument('googlefontdir',
                        help='Path to the old google font directory.')
    parser.add_argument('familydir',
                        help='The familiy directory inside of googlefontdir.')
    parser.add_argument('targetdir',
                        help='Path to the new directory to be created.')

    args = parser.parse_args()

    if args.quiet:
        # Not really quiet, but we don't actually use critical right now.
        log_level = logging.CRITICAL
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.ERROR

    logging.basicConfig(level=log_level)
    log = logging.getLogger(LOGGER)

    init_repository(
                    log
                  , args.googlefontdir
                  , args.familydir
                  , args.targetdir
                  , args.force
                  , args.yes)

if __name__ == '__main__':
    main();
