#!/usr/bin/python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: ...

"""Test the audio fingerprinting
tryton service for c3s.ado.repertoire has to be
running and accessible to run these tests.
"""

import os
import shutil
import uuid
import tempfile
import subprocess
import ConfigParser
import unittest
import requests

from collecting_society_worker import (
    fileTools,
    archive_proc,
    trytonAccess
    # repro
)


class TestFingerprinting(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestFingerprinting, self).__init__(*args, **kwargs)

    def setUp(self):
        pass

    def tearDown(self):
        pass        

    def test_ingest(self):
        """
        ingesting a fingerprint into the EchoPrint servers database
        """
        assert(True)

    def test_query(self):
        """
        querying a fingerprint on the EchoPrint server
        """
        return  # XXXXXXXXXXXXXXXXXXXXXXXX

        from collecting_society_worker import repro

        # setup file and foldernames, provide test file in source folder
        testdatafolder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '..', 'testdata')
        sourcefolder = tempfile.mkdtemp()
        targetfolder = tempfile.mkdtemp()
        filename = 'NIN-19GhostsIII.mp3'
        if os.path.isfile(os.path.join(targetfolder, filename)):
            os.unlink(os.path.join(sourcefolder, filename))
        shutil.copyfile(os.path.join(testdatafolder, filename), 
            os.path.join(sourcefolder, filename))

        # setup content database entry
        Content = Model.get('content.fingerprintlog')
        new_logentry = Fingerprintlog()
        user = Model.get('res.user')
        matching_users = user.find(['login', '=', 'admin'])
        if not matching_users:
            return

        
        repro.fingerprint_audiofile(sourcefolder, targetfolder, filename)

        self.assertTrue(os.path.isfile(os.path.join(targetfolder, filename)),
            "File wasn't moved to the target folder")
        self.assertFalse(os.path.isfile(os.path.join(sourcefolder, filename)),
            "File still is in the source folder")        
