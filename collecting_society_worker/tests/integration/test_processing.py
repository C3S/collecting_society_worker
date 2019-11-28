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
    archive_proc,
    trytonAccess,
    repro
)

test_uuid = "540e8400-e29b-11d4-a716-476655440123"

class TestProcessing(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestProcessing, self).__init__(*args, **kwargs)

    def setUp(self):
        pass

    def tearDown(self):
        pass        

    def test_echoprintserver_token_set(self):
        """
        checking if the EchoPrint server token is no longer the fake default
        """
        self.assertNotEqual(
            repro.FILEHANDLING_CONFIG['echoprint_server_token'],
            "s0secret!!",
            "default echoprint server token still set; "
            "please change the token in services/worker.env "
            "according to the one in API.py on the EchoPrint server."
        )

    def test_echoprintserver_for_existing_fingerprint(self):
        """
        querying a fingerprint that does exist on the EchoPrint server
        """
        # this is a fingerprint from the track "999,999" by "Nine Inch Nails",
        # which is part of the EchoNest test data set
        try:
            url = "https://echoprint.c3s.cc/query"
            id = "fp_code"
            fingerprint = (
                "eJzlmUtuJDEORK-kLykeh_rw_keYp1qMewyUNo1eDdAIw5lVmRQZDAbdKaU8"
                "0wOavUDzC2y-YOsDcj8vuB_7Dr5esPcLYj6g3EN_h9VecOwFEQ-o1V4w5AWe"
                "H9Cqv2ClBxDbC5q_QPYLzF5wy_gVck0v6P4CHS9Y6wX3zF-h1PICfcI99Hc4"
                "_oCa7AXuL9j1BdEe0FI8AGa-oM0XXFJ_h9lfsPwFpzwgp_WC2y7focsLZL1g"
                "-At8v-Ajpd-g9PYC0ReM_oIzH1BrfcHUB_wVc2y_YPUXnPWAXOcLpLzgWd9y"
                "Ves7FH3Bjfs7aHuB5RdcAfgOZz-g6nmBywviBf933HhXcOwX2HnBHC_4iMc3"
                "qGm8QPwFo77A2wvWfECq_QVvbqi84N8x52-48a7vu0PLeEErL5D6gJbyCywe"
                "kK6kfYcaL-j5BTpf4PGCnR-Qk7wgjxdc6n2Hf8aNWp7w7-p7jfB3uDX-Dp8H"
                "fIX1gnxl6Tv8M_XO2x5Qhr7gXcG_qdF9_Hd4VBDpyPvokL3kHFZPNnWbq7Q0"
                "Su99-I5ueqJJ1e2xZE5ZY9gcZ-3kspsfF74zZKZ6qp2S-1p9txKthUF71dlE"
                "eEgz5WWrSdor95JbXQV_MFrNOlnGaKDTZfne9YzRzyjzsCtFT7NKdB9tY5Fm"
                "y-uK1mzN46SJXgsmcxyMSD8iaZXt3ofZ5xvTz5mSTm-zmrWdLa8RR3kozRz1"
                "nK3GwzWU1avbIaClBGRyZo-RMz88SR5rFtz5tBNpZY4ak2M04Rh5zH0Djlwr"
                "HKqluWrxtj45KBpSxXbdy2XYWmN2y14t21QhDXyqbpKbxK4p6qOM--Wwk3fp"
                "B3PG08aeJWlnz47ohTdgu8fYw8Xb3JoXeSh2wy497-zKSTxZaWcsqrPqPLnm"
                "HPc1Rc-avJFajVrL0pmTiY5ZTls_kOdO-de1P8CtyKA6KwWLSZ-R2Xzq8nAS"
                "JTy25lhe1UtWiMgLVSEK669udRoxRHYnDZncH84w51ySCwQKKpnijE3ErGJn"
                "WfGos3SXZYncaG23mBe7RdaVx7hng6FH61oFNlWq1NXKTM0HHsdWJV2nJSeh"
                "noVEEH-WdAszz5aycyF1EZSsk8EJr9pWIYZ-sjV4JnMUabBi7W27xPF5C0aS"
                "Obzo5X0YD9ewUmLdx1ToLnSQm3ParSM8r96MpaqvPksmYOjWQlutxypdxcFq"
                "32mfrnrP1ludO2tz-LgapmoZXrEmDoEPqq2WTVrCYspRTaTfSqdX8TLdz1Cu"
                "01k92tiZNbCt6rnfBoKUUtj94GZt22II5-gVvzg6X0kkl4KxSNfes12xKbvY"
                "CFt7rQpLe1lt9gl_2p9gtcb5de0HpEFSUqrnNIGlR_0EafVcKgyvWqyLwwmU"
                "QqLM3reQkjHbgiyZG0gxYYYvrt8eGbA38qTkw3lJs6YB99GwncxDSMgxb6Nl"
                "dV-bfius8EoYzfo5V4Gi90lq49RSEm1bFvna5_aHDvemMkKoNOOUp1-97CFm"
                "U7webZ0EsUXV1en0tEYVbo_jpWuWWdpqVHxHaTRA7NSCCkBvPggxOTg8ajRP"
                "0BhEZgRRU2csNN2tI80daomhxrld1u5Q6Nh7y9At0HEay4mgx6FXVpHZEo-n"
                "TPQ0XYD6ocpZB-KaFbFJgyOkXNDL0mLOUISpo0e7ZUR9JgYAlDtzIAvl_rFE"
                "TtIj2kj3FfTqTuBoCLqEYhaicgIdfH5Rk0G1oFteMXab7jZGbTMOOyyyoH3R"
                "78lYh9MmxPgBI7zf135Auw7lxeiNjdSgTjafvYiV3RkWMErZKkhm51CZ38qM"
                "ddlLjXZDUM-BKiSQpjmfLAXa6IMFaaI1926_lPzcpcamn7tllqvVfO1zF4UZ"
                "sRhNTJt95ufJkyYsCP6kTm6ZpNxpRfdQ57k_z4vcFsODb9BWsMxcQvPdN-Qw"
                "CZUphIzDaYUsPOQKhBTeBJeFaXCgIznMGymn8TSYLdNC04E6necw4uaV1LTa"
                "uY2z1qywP5PVNM90AmRqlQo7UZXMwnkWjdbdRyrS7ykg6n3GkGKCIUDCLO3b"
                "QQy2z2RLB9FBFRlijL18Eg1SaCkXi7B5Jw66qJugu1CrfJB4alWKMYRRYI5S"
                "GDwMREhPtpjshqIaB8dPNNkQDKHriWb0IfEDUKftX9d-wE83Qbfu38cZcnux"
                "jaFjUulZ6uBGV63o7JW9V9wafUa6eXN1fm13OlmWVozRMQ48LFruXN29dUTx"
                "c7eEM83uXeuMuc9dpDPq52ufu1aGdHqJiaLU-PNkHyOUMJlgkwmCFKt1LtBI"
                "e1EYakCzcPpFQ-a8mCbtDowV5VNVhgwcoyLIdUA5DJsw6ApsqDT0obPJrczK"
                "a47tdVJWpY0p-x1CQWZWsnkGysQAwbhlzFLeuDeVikC6HjiBhzl92Z3pGaNC"
                "Ig27UxjVJDHaPb93X5WwRfFVDDerKMWdfcySNNyi9lrxHjmn2-PO2GYryhN9"
                "RM6Zk0YZzsS_RCZk-o4mHE4-Eh9P2OAlQ1eqWulnrdpuZpj2Qv021KcDdcas"
                "xEHCf4A-Q4H-99ofdxtFQ9HSmTSDHTLj9EhCIxjheNKkVXZBnQrdw30GDrWx"
                "a-fy0uO3CsyOzQAkKj5Fg6-JfnzukjT8YEP6f-4KkrzOprE-dyV19BOrjKYM"
                "iIflKjiD1hDyPoWuLMMqxsJwxbbMGUuQVlpNOLdrf7FBKSaz0ZE2RnHDVOMO"
                "C5EVWpgS05jnjlUCnWOjFogL3xn-CY2SXxtrnBiWMGJvVQLpKBh84tlMVLQT"
                "dVr5GqJGYR1VRHiD37EmBYe2Bo4Sa-GTtQEynlyuI7kjlrJlvVqD5BP2wbBi"
                "g_MneiTQ7ZMDqofnusmZg3H1A59M_rr2x93KkfCtY_GwlpQphWcgOG4x0y9H"
                "ByWFptPVF96lVeaEznOpJzk5LFKsjHWKzCRjXqCH-_Jq0ZkYRJz4rtOmaeLI"
                "16tKv1a6DeiBfuAwPKxm3AeTktNjv5E6OiXdqUfLLFSAKg16gbMeFhX0kp99"
                "37_7EgUdgR_YKHDUy4qAl2wHvmmzzURhekXlemKvoHcOiprCsf245rTRxjJG"
                "Gv1OarzBoF_0rgosIca0xwyw7LCYZMwn6oDJvgsgNIE1dZMvpgZ-jbN3NF23"
                "BD4pVnZnqWBki-LDLSNvMNQrLcP7iCrfjXtjuWhs7CUrDwOAbYIkoe_R57r_"
                "gbAnclsRY6YvHw9hHMkfwLg6v6_9F3z10TVBw6tJJpgE8mp4OfLAP7wcvhF_"
                "eJeeoMnwyxNC9lKbZhg1uM5eQQsxZ2F6nyysgcNJLFxboJBeD5aRZhRHCH8c"
                "-E7DwI3p66BgnDyYPagS2ksVO0Z94d0bmxwTSa7m3a2IBQMr3a4TQs7vkGs5"
                "4AzLXtw5lBgYKC2XA41FQzuOm3dgGIX-qozmkYvcBoIhTmYZvuy8LMMy-Exx"
                "Bvkm6kavdKqneLqB7ytstLyLsnRmEVvYteJYoeAggnPCw6CNieIQ-cDWCktU"
                "WyOjcTOcYRAmC9vNRkC3sxzgDJEIzKRWpgQDfIzCryh5LNZ4ptkPfLLx69oP"
                "_AelnBuU"
            )
            # query_request = requests.get(url + "?" + id + '=' + fingerprint                
            #     .encode('utf8'), verify=False
            # )
            query_request = requests.post(url, 
                data = { id: fingerprint.encode('utf8') }, verify=False
            )
            self.assertEqual(query_request.status_code, 200,
                "status code returned from server is not 200 but " + 
                query_request.status_code + " -- " +
                query_request.reason)
            self
            qresult = json.loads(query_request.text)
            self.assertGreaterEqual(int(qresult['score']), 50,
                "score from EchoPrintServer result is too low")
            self.asserEqual(qresult['artist'], "Nine Inch Nails")
            self.asserEqual(qresult['track'], "999,999")            
        except:
            self.assertTrue(False, "exception while sending get request; " + 
                "server returned code: " + str(query_request.status_code) + 
                " -- " + query_request.reason)

        self.assertNotEqual(
            repro.FILEHANDLING_CONFIG['echoprint_server_token'],
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
        querying a fingerprint on the EchoPrint server
        """

        # setup file and foldernames, provide test file in source folder
        testdatafolder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '..', 'testdata')
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
