#!env/bin/python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: ...

"""
The one and only C3S fingerprinting utility
"""

import sys
import os
import subprocess
import ConfigParser
import json
import datetime
import click
import requests
from proteus import config, Model


# read config from .ini
CONFIGURATION = ConfigParser.ConfigParser()
CONFIGURATION.read("config.ini")
PROTEUS_CONFIG = dict(CONFIGURATION.items('proteus'))
FILEHANDLING_CONFIG = dict(CONFIGURATION.items('filehandling'))

#  get access to database
config.set_xmlrpc(
    "https://"   + PROTEUS_CONFIG['user'] + ":" + PROTEUS_CONFIG['password'] + "@"
    + PROTEUS_CONFIG['host'] + ":" + PROTEUS_CONFIG['port'] + "/" + PROTEUS_CONFIG['database']
)

def process_audiofile(path, filename):
    """
    Audiofingerprinting a single file along with metadata lookup.
    """

    filepath = path + os.sep + filename

    # get track_id and metadata from web service
    content = Model.get('content')
    for matching_content in content.find(['uuid', "=", filename]):
        creation = Model.get('creation')
        for matching_creation in creation.find(['id', "=", matching_content.id]):

            if matching_creation.artist.name == '' or matching_creation.title == '':
                print "--> postponed till metadata is available"
                break

            if len(matching_creation.releases) == 0:
                release = ''
            else:
                release = matching_creation.releases[0]
                # TO DO: decide what to do if there is more than one release for a title

            # create fringerprint from audio file using echoprint-codegen
            print '-' * 80
            print "processing file " + filepath
            proc = subprocess.Popen(["../echoprint-codegen/echoprint-codegen", filepath],
                                    stdout=subprocess.PIPE)
            json_meta_fp = proc.communicate()[0]
            fpcode_pos = json_meta_fp.find('"code":')
            if fpcode_pos > 0 and len(json_meta_fp) > 80:
                print "Got from codegen:" + json_meta_fp[:fpcode_pos+40] + \
                      "....." + json_meta_fp[-40:]
            else:
                print "Got from codegen:" + json_meta_fp
            meta_fp = json.loads(json_meta_fp)

            # save fingerprint to echoprint server
            data = {'track_id': matching_creation.code,
                    'token' : FILEHANDLING_CONFIG['echoprint_server_token'],
                    'fp': meta_fp[0]['code'],
                    'artist' : matching_creation.artist.name,
                    'release' : release,
                    'track' : matching_creation.title,
                    'length' : int(matching_content.length),
                    'codever' : str(meta_fp[0]['metadata']['version']),
                   }
            json_data = json.dumps(data)
            fpcode_pos = json_data.find('"fp":')
            if fpcode_pos > 0 and len(json_data) > 250:
                print "Sent to server: " + json_data[:fpcode_pos+40] + "....." + \
                      json_data[-200:].replace(FILEHANDLING_CONFIG['echoprint_server_token'], 9*'*')
            else:
                print "Sent to server: " + \
                      json_data.replace(FILEHANDLING_CONFIG['echoprint_server_token'], 9*'*')
            print
            ingest_request = requests.post("https://echoprint.c3s.cc/ingest",
                                           data,
                                           verify=False, # TO DO: remove when certificate is updated
                                          )
            print
            print "Server response:", ingest_request.status_code, ingest_request.reason
            print
            print "Body: " + (ingest_request.text[:500] + '...' + ingest_request.text[-1500:]
                              if len(ingest_request.text) > 2000 else ingest_request.text)

            # TO DO: update content processing state
            matching_content.processing_state = 'fingerprinted'
            matching_content.save()

            # TO DO: how the heck do I tell tryton who is the user??
            Fingerprintlog = Model.get('content.fingerprintlog')
            new_logentry = Fingerprintlog()
            user = Model.get('res.user')
            matching_users = user.find(['login', '=', 'admin'])
            if not matching_users:
                return

            new_logentry.user = matching_users[0]
            new_logentry.content = matching_content
            new_logentry.timestamp = datetime.datetime.now()
            new_logentry.fingerprinting_algorithm = 'EchoPrint'
            new_logentry.fingerprinting_version = str(meta_fp[0]['metadata']['version'])
            new_logentry.save()

            # TO DO: move file from complete folder to fingerprinted folder

            break
        break

@click.group()
def fingerprint():
    """
    Command line tool to print fingers.
    """

@fingerprint.command('get-jobs')
#@click.pass_context
def get_jobs():
    """
    Get Jobs
    """

    #webuser = Model.get('web.user')
    #for web_user in webuser.find(['email', "=", "meik@c3s.cc"]):
    #    print web_user.nickname

    startpath = FILEHANDLING_CONFIG['complete_path']
    for root, _, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        if level == 1:
            for audiofile in files:
                if audiofile is not "archive.info":
                    process_audiofile(root, audiofile)

@fingerprint.command('match')
#@click.argument('code')
#@click.pass_context
def match(): # code
    """
    match fingerprint, get the identifier from the echoprint server
    """

    # for testing, match first fingerprint code in creation.utilisation.imp
    #code = ""

    utilizations = Model.get('creation.utilisation.imp')
    result = utilizations.find(['title', "=", "999,999"])
    if not result:
        sys.exit()
    #code = result.fingerprint

    print result[0].fingerprint


if __name__ == '__main__':
    fingerprint()
