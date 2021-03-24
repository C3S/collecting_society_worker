#!/usr/bin/env python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: https://github.com/C3S/collecting_society_worker

"""
The one and only C3S tools for filehandling of repertoire files or similar
"""


import subprocess
import re
import hashlib
# import trytonAccess


def get_rel_path(line, base_path):
    result_line = re.sub(base_path, "", line)
    return result_line


def get_filename(filepath):
    slashpos = filepath.rfind("/")
    return filepath[slashpos+1:]


def get_path_only(filepath):
    slashpos = filepath.rfind("/")
    return filepath[:slashpos-1]


def checksum_correct(host_ssh, directory, filename):

    filepath = directory + "/" + filename
    # read checksum from object and file contents to compare
    # matching_content = trytonAccess.get_content_by_filename(filename)
    bufsize = 65536
    sha256 = hashlib.sha256()
    # when file is on remote host
    if host_ssh != "":
        try:
            subprocess.check_output(["ssh", host_ssh, "cat " + filepath])
        except Exception:
            print("file could not be checked")
            return False
        else:
            # TODO handle remote file's content
            # data = file_cont.read(bufsize)
            # sha256.update(data)
            checksum = (subprocess.check_output(["ssh", host_ssh, "cat "
                                                + filepath + ".checksum"]))
    else:
        # generate checksum from file
        with open(filepath, 'rb') as filetohash:
            while True:
                data = filetohash.read(bufsize)
                if not data:
                    break
                sha256.update(data)
        open(directory + "/" + filename + ".checksum", "r")
        # checksum = print checkf

    # compare
    newhash_matches_checksum = (sha256.hexdigest() == checksum)
    # TODO compare with hash from obj db, too

    return newhash_matches_checksum


def is_checksum_file(filename):
    if filename.endswith(".checksum") or filename.endswith(".checksums"):
        return True
