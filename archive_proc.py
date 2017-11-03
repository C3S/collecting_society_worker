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
pconf = dict(CONFIGURATION.items('proteus'))
aconf = dict(CONFIGURATION.items('archivehandling'))
HOSTNAME = socket.gethostname()

srchost_ssh = aconf['srcuser'] + ":" + aconf['srcpw'] + "@" + aconf['srchost']
desthost_ssh = (aconf['destuser'] + ":" + aconf['destpw'] + "@"
                + aconf['desthost'])
srcdir_closed = aconf['srcdir'] + ".closed"


class ArchProc():

    def _remote_path_exists(self, host_ssh, path):
        if subprocess.call(["ssh", host_ssh, "[ -d " + path + " ]"]) == 0:
            return True

    def _list_files(self, host_ssh, directory):
        """
        determines files on specific host in specific dir
        """
        if self._remote_path_exists(host_ssh, directory):
            lines = (subprocess.check_output(["ssh", host_ssh, "find "
                     + directory + "/ -type f -name \*"]))
            return lines

    def _archive_filebunch(self, filename):
        """
        rsync all files from source to destination host
        """
        srcfiles = [filename, filename + ".checksum",
                    filename + ".checksums"]
        rs = 0
        for f in srcfiles:
            subprocess.call(["ssh", desthost_ssh, "mkdir", "-p",
                             aconf['destdir'] + "/" + f[:1]])
            subprocess.call(["ssh", desthost_ssh, "mkdir", "-p",
                             aconf['destdir'] + "/" + f[:1] + "/" + f[1:2]])
            rsf = (subprocess.call(["rsync", srchost_ssh + ":" + srcdir_closed
                                    + "/" + f, desthost_ssh
                                    + ":" + aconf['destdir'] + "/"
                                    + f[:1] + "/" + f[1:2] + "/"]))
            rs = rs + rsf
        return rs

    def _delete_src_filebunch(self, filename):
        srcfiles = [filename, filename + ".checksum",
                    filename + ".checksums"]
        for f in srcfiles:
            (subprocess.call(["ssh", srchost_ssh, "rm",
                             srcdir_closed + "/" + f]))

    def start_proc(self):
        trytonAccess.connect(pconf)

        # get single full paths of sourcefiles as list
        lines = self._list_files(srchost_ssh, aconf['srcdir'])
        filepaths = lines.split()

        # create .closed dir on source host if not exists
        subprocess.call(["ssh", srchost_ssh, "mkdir -p " + srcdir_closed])

        # move files to .closed folder on source host
        for filepath in filepaths:
            filename = fileTools.get_filename(filepath)
            (subprocess.call(["ssh", srchost_ssh, "mv", filepath,
                              srcdir_closed + "/" + filename]))

        # rsync files to archive and delete them from .closed dir on source
        # host when checksums are correct
        lines = self._list_files(srchost_ssh, srcdir_closed)
        filepaths = lines.split()
        for filepath in filepaths:
            print "[path] " + filepath
            filename = fileTools.get_filename(filepath)
            result = -1
            # get 'real files', which are not checksum files
            if not fileTools.is_checksum_file(filename):
                print "[filename] " + filename
                chks = fileTools.checksum_correct(srchost_ssh, srcdir_closed,
                                                  filename)
                objs = (trytonAccess.get_obj_state(filename) == "dropped")
                print "[DEBUG] chks is: " + str(chks)
                print "[DEBUG] objs is: " + str(objs)
                # TODO: test success depending on these results

                if chks and objs:
                    result = self._archive_filebunch(filename)
                else:
                    # move incorrect files to "unknown" folder and set state to
                    # "unknown"
                    # TODO: move files
                    todo = "TODO"
                    # set_content_unknown(filename)

            if result == 0:
                self._delete_src_filebunch(filename)

        # set archive flag in db if archiving was successful
        for filepath in filepaths:
            filename = fileTools.get_filename(filepath)
            if not fileTools.is_checksum_file(filename):
                chks = fileTools.checksum_correct(srchost_ssh, srcdir_closed,
                                                  filename)
                # if chks:
                #     # set state to "archived"
                #     matching_content =
                #         trytonAccess.get_content_by_filename(filename)
                #     matching_content.processing_state = "archived"
                #     # TODO insert archiving target name instead of "Archive"
                #     matching_content.archive = "Archive"
                #     matching_content.save()
                # else:
                #     # move incorrect files to "unknown" folder and set state
                #     # to "unknown"
                #     # TODO: move files
                #     todo = "TODO"
                todo = "TODO"
                # set_content_unknown(filename)
