#!env/bin/python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: ...

"""
The one and only C3S repertoire processing utility
"""


#--- Imports ---


import sys
import os
# import shutil
import subprocess
import ConfigParser
import json
import datetime
import re
import hashlib
import click
import requests
from proteus import config, Model


#--- Initialization ---


# read config from .ini
CONFIGURATION = ConfigParser.ConfigParser()
CONFIGURATION.read("config.ini")
PROTEUS_CONFIG = dict(CONFIGURATION.items('proteus'))
FILEHANDLING_CONFIG = dict(CONFIGURATION.items('filehandling'))

#  get access to database
config.set_xmlrpc(
    "https://"   + PROTEUS_CONFIG['user'] + ":" + PROTEUS_CONFIG['password'] + "@"
    + PROTEUS_CONFIG['host'] + ":" + PROTEUS_CONFIG['port'] + "/" + PROTEUS_CONFIG['database']
)


#--- Processing stage functions for single audiofiles ---


def checksum_audiofile(srcdir, destdir, filename):
    """
    Hashing a single file.
    """

    filepath = os.path.join(srcdir, filename)

    bufsize = 65536

    sha256 = hashlib.sha256()

    with open(filepath, 'rb') as filetohash:
        while True:
            data = filetohash.read(bufsize)
            if not data:
                break
            sha256.update(data)

    print "SHA256 of file {0}: {1}".format(filename, sha256.hexdigest())

    # find content in database from filename
    matching_content = get_content_by_filename(filename)
    if matching_content is None:
        return

    # move file to checksummed directory
    if move_file(filepath, destdir + os.sep + filename) is False:
        print "ERROR: '" + filename + "' couldn't be moved to '" + destdir +"'."
        return

    # TO DO: save sha256 to database

    # check and update content processing status
    if matching_content.processing_state != 'previewed':
        print "WARNING: File '" + filename + "' in the previewed folder had status '" + \
                matching_content.processing_state +"'."
    matching_content.processing_state = 'checksummed'
    matching_content.save()


def fingerprint_audiofile(srcdir, destdir, filename):
    """
    Audiofingerprint a single file.

    Along with metadata lookup and store it on the EchoPrint server
    """

    filepath = os.path.join(srcdir, filename)

    # get track_id and metadata from the creation via content table
    matching_content = get_content_by_filename(filename)
    if matching_content is None:
        return
    matching_creation = get_creation_by_content(matching_content)
    if matching_creation is None:
        return

    if matching_creation.artist.name == '' or matching_creation.title == '':
        print "--> postponed till metadata is available"
        return

    if len(matching_creation.releases) == 0:
        release = ''
    else:
        release = matching_creation.releases[0]
        # TO DO: decide what to do if there is more than one release for a title

    # create fringerprint from audio file using echoprint-codegen
    print '-' * 80
    print "processing file " + filepath
    proc = subprocess.Popen(["../echoprint-codegen/echoprint-codegen", filepath],
                            stdout=subprocess.PIPE)
    json_meta_fp = proc.communicate()[0]
    fpcode_pos = json_meta_fp.find('"code":')
    if fpcode_pos > 0 and len(json_meta_fp) > 80:
        print "Got from codegen:" + json_meta_fp[:fpcode_pos+40] + \
                "....." + json_meta_fp[-40:]
    else:
        print "Got from codegen:" + json_meta_fp
    meta_fp = json.loads(json_meta_fp)

    # save fingerprint to echoprint server
    data = {'track_id': matching_creation.code,
            'token' : FILEHANDLING_CONFIG['echoprint_server_token'],
            'fp': meta_fp[0]['code'],
            'artist' : matching_creation.artist.name,
            'release' : release,
            'track' : matching_creation.title,
            'length' : int(matching_content.length),
            'codever' : str(meta_fp[0]['metadata']['version']),
           }
    json_data = json.dumps(data)
    fpcode_pos = json_data.find('"fp":')
    if fpcode_pos > 0 and len(json_data) > 250:
        print "Sent to server: " + json_data[:fpcode_pos+40] + "....." + \
                json_data[-200:].replace(FILEHANDLING_CONFIG['echoprint_server_token'], 9*'*')
    else:
        print "Sent to server: " + \
                json_data.replace(FILEHANDLING_CONFIG['echoprint_server_token'], 9*'*')
    print
    ingest_request = requests.post("https://echoprint.c3s.cc/ingest",
                                   data,
                                   verify=False, # TO DO: remove when certificate is updated
                                  )
    print
    print "Server response:", ingest_request.status_code, ingest_request.reason
    print
    print "Body: " + (ingest_request.text[:500] + '...' + ingest_request.text[-1500:]
                      if len(ingest_request.text) > 2000 else ingest_request.text)

    # check and update content processing state
    if matching_content.processing_state != 'checksummed':
        print "WARNING: File '" + filename + "' in the checksummed folder had status '" + \
                matching_content.processing_state +"'."
    matching_content.processing_state = 'fingerprinted'
    matching_content.save()

    # TO DO: user access control
    Fingerprintlog = Model.get('content.fingerprintlog')
    new_logentry = Fingerprintlog()
    user = Model.get('res.user')
    matching_users = user.find(['login', '=', 'admin'])
    if not matching_users:
        return

    new_logentry.user = matching_users[0]
    new_logentry.content = matching_content
    new_logentry.timestamp = datetime.datetime.now()
    new_logentry.fingerprinting_algorithm = 'EchoPrint'
    new_logentry.fingerprinting_version = str(meta_fp[0]['metadata']['version'])
    new_logentry.save()

    # move file to fingerprinted directory
    if move_file(filepath, destdir + os.sep + filename) is False:
        print "ERROR: '" + filename + "' couldn't be moved to '" + destdir +"'."
        return


