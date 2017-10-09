#!/usr/bin/python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: ...

"""
The one and only C3S archive processing utility
"""

import sys
import subprocess
import socket
import ssl
import ConfigParser
import pprint
import re
import hashlib
import proteus


# --- read config from .ini
CONFIGURATION = ConfigParser.ConfigParser()
CONFIGURATION.read("config.ini")
PROTEUS_CONFIG = dict(CONFIGURATION.items('proteus'))
ARC_CONF = dict(CONFIGURATION.items('archivehandling'))
HOSTNAME = socket.gethostname()

srchost_ssh = ARC_CONF['srcuser'] + "@" + ARC_CONF['srchost']
desthost_ssh = ARC_CONF['destuser'] + "@" + ARC_CONF['desthost']
srcdir_closed = ARC_CONF['srcdir'] + ".closed"


def get_content_by_filename(filename):
    """
    Get a content by filename/uuid.
    """
    Content = proteus.Model.get('content')
    matching_contents = Content.find(['uuid', "=", filename])
    if len(matching_contents) == 0:
        print "ERROR: Wasn't able to find content entry in the database \
              for '" + filename + "'."
        return None
    if len(matching_contents) > 1:
        # unlikely with uuids, but we are
        # supersticious...
        print "WARNING: More than one content entry in the database for '" \
              + filename + "'. Using the first one."
    return matching_contents[0]


def remote_path_exists(host_ssh, path):
    if subprocess.call(["ssh", host_ssh, "[ -d " + path + " ]"]) == 0:
        return True


def list_files(host_ssh, directory):
    """
    determines files on specific host in specific dir
    """
    if remote_path_exists(host_ssh, directory):
        lines = (subprocess.check_output(["ssh", host_ssh, "find "
                 + directory + "/ -type f -name \*"]))
        return lines


def get_rel_path(line, base_path):
    result_line = re.sub(base_path, "", line)
    return result_line


def get_filename(filepath):
    slashpos = filepath.rfind("/")
    return filepath[slashpos+1:]


def checksum_correct(host_ssh, directory, filename):

    filepath = directory + "/" + filename
    # read checksum from object and file contents to compare
    matching_content = get_content_by_filename(filename)
    bufsize = 65536
    sha256 = hashlib.sha256()
    if host_ssh != "":
        file_cont = (subprocess.check_output("ssh " + host_ssh + " 'cat "
                     + filepath + "'"))
        data = file_cont.read(bufsize)
        sha256.update(data)
        checksum = (subprocess.check_output("ssh " + host_ssh + " 'cat "
                    + filepath + ".checksum'"))
    else:
        # generate checksum from file
        with open(filepath, 'rb') as filetohash:
            while True:
                data = filetohash.read(bufsize)
                if not data:
                    break
                sha256.update(data)
        checkf = open(directory + "/" + filename + ".checksum", r)
        # checksum = print checkf

    # compare
    newhash_matches_checksum = (sha256.hexdigest() == checksum)
    # TODO compare with hash from obj db, too

    return newhash_matches_checksum


def obj_state_correct(filename):
    matching_content = get_content_by_filename(filename)
    return matching_content.processing_state == "dropped"


def set_content_unknown(filename):
    matching_content = get_content_by_filename(filename)
    matching_content.processing_state = "unknown"
    matching_content.save()


def archive_filebunch(filename):
    """
    rsync all files from source to destination host
    """
    srcfiles = [filename, filename + ".checksum",
                filename + ".checksums"]
    rs = 0
    for f in srcfiles:
        rsf = (subprocess.call(["rsync", srchost_ssh
                               + ":" + ARC_CONF['srcdir_closed']
                               + "/" + f,
                               desthost_ssh
                               + ":" + ARC_CONF['destdir']]))
        rs = rs + rsf
    return rs


def delete_src_filebunch(filename):
    srcfiles = [filename, filename + ".checksum",
                filename + ".checksums"]
    for f in srcfiles:
        (subprocess.call(["ssh", srchost_ssh, "rm",
                         srcdir_closed + "/" + f]))


# -------------
# main

# get access to tryton database for processing state updates
proteus.config.set_xmlrpc(
    ("https://" + PROTEUS_CONFIG['user'] + ":" + PROTEUS_CONFIG['password']
     + "@" + PROTEUS_CONFIG['host'] + ":" + PROTEUS_CONFIG['port'] + "/"
     + PROTEUS_CONFIG['database'])
)

# get single full paths of sourcefiles as list
lines = list_files(srchost_ssh, ARC_CONF['srcdir'])
filepaths = lines.split()

# create .closed dir on source host if not exists
subprocess.call(["ssh", srchost_ssh, "mkdir -p " + srcdir_closed])

# move  files to .closed folder on source host
for filepath in filepaths:
    filename = get_filename(filepath)
    (subprocess.call(["ssh", srchost_ssh, "mv", filepath,
                     srcdir_closed + "/" + filename]))

# rsync files to archive and delete them from .closed dir on source host
for filepath in filepaths:
    filename = get_filename(filepath)
    result = -1
    # get 'real files', which are not checksum files
    print "++++ file: " + filepath
    if not filename.endswith(".checksum") and \
       not filename.endswith(".checksums"):
        chks = checksum_correct(desthost_ssh, ARC_CONF['destdir'], filename)
        objs = obj_state_correct(filename)
        print "chks is: " + chks
        print "objs is: " + objs

        if chks and objs:
            result = archive_filebunch(filename)
        else:
            # move incorrect files to "unknown" folder and set state to
            # "unknown"
            # TODO: move files
            todo = "TODO"

        set_content_unknown(filename)

    if result == 0:
        delete_src_filebunch(filename)

# archive files if checksums correct
for filepath in filepaths:
    filename = get_filename(filepath)
    if not filename.endswith(".checksum") and \
       not filename.endswith(".checksums"):
        if checksum_correct(ARC_CONF['desthost_ssh'],
                            ARC_CONF['destdir'], filename):
            # rsync file to archive location and delete it on this machine,
            # set state to "archived"
            matching_content = get_content_by_filename(filename)
            matching_content.processing_state = "archived"
            # TODO insert archiving target name instead of "Archive"
            matching_content.archive = "Archive"
            matching_content.save()
        else:
            # move incorrect files to "unknown" folder and set state to
            # "unknown"
            # TODO: move files
            todo = "TODO"

        set_content_unknown(filename)
