#!/usr/bin/python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: ...

"""
Test the archive processing
tryton service for c3s.ado.repertoire has to be
running and accessible to run these tests.
"""

import subprocess
import ConfigParser
import unittest

import trytonAccess
import fileTools
import archive_proc

# --- read config from .ini
CONFIGURATION = ConfigParser.ConfigParser()
CONFIGURATION.read("config.ini")
pconf = dict(CONFIGURATION.items('proteus'))
aconf = dict(CONFIGURATION.items('archivehandling'))

srchost_ssh = (aconf["srcuser"] + ":" + aconf["srcpw"] + "@"
               + aconf["srchost"])
desthost_ssh = (aconf["destuser"] + ":" + aconf["destpw"]
                + "@" + aconf["desthost"])
srcdir_closed = aconf["srcdir"] + ".closed"

# prepare folder contents
example_files = [["testuser1", "uuid1"],
                 ["testuser2", "uuid2"]]
checks_file = ".checksum"
checks_all = ".checksums"
rmdirs = [aconf["srcdir"], srcdir_closed, aconf["destdir"]]


class TestArchiveProc(unittest.TestCase):

    def setUp(self):
        self.tearDown()

    def tearDown(self):
        # empty example dirs
        for rmdir in rmdirs:
            subprocess.call(["ssh",
                             srchost_ssh,
                             "[ -f '" + rmdir + "' ] && rm '"
                             + rmdir + "/*'"])
        # TODO delete example tryton datasets

    def _create_correct_filestructure(self, uid, user):
        # create dirs and files
        subprocess.call(["ssh", srchost_ssh, "mkdir", "-p",
                        aconf["srcdir"] + "/" + str(uid)])
        for names in example_files:
            if names[0] == user:
                for f in (names[1], names[1] + checks_file,
                          names[1] + checks_all):
                    subprocess.call(["ssh", srchost_ssh, "touch",
                                    aconf["srcdir"] + "/" + str(uid) + "/"
                                    + f])

    def _create_correct_example_data(self):
        trytonAccess.connect(pconf)

        # insert and prepare datasets into tryton db
        for names in example_files:
            objUser = trytonAccess.get_or_insert_web_user(
                names[0] + "@example.test"
            )
            # if this content does not already exist
            if not trytonAccess.get_content_by_filename(names[1]):
                # create content with state "dropped"
                trytonAccess.insert_content_by_filename(
                    names[1], names[0], "dropped"
                )
            else:
                trytonAccess.update_content_pstate(names[1], "dropped")
            # create correct filestructure according to tryton data
            self._create_correct_filestructure(objUser.id, names[0])

    def _delete_correct_example_data(self):
        trytonAccess.connect(pconf)
        # delete example datasets from tryton db
        for names in example_files:
            trytonAccess.delete_web_user(names[0] + "@example.test")
            trytonAccess.delete_content(names[1])
        # files and folders will be deleted by tearDown function

    def test_correct_condition(self):
        self._create_correct_example_data()
        # start the archiving process
        aproc = archive_proc.ArchProc()
        aproc.start_proc()
        self._delete_correct_example_data()