#--- Helper functions ---


# notiz fuer mich: von Content aus betrachtet: content.creation.licenses[n].name


def get_content_by_filename(filename):
    """
    Get a content by filename/uuid.
    """
    content = Model.get('content')
    matching_contents = content.find(['uuid', "=", filename])
    if matching_contents is None:
        print "ERROR: Wasn't able to find content entry in the database for '" + filename + "'."
        return None
    if len(matching_contents) > 1: # unlikely with uuids, but we are supersticious...
        print "WARNING: More than one content entry in the database for '" + filename + \
              "'. Using the first one."
    return matching_contents[0]


def get_creation_by_content(content):
    """
    Get a creation by content(.id).
    """
    creation = Model.get('creation')
    matching_creations = creation.find(['id', "=", content.id])
    if matching_creations is None:
        print "ERROR: Wasn't able to find creation entry in the database with id '" + content.id + \
              "' for file '" + content.uuid + "'."
        return None
    if len(matching_creations) > 1:
        print "WARNING: More than one content entry in the database for '" + content.uuid + \
              "'. Using the first one."
    return matching_creations[0]


def directory_walker(processing_step_func, args):
    """
    Walks through the specified directory tree.

    Applies the specified repertoire processing step for each file.

    Example: directory_walker(fingerprint_audiofile, (sourcedir, destdir))
    """

    startpath = args[0]
    destdir = args[1]
    if ensure_path_exists(destdir) is None:
        print "ERROR: '" + destdir + "' couldn't be created."
        return

    uuid4rule = '^[0-9A-F]{8}-[0-9A-F]{4}-[4][0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$'
    uuid4hex = re.compile(uuid4rule, re.I)
    for root, _, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        if level == 1:
            for audiofile in files:
                if uuid4hex.match(audiofile) is not None: # only uuid4 compilant filenames
                    destsubdir = root.replace(args[0], destdir)
                    if ensure_path_exists(destsubdir) is None:  # ensure user subfolder exists
                        print "ERROR: '" + destdir + "' couldn't be created."
                        continue
                    processing_step_func(root, destsubdir, audiofile)


def move_file(source, target):
    """
    Moves a file from one path to another.
    """

    # check file
    if not os.path.isfile(source):
        return False
    if os.path.isfile(target):
        return False
    # move file
    try:
        #shutil.copyfile(source, target)
        #shutil.copyfile(source + ".checksums", target + ".checksums")
        #os.remove(source)
        #os.remove(source + ".checksums")
        os.rename(source + ".checksums", target + ".checksums")
        os.rename(source, target) # suppose we only have one mounted filesystem
    except IOError:
        pass
    return os.path.isfile(target) and not os.path.isfile(source)


def ensure_path_exists(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except IOError:
            pass
    return os.path.exists(path)


#--- Click Commands ---


@click.group()
def repro():
    """
    Repertoire Processor command line tool.
    """


@repro.command('checksum')
#@click.pass_context
def checksum():
    """
    Get files from previewed_path and hash them.
    """
    directory_walker(checksum_audiofile, (FILEHANDLING_CONFIG['previewed_path'],
                                          FILEHANDLING_CONFIG['checksummed_path']))


@repro.command('fingerprint')
#@click.pass_context
def fingerprint():
    """
    Get files from checksummed_path and fingerprint them.
    """
    directory_walker(fingerprint_audiofile, (FILEHANDLING_CONFIG['checksummed_path'],
                                             FILEHANDLING_CONFIG['fingerprinted_path']))


@repro.command('match')
#@click.argument('code')
#@click.pass_context
def match(): # code
    """
    match fingerprint, get the identifier from the echoprint server
    """

    # for testing, match first fingerprint code in creation.utilisation.imp
    #code = ""

    utilizations = Model.get('creation.utilisation.imp')
    result = utilizations.find(['title', "=", "999,999"])
    if not result:
        sys.exit()
    #code = result.fingerprint

    print result[0].fingerprint


if __name__ == '__main__':
    repro()
