#!/usr/bin/python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: ...

"""
Prepare test folders and files for the one and only C3S archive
processing utility
"""

import subprocess
import ConfigParser

CONFIGURATION = ConfigParser.ConfigParser()
CONFIGURATION.read("config.ini")
ARC_CONF = dict(CONFIGURATION.items('archivehandling'))

srchost_ssh = ARC_CONF['srcuser'] + "@" + ARC_CONF['srchost']
desthost_ssh = ARC_CONF['destuser'] + "@" + ARC_CONF['desthost']
srcdir_closed = ARC_CONF['srcdir'] + ".closed"

# empty example dirs
rmdirs = [ARC_CONF['srcdir'], srcdir_closed, ARC_CONF['destdir']]

for rmdir in rmdirs:
    subprocess.call(["ssh", srchost_ssh, "rm", "-r", rmdir + "/*"])

# prepare folder contents
mkdirs = ["user1", "user2"]
touchs = ["user1/uuid1",
          "user1/uuid1.checksums",
          "user1/uuid1.checksum",
          "user2/uuid2",
          "user2/uuid2.checksums",
          "user2/uuid2.checksum"]

for mkdir in mkdirs:
    subprocess.call(["ssh", srchost_ssh, "mkdir", "-p",
                    ARC_CONF['srcdir'] + "/" + mkdir])
for touch in touchs:
    subprocess.call(["ssh", srchost_ssh, "touch",
                    ARC_CONF['srcdir'] + "/" + touch])
