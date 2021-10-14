#!/usr/bin/python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: ...

"""Test the archive processing
tryton service for c3s.ado.repertoire has to be
running and accessible to run these tests.
"""

import os
import subprocess
import configparser
import unittest

from collecting_society_worker import (
    archive_proc,
    trytonAccess
)


class TestArchiveProc(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestArchiveProc, self).__init__(*args, **kwargs)

        # --- read config from .ini
        CONFIGURATION = configparser.ConfigParser()
        CONFIGURATION.read(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..', '..', '..', 'config.ini'))
        self.pconf = dict(CONFIGURATION.items('proteus'))
        self.aconf = dict(CONFIGURATION.items('archivehandling'))

        self.srchost_ssh = (self.aconf["srcuser"] + ":" + self.aconf["srcpw"]
                            + "@" + self.aconf["srchost"])
        self.desthost_ssh = (self.aconf["destuser"] + ":"
                             + self.aconf["destpw"] + "@"
                             + self.aconf["desthost"])
        self.srcdir_closed = self.aconf["srcdir"] + ".closed"

        # prepare folder contents
        self.example_files = [
            ["testuser1", "uuid1"],
            ["testuser2", "uuid2"]]
        self.checks_file = ".checksum"
        self.checks_all = ".checksums"
        self.rmdirs = [
            self.aconf["srcdir"],
            self.srcdir_closed,
            self.aconf["destdir"]]

    def setUp(self):
        self.tearDown()

    def tearDown(self):
        # empty example dirs
        for rmdir in self.rmdirs:
            subprocess.call(["ssh",
                             self.srchost_ssh,
                             "[ -f '" + rmdir + "' ] && rm '"
                             + rmdir + "/*'"])
        # TODO delete example tryton datasets
        pass

    def _create_correct_filestructure(self, uid, user):
        # create dirs and files
        subprocess.call(["ssh", self.srchost_ssh, "mkdir", "-p",
                        self.aconf["srcdir"] + "/" + str(uid)])
        for names in self.example_files:
            if names[0] == user:
                for f in (names[1], names[1] + self.checks_file,
                          names[1] + self.checks_all):
                    subprocess.call(["ssh", self.srchost_ssh, "touch",
                                    self.aconf["srcdir"] + "/" + str(uid) + "/"
                                    + f])

    def _create_correct_example_data(self):
        trytonAccess.connect(self.pconf)

        # insert and prepare datasets into tryton db
        for names in self.example_files:
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
        trytonAccess.connect(self.pconf)
        # delete example datasets from tryton db
        for names in self.example_files:
            trytonAccess.delete_web_user(names[0] + "@example.test")
            trytonAccess.delete_content(names[1])
        # files and folders will be deleted by tearDown function

    def test_correct_condition(self):
        self._create_correct_example_data()
        # start the archiving process
        aproc = archive_proc.ArchProc()
        aproc.start_proc()
        self._delete_correct_example_data()
