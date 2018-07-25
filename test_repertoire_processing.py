#!/usr/bin/python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: ...

"""Test the archive processing
tryton service for c3s.ado.repertoire has to be
running and accessible to run these tests.
"""

import subprocess
import ConfigParser
import unittest

import trytonAccess
import fileTools
import repro

import click
from click.testing import CliRunner


# --- read config from .ini
CONFIGURATION = ConfigParser.ConfigParser()
CONFIGURATION.read("config.ini")
pconf = dict(CONFIGURATION.items('proteus'))


class TestRepertoireProcessing(unittest.TestCase):

    def setUp(self):
        self.tearDown()

    def tearDown(self):
        pass

    def _create_correct_filestructure(self, uid, user):
        # create dirs and files
        pass

    def _create_correct_example_data(self):
        trytonAccess.connect(pconf)


    def _delete_correct_example_data(self):
        trytonAccess.connect(pconf)

    def test_preview(self):

        runner.invoke(repro.preview)
        assert False

    def test_checksum(self):

        runner.invoke(repro.checksum)
        assert False

    def test_fingerprint(self):

        runner.invoke(repro.fingerprint)
        assert False

    def test_drop(self):

        runner.invoke(repro.drop)
        assert False

if __name__ == '__main__':
    runner = CliRunner()
    unittest.main()