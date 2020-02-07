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

test_uuid = str(uuid.uuid4())  # like "540e8400-e29b-11d4-a716-476655440123"
tmp1 = tempfile.mkdtemp()
tmp2 = tempfile.mkdtemp()

class TestProcessing(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestProcessing, self).__init__(*args, **kwargs)

        repro.connect_db()

        # some object variables
        self.WebUser = Model.get('web.user')
        self.Content = Model.get('content')
        self.Party = Model.get('party.party')
        self.c = None
        self.web_user = None
        self.testdatafolder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'data')

        # read fingerprint from file
        self.url = repro.ECHOPRINT_URL + "/query"
        self.var_id = "fp_code"
        self.fingerprint = open(os.path.join(self.testdatafolder,
                                "NIN-19GhostsIII.fingerprint"),"r").read()



         # make sure previews and excerpts paths exist
        self.content_base_path = repro.FILEHANDLING_CONFIG['content_base_path']
        if repro.ensure_path_exists(self.content_base_path) is None:
            print(
                "ERROR: '" +
                self.content_base_path +
                "' couldn't be created as content base path."
            )
            return
        self.previews_path = os.path.join(
            repro.FILEHANDLING_CONFIG['previews_path'],
            test_uuid[0],
            test_uuid[1])
        self.excerpts_path = os.path.join(
            repro.FILEHANDLING_CONFIG['excerpts_path'],
            test_uuid[0],
            test_uuid[1])

        # create excerpt paths with filenames
        excerpts_filepath_relative = os.path.join(self.excerpts_path, test_uuid)
        self.excerpts_filepath = os.path.join(
            self.content_base_path,
            excerpts_filepath_relative
        )   

        # create preview paths with filenames
        previews_filepath_relative = os.path.join(self.previews_path, 
            test_uuid)
        self.previews_filepath = os.path.join(
            self.content_base_path,
            previews_filepath_relative
        )

        # setup file and foldernames, provide test file in source folder
        self.sourcefolder = tmp1
        self.targetfolder = tmp2
        original_filename = 'NIN-19GhostsIII.mp3'
        self.source_filepath = os.path.join(self.sourcefolder, test_uuid)
        self.target_filepath = os.path.join(self.targetfolder, test_uuid)
        if os.path.isfile(self.source_filepath):
            os.unlink(self.source_filepath)
        shutil.copyfile(os.path.join(self.testdatafolder, original_filename),
            self.source_filepath)

        # TODO: no clue how to delete a webuser
        # find_webuser = self.WebUser.find(['email', "=", 'john.doe@rep.test'])
        # if find_webuser:  # clean up db, if record existed before
        #     wu = find_webuser[0]
        #     User = Model('res.user')
        #     Party = Model('party.party')
        #     Artist = Model('artist')
        #     WebUserRole = Model('web.user.role')
        #     p = None
        #     if wu.party:
        #         p = wu.party
        #     self.WebUser.delete(wu)
        #     wu.party = None
        #     if p:
        #         self.Party.delete(p)
        birthdate = datetime.date(
            random.randint(1950, 2000),
            random.randint(1, 12),
            random.randint(1, 28))
        firstname = "John"
        lastname = "Doe"
        self.web_user = self.WebUser(
            email='john.doe' + str(random.randint(0, 2000000)) + '@rep.test',
            nickname=firstname + ' ' + lastname,
            password="%s" % random.randint(0, 2000000),
            opt_in_state='opted-in'
        )
        self.web_user.default_role = 'licenser'
        self.web_user.save()
        self.web_user.party.firstname = firstname
        self.web_user.party.lastname = lastname
        self.web_user.party.name = firstname + ' ' + lastname
        self.web_user.party.repertoire_terms_accepted = True
        self.web_user.party.birthdate = birthdate
        self.web_user.party.save()        

        # create content database entry
        find_content = self.Content.find(['uuid', "=", test_uuid])
        if find_content:
            self.Content.delete(find_content[0])  # clean up db, just in case        
        self.c = self.Content()
        self.c.uuid = test_uuid
        self.c.commit_state = 'uncommited'
        self.c.entity_creator = self.web_user.party
        self.c.processing_hostname = "processing_test"
        self.c.processing_state = "checksummed"
        self.c.entity_origin = "direct"
        self.c.name = original_filename
        self.c.category = "audio"
        self.c.mime_type = "audio/mpeg"
        self.c.size = os.path.getsize(self.source_filepath)
        self.c.length = 131  # in seconds
        self.c.path = self.source_filepath
        self.c.preview_path = '/some/preview/path'
        self.c.save()

        self.assertTrue(trytonAccess.get_content_by_filename(test_uuid),
            "content record coudn't be added to the database")


    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass


    # TODO: fix
    def _test_005_query_existing_fingerprint(self):
        """
        querying a fingerprint that does already exist on the EchoPrint server
        """
        # this test uses a fingerprint from "billie jean" by michael jackson,
        # which is part of the EchoNest test data set
        url = repro.ECHOPRINT_URL + "/query"
        var_id = "fp_code"
        fp_file = open(os.path.join(self.testdatafolder,
                       "michael_jackson_-_billie_jean.fingerprint"),"r")
        fingerprint = fp_file.read()

        # query_request = requests.get(url + "?" + id + '=' + fingerprint
        #     .encode('utf8'), verify=False
        # )
        query_request = requests.post(url,
            data = { var_id: fingerprint.encode('utf8') }, verify=False
        )

        self.assertEqual(query_request.status_code, 200,
            "status code returned from server is not 200 but " +
            str(query_request.status_code) + " -- " +
            query_request.reason)
        qresult = json.loads(query_request.text)
        self.assertGreaterEqual(int(qresult['score']), 50,
            "score from EchoPrintServer result is too low (" +
            str(qresult['score']) + ")")
        self.assertEqual(qresult['track_id'], "TRWIZHB123E858D912")

        self.assertNotEqual(
            repro.ECHOPRINT_CONFIG['token'],
            "s0secret!!",
            "default echoprint server token still set; "
            "please change the token in services/worker.env "
            "according to the one in API.py on the EchoPrint server."
        )


    # TODO: fix deletion of a fingerprint on the echoprint server
    #       (step through server code as soon as ptvsd 5 is available!)
    def _test_010_delete_a_fingerprint(self):
        """
        deleting a fingerprint that does already exists on the EchoPrint server
        """
        # this test uses a fingerprint from "billie jean" by michael jackson,
        # which is part of the EchoNest test data set
        url = repro.ECHOPRINT_URL + "/delete"
        var_id = "track_id"
        track = "TRWIZHB123E858D912"

        query_request = requests.post(url,
            data = { var_id: track }, verify=False
        )
        self.assertEqual(query_request.status_code, 200,
            "status code returned from server is not 200 but " +
            str(query_request.status_code) + " -- " +
            query_request.reason)

        self.assertNotEqual(
            repro.ECHOPRINT_CONFIG['token'],
            "s0secret!!",
            "default echoprint server token still set; "
            "please change the token in services/worker.env "
            "according to the one in API.py on the EchoPrint server."
        )

    # TODO: fix
    def _test_020_query_before_ingestion(self):
        """
        query non-existing print (before ingestion)
        """       

        # query before ingestion -- result should be negative
        query_request = requests.post(self.url,
            data = { self.var_id: self.fingerprint.encode('utf8') }, verify=False
        )
        self.assertEqual(query_request.status_code, 200,
            "status code returned from server is not 200 but " +
            str(query_request.status_code) + " -- " +
            query_request.reason)
        qresult = json.loads(query_request.text)
        self.assertEqual(int(qresult['score']), 0,
            "query for not existing fingerprint should result in a score of 0"
            " but actually is " + str(qresult['score']))
        self.assertEqual(qresult['match'], False,
            "false positive match from query to EchoPrint server") 

    def _reload_sourcefolder(self):
        """
        check processing folders, move file from target to source folder again
        for next test
        """
        self.assertTrue(
            os.path.isfile(os.path.join(self.targetfolder, test_uuid)),
            "File wasn't moved to the target folder")
        self.assertFalse(
            os.path.isfile(os.path.join(self.sourcefolder, test_uuid)),
            "File still is in the source folder") 
        self.assertTrue(
            repro.move_file(
                os.path.join(self.targetfolder, test_uuid),
                os.path.join(self.sourcefolder, test_uuid)
            ),
            "couldn't move the audiofile back to the source folder"
        )

    def test_100_preview(self):
        """
        preview processing stage: create a preview and excerpt from audio file
        """

        repro.preview_audiofile(self.sourcefolder, 
            self.targetfolder, test_uuid)
        self.assertTrue(os.path.isfile(self.previews_filepath),
            "no preview file was created")
        self._reload_sourcefolder()

    def test_200_checksum(self):
        """
        checksum processing stage: create a checksum from audio file
        """

        repro.checksum_audiofile(self.sourcefolder, 
            self.targetfolder, test_uuid)
        self.assertTrue(os.path.isfile(self.target_filepath + ".checksum"),
            "no checksum file was created")
        # TODO: further checking, i.e. file checksum with db entry
        self._reload_sourcefolder()

    def XXXXXXXXXtest_300_fingerprint(self):
        """
        fingerprint processing stage and query after ingestion
        """

        repro.fingerprint_audiofile(self.sourcefolder, 
            self.targetfolder, test_uuid)

        # query after ingestion -- result should be positive
        query_request = requests.post(self.url,
            data = { self.id: self.fingerprint.encode('utf8') }, verify=False
        )

        self.assertEqual(query_request.status_code, 200,
            "status code returned from server is not 200 but " +
            str(query_request.status_code) + " -- " +
            query_request.reason)
        qresult = json.loads(query_request.text)
        self.assertGreaterEqual(int(qresult['score']), 50,
            "score from EchoPrintServer result is too low (" +
            str(qresult['score']) + ") -- message from server: '" +
            qresult['message'] + "'")
        self.assertEqual(qresult['track_id'], 
            test_uuid.replace('-', ''))
        self._reload_sourcefolder()                 

    def test_900_cleanup(self):
        """
        deleting test records and cleanup
        """
        # TODO: Find out what this error might mean when deleting the content:
        #       Fault 1: "('UserError', ('foreign_model_exist', ''))"
        # self.Content.delete(self.c)

        #self.WebUser.delete(self.web_user)
        #self.WebUser.delete(self.web_user.party)

        if os.path.isfile(self.source_filepath):
            os.unlink(self.source_filepath)
        if os.path.isfile(self.target_filepath):
            os.unlink(self.target_filepath)
        if os.path.isfile(self.source_filepath + ".checksum"):
            os.unlink(self.source_filepath + ".checksum")
        if os.path.isfile(self.target_filepath + ".checksum"):
            os.unlink(self.target_filepath + ".checksum")
        if os.path.isdir(self.sourcefolder):
            os.rmdir(self.sourcefolder)
        if os.path.isdir(self.targetfolder):
            os.rmdir(self.targetfolder)

        if os.path.isfile(self.excerpts_filepath):
            os.unlink(self.excerpts_filepath)
        if os.path.isdir(self.excerpts_path):
            os.rmdir(self.excerpts_path)
        if os.path.isfile(self.previews_filepath):
            os.unlink(self.previews_filepath)        
        if os.path.isdir(self.previews_path):
            os.rmdir(self.previews_path)
