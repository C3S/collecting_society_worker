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
import datetime
import random
import json

from proteus import config, Model
from collecting_society_worker import (
    fileTools,
    trytonAccess,
    repro
)

test_uuid = "540e8400-e29b-11d4-a716-476655440123"

testdatafolder = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'data')

class TestProcessing(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestProcessing, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        repro.connect_db()

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_echoprintserver_for_existing_fingerprint(self):
        """
        querying a fingerprint that does exist on the EchoPrint server
        """
        # this test uses a fingerprint from "billie jean" by michael jackson,
        # which is part of the EchoNest test data set
        url = repro.ECHOPRINT_URL + "/query"
        id = "fp_code"
        fp_file = open(os.path.join(testdatafolder,
                       "michael_jackson_-_billie_jean.fingerprint"),"r")
        fingerprint = fp_file.read()

        # query_request = requests.get(url + "?" + id + '=' + fingerprint
        #     .encode('utf8'), verify=False
        # )
        query_request = requests.post(url,
            data = { id: fingerprint.encode('utf8') }, verify=False
        )
        self.assertEqual(query_request.status_code, 200,
            "status code returned from server is not 200 but " +
            str(query_request.status_code) + " -- " +
            query_request.reason)
        qresult = json.loads(query_request.text)
        self.assertGreaterEqual(int(qresult['score']), 50,
            "score from EchoPrintServer result is too low")
        self.assertEqual(qresult['artist'], "Michael Jackson")
        self.assertEqual(qresult['track'], "Billie Jean")

        self.assertNotEqual(
            repro.ECHOPRINT_CONFIG['token'],
            "s0secret!!",
            "default echoprint server token still set; "
            "please change the token in services/worker.env "
            "according to the one in API.py on the EchoPrint server."
        )

    def test_ingest(self):
        """
        ingesting a fingerprint into the EchoPrint servers database
        """
        assert(True)

    def test_processing(self):
        """
        fingerprint_audiofile()
        """

        # setup file and foldernames, provide test file in source folder
        sourcefolder = tempfile.mkdtemp()
        targetfolder = tempfile.mkdtemp()
        original_filename = 'NIN-19GhostsIII.mp3'
        sourcepath = os.path.join(sourcefolder, test_uuid)
        targetpath = os.path.join(targetfolder, test_uuid)
        if os.path.isfile(sourcepath):
            os.unlink(sourcepath)
        shutil.copyfile(os.path.join(testdatafolder, original_filename), sourcepath)

        # find an artist as entity_creator
        #Artist = Model.get('artist')
        #artists = Artist.find([('claim_state', '!=', 'unclaimed')])
        #self.assertTrue(artists,
        #    "Not able to find an artist as entity_creator in testdata")
        #artist = artists[0]

        WebUser = Model.get('web.user')
        birthdate = datetime.date(
            random.randint(1950, 2000),
            random.randint(1, 12),
            random.randint(1, 28))
        firstname = "John"
        lastname = "Doe"
        web_user = WebUser(
            email='john.doe@rep.test',
            nickname=firstname + ' ' + lastname,
            password="%s" % random.randint(0, 2000000),
            opt_in_state='opted-in'
        )
        web_user.default_role = 'licenser'
        web_user.save()
        web_user.party.firstname = firstname
        web_user.party.lastname = lastname
        web_user.party.name = firstname + ' ' + lastname
        web_user.party.repertoire_terms_accepted = True
        web_user.party.birthdate = birthdate
        web_user.party.save()        

        # create content database entry
        Content = Model.get('content')
        c = Content()
        c.uuid = test_uuid
        c.commit_state = 'uncommited'
        c.entity_creator = web_user.party
        c.processing_hostname = "processing_test"
        c.processing_state = "checksummed"
        c.entity_origin = "direct"
        c.name = original_filename
        c.category = "audio"
        c.mime_type = "audio/mpeg"
        c.size = os.path.getsize(sourcepath)
        c.length = 131  # in seconds
        c.path = sourcepath
        c.preview_path = '/some/preview/path'
        c.save()

        self.assertTrue(trytonAccess.get_content_by_filename(test_uuid),
            "content record coudn't be added to the database")

        user = Model.get('res.user')
        matching_users = user.find(['login', '=', 'admin'])
        if not matching_users:
            return

        repro.fingerprint_audiofile(sourcefolder, targetfolder, test_uuid)

        # TODO: Find out what this error might mean when deleting the content:
        #       Fault 1: "('UserError', ('foreign_model_exist', ''))"
        # Content.delete(c)

        #WebUser.delete(web_user)
        #WebUser.delete(web_user.party)

        self.assertTrue(os.path.isfile(os.path.join(targetfolder, test_uuid)),
            "File wasn't moved to the target folder")
        self.assertFalse(os.path.isfile(os.path.join(sourcefolder, test_uuid)),
            "File still is in the source folder")        
