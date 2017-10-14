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
import trytonAccess
import fileTools


# --- read config from .ini
CONFIGURATION = ConfigParser.ConfigParser()
CONFIGURATION.read("config.ini")
PROTEUS_CONFIG = dict(CONFIGURATION.items('proteus'))
ARC_CONF = dict(CONFIGURATION.items('archivehandling'))
HOSTNAME = socket.gethostname()

srchost_ssh = ARC_CONF['srcuser'] + "@" + ARC_CONF['srchost']
desthost_ssh = ARC_CONF['destuser'] + "@" + ARC_CONF['desthost']
srcdir_closed = ARC_CONF['srcdir'] + ".closed"


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
# use http only on local test instance (and uncomment [ssl] entries in
# server side trytond.conf for using http)
# proteus.config.set_xmlrpc(
#    "http://" + PROTEUS_CONFIG['user'] + ":" + PROTEUS_CONFIG['password']
#    + "@" + PROTEUS_CONFIG['host'] + ":" + PROTEUS_CONFIG['port'] + "/"
#    + PROTEUS_CONFIG['database']
# )
trytonAccess.connect(PROTEUS_CONFIG)

# get single full paths of sourcefiles as list
lines = list_files(srchost_ssh, ARC_CONF['srcdir'])
filepaths = lines.split()

# create .closed dir on source host if not exists
subprocess.call(["ssh", srchost_ssh, "mkdir -p " + srcdir_closed])

# move  files to .closed folder on source host
for filepath in filepaths:
    filename = fileTools.get_filename(filepath)
    (subprocess.call(["ssh", srchost_ssh, "mv", filepath,
                     srcdir_closed + "/" + filename]))

# rsync files to archive and delete them from .closed dir on source host
for filepath in filepaths:
    filename = fileTools.get_filename(filepath)
    result = -1
    # get 'real files', which are not checksum files
    print "[DEBUG] file: " + filepath
    if not fileTools.is_checksum_file(filename):
        chks = fileTools.checksum_correct(desthost_ssh, ARC_CONF['destdir'],
                                          filename)
        objs = (get_obj_state == "dropped")
        print "[DEBUG] chks is: " + chks
        print "[DEBUG] objs is: " + objs

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
    filename = fileTools.get_filename(filepath)
    if not fileTools.is_checksum_file(filename):
        if fileTools.checksum_correct(desthost_ssh, ARC_CONF['destdir'],
                                      filename):
            # rsync file to archive location and delete it on this machine,
            # set state to "archived"
            matching_content = trytonAccess.get_content_by_filename(filename)
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
