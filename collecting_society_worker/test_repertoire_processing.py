#!/usr/bin/env python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: https://github.com/C3S/collecting_society_worker

"""Test the archive processing
tryton service for c3s.ado.repertoire has to be
running and accessible to run these tests.
"""

import configparser
import unittest

from . import trytonAccess
from . import repro

from click.testing import CliRunner


# --- read config from .ini
CONFIGURATION = configparser.ConfigParser()
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
