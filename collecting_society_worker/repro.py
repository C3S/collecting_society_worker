#!/usr/bin/env python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: https://github.com/C3S/collecting_society_worker

"""
The one and only C3S repertoire processing utility
"""


# --- Imports ---

import os
import time
import fcntl
import socket
import subprocess
import configparser
import json
import datetime
import re
import hashlib
import click
import requests
from pydub import AudioSegment
import taglib
from proteus import config, Model
try:
    import trytonAccess
except Exception:
    from . import trytonAccess
# import fileTools

# --- some constants ---

# 2DO: _preview_default
_preview_format = 'ogg'
_preview_quality = '0'
_preview_samplerate = '16000'
_preview_fadein = 1000
_preview_fadeout = 1000
_preview_segment_duration = 8000
_preview_segment_crossfade = 2000
_preview_segment_interval = 54000
_excerpt_format = 'wav'
_excerpt_quality = '0'
_excerpt_samplerate = '11025'
_excerpt_fadein = 0
_excerpt_fadeout = 0
_excerpt_segment_duration = 60000


# --- some initialization ---

def expand_envvars(section):
    return dict(
        (k, os.path.expandvars(v)) for k, v in section.items()
    )


# read config from .ini
CONFIGURATION = configparser.ConfigParser()
CONFIGURATION.read(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'config.ini'))

# debugging
try:
    DEBUGGING_CONFIG = expand_envvars(dict(CONFIGURATION.items('debugging')))
    # winpdb
    if int(DEBUGGING_CONFIG['debugger_winpdb']):
        import rpdb2
        rpdb2.start_embedded_debugger("supersecret", fAllowRemote=True)
    # ptvsd
    if int(DEBUGGING_CONFIG['debugger_ptvsd']):
        import ptvsd
        ptvsd.enable_attach(address=("0.0.0.0", 51002), redirect_output=True)
        # print("ptvsd debugger listening to port 51002.")
except configparser.NoSectionError:
    pass

try:
    PROTEUS_CONFIG = expand_envvars(dict(CONFIGURATION.items('proteus')))
except configparser.NoSectionError:
    print(
        "Error: Please run repro.py "
        "from the collecting_society_worker main folder.")
    exit()

FILEHANDLING_CONFIG = expand_envvars(dict(CONFIGURATION.items('filehandling')))

ECHOPRINT_CONFIG = expand_envvars(dict(CONFIGURATION.items('echoprint')))
ECHOPRINT_SCHEMA = ECHOPRINT_CONFIG['schema']
assert ECHOPRINT_SCHEMA
ECHOPRINT_HOSTNAME = ECHOPRINT_CONFIG['hostname']
assert ECHOPRINT_HOSTNAME
ECHOPRINT_PORT = ECHOPRINT_CONFIG['port']
if not ECHOPRINT_PORT:
    ECHOPRINT_PORT = 80
ECHOPRINT_URL = (ECHOPRINT_SCHEMA + "://" + ECHOPRINT_HOSTNAME + ":" +
                 ECHOPRINT_PORT)

HOSTNAME = socket.gethostname()
STORAGE_BASE_PATH = FILEHANDLING_CONFIG['storage_base_path']


# --- Processing stage functions for single audiofiles ---


def preview_audiofile(srcdir, destdir, filename):
    """
    Creates a low-quality preview audio snippet for newly uploaded files.
    """

    # make sure previews and excerpts paths exist
    content_base_path = FILEHANDLING_CONFIG['content_base_path']
    if ensure_path_exists(content_base_path) is None:
        print("ERROR: '" + content_base_path +
              "' couldn't be created as content base path.")
        return

    # create directories in absolute paths if needed
    previews_path = os.path.join(
        FILEHANDLING_CONFIG['previews_path'],
        filename[0],
        filename[1])
    excerpts_path = os.path.join(
        FILEHANDLING_CONFIG['excerpts_path'],
        filename[0],
        filename[1])
    if ensure_path_exists(
            os.path.join(content_base_path, previews_path)
    ) is None:
        print("ERROR: '" +
              os.path.join(content_base_path, previews_path) +
              "' couldn't be created for previews.")
        return
    if ensure_path_exists(
            os.path.join(content_base_path, excerpts_path)
    ) is None:
        print(
            "ERROR: '" +
            os.path.join(content_base_path, excerpts_path) +
            "' couldn't be created for excerpts.")
        return

    # create paths with filenames
    filepath = os.path.join(srcdir, filename)
    previews_filepath_relative = os.path.join(previews_path, filename)
    excerpts_filepath_relative = os.path.join(excerpts_path, filename)
    previews_filepath = os.path.join(
        content_base_path,
        previews_filepath_relative)
    excerpts_filepath = os.path.join(
        content_base_path,
        excerpts_filepath_relative)

    # find content in database from filename
    try:
        matching_content = trytonAccess.get_content_by_filename(filename)
    except Exception:
        print("ERROR: Database seems to be under rebuild. Trying again later.")
        exit()
    if matching_content is None:
        print(
            "ERROR: Couldn't find content entry for '" +
            filename +
            "' in database.")
        reject_file(
            filepath,
            'missing_database_record',
            "File name: " +
            filepath)
        return

    if matching_content.category == 'audio':
        # create preview
        audio = AudioSegment.from_file(filepath)
        result = create_preview(audio, previews_filepath)
        if not result:
            print("ERROR: '" + filename + "' couldn't be previewed.")
            return

        # create excerpt
        result = create_excerpt(audio, excerpts_filepath)
        if not result:
            print(
                "ERROR: No excerpt could be cut out of '" +
                filename + "'.")
            return

        # do a first test query on the EchoPrint server (2nd one after ingest)
        score = 0
        track_id_from_test_query = None
        similiar_artist = ''
        similiar_track = ''

        # create fingerprint from audio file
        # using echoprint-codegen and relate to the score
        print('-' * 80)
        print("test query with excerpt file " + excerpts_filepath)
        try:
            proc = subprocess.Popen(["echoprint-codegen", excerpts_filepath],
                                    stdout=subprocess.PIPE)
        except OSError:
            print(
                "Error: Unable to find echoprint-codegen executable in exe "
                "path."
            )
            return
        json_meta_fp = str(proc.communicate()[0], "utf-8")
        fpcode_pos = json_meta_fp.find('"code":')
        if fpcode_pos > 0 and len(json_meta_fp) > 80:
            print(
                "Got from codegen:" +
                json_meta_fp[:fpcode_pos+40] +
                "....." + json_meta_fp[-40:])

            meta_fp = json.loads(json_meta_fp)

            try:
                query_request = requests.get(
                    ECHOPRINT_URL + "/query?fp_code=" +
                    meta_fp[0]['code'],
                    verify=False,  # TODO: remove when cert. is updated
                )
            except Exception as e:
                raise e
                print(
                    "ERROR: '" + excerpts_filepath_relative +
                    "' couldn't be test-queried on the EchoPrint server.")
                return

            print
            print(
                "Server response: ",
                query_request.status_code,
                query_request.reason)
            print
            print(
                "Body: " +
                (query_request.text[:500] +
                 '...' + query_request.text[-1500:]
                 if len(query_request.text) > 2000 else query_request.text)
            )

            if query_request.status_code != 200:
                print(
                    "ERROR: '" +
                    srcdir +
                    "' cloudn't be test-queried on the EchoPrint server.")
            else:
                qresult = json.loads(query_request.text)
                score = qresult['score']
                if qresult['match']:
                    track_id_from_test_query = (
                        qresult['track_id'][:8] +
                        '-' +
                        qresult['track_id'][8:12] +
                        '-' +
                        qresult['track_id'][12:16] +
                        '-' +
                        qresult['track_id'][16:]
                    )
                    # TODO: get these two from the creation table:
                    if 'artist' in qresult.keys():
                        similiar_artist = qresult['artist']
                    if 'track' in qresult.keys():
                        similiar_track = qresult['track']
        else:
            print("Got from codegen:" + json_meta_fp)

        # check and update content processing status,
        # save some pydub metadata to database
        if matching_content.processing_state != 'uploaded':
            print(
                "WARNING: File '" +
                filename +
                "' in the uploaded folder had status '" +
                matching_content.processing_state +
                "'.")
        matching_content.processing_state = 'previewed'
        matching_content.processing_hostname = HOSTNAME
        matching_content.path = filepath.replace(
            STORAGE_BASE_PATH +
            os.sep, '')  # relative path
        matching_content.preview_path = previews_filepath
        matching_content.length = int(audio.duration_seconds)
        matching_content.channels = int(audio.channels)
        matching_content.sample_rate = int(audio.frame_rate)
        matching_content.sample_width = int(audio.sample_width * 8)
        matching_content.pre_ingest_excerpt_score = score
        if track_id_from_test_query:
            most_similar_content = trytonAccess.get_content_by_filename(
                track_id_from_test_query)
            if most_similar_content is None:
                print(
                    "ERROR: Couldn't find content entry " +
                    "of most similar content for '" +
                    filename +
                    "' in database. EchoPrint server seems " +
                    "out of sync with database."
                )
            else:
                matching_content.most_similiar_content = most_similar_content
        matching_content.most_similiar_artist = similiar_artist
        matching_content.most_similiar_track = similiar_track

        # read metadata from file
        try:  # to append the extension from the original filename temporarily,
            # because taglib
            # isn't smart enough to process files without the proper extension
            filepath_plus_extension = filepath + os.path.splitext(
                matching_content.name)[1]
            os.rename(filepath, filepath_plus_extension)
            try:
                song = taglib.File(filepath_plus_extension)
                if song.tags:
                    if "ARTIST" in song.tags and song.tags["ARTIST"][0]:
                        matching_content.metadata_artist = song.tags[
                                                           "ARTIST"][0]
                    if "TITLE" in song.tags and song.tags["TITLE"][0]:
                        matching_content.metadata_title = song.tags["TITLE"][
                                                          0]
                    if "ALBUM" in song.tags and song.tags["ALBUM"][0]:
                        matching_content.metadata_release = song.tags["ALBUM"][
                                                            0]
                    if "TDOR" in song.tags and song.tags["TDOR"][0]:
                        matching_content.metadata_release_date = song.tags[
                            "TDOR"][0]
                    if (
                            "TRACKNUMBER" in song.tags and
                            song.tags["TRACKNUMBER"][0]
                    ):
                        matching_content.metadata_track_number = song.tags[
                            "TRACKNUMBER"][0]
            except OSError:
                print(
                    "WARNING: taglib couldn't extract any metadata from file '"
                    + filepath_plus_extension +
                    "' "
                )
            try:
                os.rename(filepath_plus_extension, filepath)
            except IOError:
                print(
                    "ERROR: File '" +
                    filepath_plus_extension +
                    "' in the uploaded folder that was temporarily " +
                    "renamed to have a file extension " +
                    "to retrieve metadata from it couldn't be renamed back")
        except IOError as e:
            print(e)
            print(
                "WARNING: File '" +
                filename +
                "' in the uploaded folder couldn't be renamed " +
                "temproarily to retrieve metadata from it")
        # song.tags

        matching_content.save()

        # check it the audio format is much too bad even for 8bit enthusiasts
        reason_details = ''
        if audio.frame_rate < 11025:
            reason_details = (
                'Invalid frame rate of ' +
                str(int(audio.frame_rate)) +
                ' Hz')
        if audio.sample_width < 1:
            # less than one byte? is this even possible? :-p
            reason_details = (
                'Invalid sample rate of ' +
                str(int(audio.sample_width * 8)) +
                ' bits')
        if reason_details != '':
            reject_file(filepath, 'format_error', reason_details)
            return

    # move file to previewed directory
    if move_file(filepath, destdir + os.sep + filename) is False:
        print(
            "ERROR: '" +
            filename +
            "' couldn't be moved to '" +
            destdir + "'.")
        return


def get_segments(audio):
    """
    Yields the segments back to the caller one by one.
    """
    _total = len(audio)
    _segment = _preview_segment_duration
    _interval = _preview_segment_interval
    if _segment >= _total:
        yield audio
    else:
        start = 0
        end = _segment
        while end < _total:
            yield audio[start:end]
            start = end + _interval + 1
            end = start + _segment


def create_preview(audio, preview_path):
    """
    mix a cool audio preview file with low quality
    """

    # convert to mono
    mono = audio.set_channels(1)

    # mix segments
    preview = None
    for segment in get_segments(mono):
        preview = segment if not preview else preview.append(
            segment, crossfade=_preview_segment_crossfade
        )

    # fade in/out
    preview = preview.fade_in(_preview_fadein).fade_out(_preview_fadeout)

    # export
    ok_return = True
    try:
        preview.export(
            preview_path,
            format=_preview_format,
            parameters=[
                "-aq", _preview_quality,
                "-ar", _preview_samplerate
            ]
        )
    except Exception:
        ok_return = False

    return ok_return and os.path.isfile(preview_path)


def create_excerpt(audio, excerpt_path):
    """
    well, as the functin name says...
    """

    # convert to mono
    # mono =
    audio.set_channels(1)

    # this was for experimenting with different code lengths:
    # for exlen in range(1000, 61000, 1000):
    #    # cut out one minute from the middle of the file
    #    if len(audio) > exlen:
    #        excerpt_center = len(audio) / 2
    #        excerpt_start = excerpt_center - exlen/2
    #        excerpt_end = excerpt_center + exlen/2
    #        audio2 = audio[excerpt_start:excerpt_end]
    #
    #    # export
    #    ok_return = True
    #    try:
    #        audio2.export(
    #            excerpt_path+"-"+str(int(exlen/1000))+".wav",
    #            format=_excerpt_format,
    #            parameters=[
    #                "-aq", _excerpt_quality,
    #                "-ar", _excerpt_samplerate
    #            ]
    #        )
    #    except:
    #        ok_return = False

    # cut out one minute from the middle of the file
    if len(audio) > 60000:
        excerpt_center = len(audio) / 2
        excerpt_start = excerpt_center - 30000
        excerpt_end = excerpt_center + 30000
        audio = audio[excerpt_start:excerpt_end]

    # export
    ok_return = True
    try:
        audio.export(
            excerpt_path,
            format=_excerpt_format,
            parameters=[
                "-aq", _excerpt_quality,
                "-ar", _excerpt_samplerate
            ]
        )
    except Exception:
        ok_return = False

    return ok_return and os.path.isfile(excerpt_path)


def checksum_audiofile(srcdir, destdir, filename):
    """
    Hashing a single file.
    """

    filepath = os.path.join(srcdir, filename)
    statinfo = os.stat(filepath)
    filelength = statinfo.st_size

    bufsize = 65536

    sha256 = hashlib.sha256()

    with open(filepath, 'rb') as filetohash:
        while True:
            data = filetohash.read(bufsize)
            if not data:
                break
            sha256.update(data)

    print(
        "SHA256 of file {0}: {1}".format(
            filename,
            sha256.hexdigest())
    )

    # TO DO:
    # check for duplicate checksums in database
    # and possibly issue a 'checksum_collision'

    # find content in database from filename
    matching_content = trytonAccess.get_content_by_filename(filename)
    if matching_content is None:
        print(
            "ERROR: Orphaned file " +
            filename +
            " (no DB entry) -- please clean up!")
        return  # shouldn't happen

    # write checksum to file '<UUID>.checksum'
    checksumfile = open(srcdir + os.sep + filename + '.checksum', 'w+')
    checksumfile.write(sha256.__class__.__name__ + ':' + sha256.hexdigest())
    checksumfile.close()

    # move file to checksummed directory
    if move_file(filepath, destdir + os.sep + filename) is False:
        print(
            "ERROR: '" +
            filename +
            "' couldn't be moved to '" +
            destdir +
            "'."
        )
        return

    # check and update content processing status
    if (matching_content.processing_state != 'previewed' and
            matching_content.category == 'audio'):
        print(
            "WARNING: File '" +
            filename +
            "' in the previewed folder had status '" +
            matching_content.processing_state + "'.")
    if (matching_content.processing_state != 'previewed' and
            matching_content.processing_state != 'uploaded' and
            matching_content.category == 'sheet'):
        print(
            "WARNING: File '" +
            filename +
            "' in the previewed folder had status '" +
            matching_content.processing_state + "'.")
    matching_content.processing_state = 'checksummed'
    matching_content.processing_hostname = HOSTNAME
    matching_content.path = filepath.replace(
        STORAGE_BASE_PATH + os.sep,
        '')  # relative path
    matching_content.save()

    # save sha256 to database
    matching_checksums = [
        x for x in matching_content.checksums if (
            x.begin == 0 and
            x.end == filelength
        )
    ]
    if len(matching_checksums) == 0:
        # create a checksum
        Checksum = Model.get('checksum')
        checksum_to_use = Checksum()
        matching_content.checksums.append(checksum_to_use)
    elif len(matching_checksums) > 1:  # shouldn't happen
        print(
            "WARNING: More than one whole file checksum entry " +
            "in the database for '" +
            filename +
            "'. Please clean up the mess! Using the first one.")
    else:
        checksum_to_use = matching_checksums[0]  # just one found: use it!

    checksum_to_use.code = sha256.hexdigest()
    checksum_to_use.timestamp = datetime.datetime.now()
    checksum_to_use.algorithm = sha256.__class__.__name__
    checksum_to_use.begin = 0
    checksum_to_use.end = filelength
    checksum_to_use.save()


def fingerprint_audiofile(srcdir, destdir, filename):
    """
    Audiofingerprint a single file.

    Comes along with metadata lookup and store it on the EchoPrint server.
    """

    filepath = os.path.join(srcdir, filename)

    # get track_id and metadata from the creation via content table
    matching_content = trytonAccess.get_content_by_filename(filename)
    if matching_content is None:
        return

    if matching_content.category == 'audio':
        # already metadata present in creation?
        # then put it on the EchoPrint server rightaway
        artist = ''
        title = ''
        release = ''
        matching_creation = trytonAccess.get_creation_by_content(
                            matching_content)
        if matching_creation:
            artist = matching_creation.artist.name
            title = matching_creation.title
            if matching_creation.releases:
                release = matching_creation.releases[0].title
            if artist == '':
                artist = 'DummyFiFaFu'
            if title == '':
                title = 'DummyFiFaFu'
            if release == '':
                release = 'DummyFiFaFu'

        # create fringerprint from audio file using echoprint-codegen
        print('-' * 80)
        print("processing file " + filepath)
        proc = subprocess.Popen(
            ["echoprint-codegen", filepath],
            stdout=subprocess.PIPE)
        json_meta_fp = proc.communicate()[0]
        fpcode_pos = json_meta_fp.find('"code":')
        if fpcode_pos > 0 and len(json_meta_fp) > 80:
            print(
                "Got from codegen:" +
                json_meta_fp[:fpcode_pos+40] +
                "....." + json_meta_fp[-40:]
            )
        else:
            print(
                "Got from codegen:" +
                json_meta_fp)
            reject_file(
                filepath,
                'no_fingerprint',
                "Got from codegen:" +
                json_meta_fp)
            return

        meta_fp = json.loads(json_meta_fp)

        # TO DO: More sanity checks with possible no_fingerprint rejection

        # save fingerprint to echoprint server
        data = {
            'track_id': filename.replace('-', ''),
            # '-' reserved for fp segment
            'token': ECHOPRINT_CONFIG['token'],
            'fp_code': meta_fp[0]['code'].encode('utf8'),
            'artist': artist,
            'release': release,
            'track': title,
            'length': int(matching_content.length),
            'codever': str(meta_fp[0]['metadata']['version']),
            }
        json_data = json.dumps(data)
        fpcode_pos = json_data.find('"fp":')
        if ECHOPRINT_CONFIG['token']:
            json_data_pwhidden = json_data[-200:].replace(
                                 ECHOPRINT_CONFIG['token'], 9*'*')
        else:
            json_data_pwhidden = json_data
        if fpcode_pos > 0 and len(json_data_pwhidden) > 250:
            print(
                "Ingesting to server: " +
                json_data_pwhidden[:fpcode_pos+40] +
                "....." +
                json_data_pwhidden[-200:]
            )
        else:
            print("Ingesting to server: " + json_data_pwhidden)
        print()

        try:
            ingest_request = requests.post(
                ECHOPRINT_URL + "/ingest",
                data,
                verify=False,  # TO DO: remove when certificate is updated
            )
        except Exception as e:
            reject_file(
                filepath,
                'no_fingerprint',
                (  # TODO think about a better message...
                    "Could not be sent to EchoPrint server " +
                    "response code (server offline?). Note: %s" % e
                )
            )
            print(
                "ERROR: '" +
                srcdir +
                "' cloudn't be ingested into the EchoPrint server."
            )
            return

        print()
        print(
            "Server response:",
            ingest_request.status_code,
            ingest_request.reason
        )
        print()
        if (len(ingest_request.text) > 2000):
            print(
                "Body: " +
                ingest_request.text[:500] +
                '...' +
                ingest_request.text[-1500:]
            )
        else:
            print(
                "Body: " +
                ingest_request.text
            )

        if ingest_request.status_code != 200:
            reject_file(
                filepath,
                'no_fingerprint',
                (
                    "Could not be sent to EchoPrint server response code " +
                    str(ingest_request.status_code) +
                    ': ' +
                    ingest_request.reason
                )
            )
            print(
                "ERROR: '" +
                srcdir +
                "' cloudn't be ingested into the EchoPrint server. " +
                "File rejected.")
            return

        # do a 2nd test query on the EchoPrint server
        # (1st was before ingest, during preview)
        score = 0
        track_id_from_test_query = ''
        # similiar_artist = ''
        # similiar_track = ''

        # make sure previews and excerpts paths exist
        content_base_path = FILEHANDLING_CONFIG['content_base_path']
        if ensure_path_exists(content_base_path) is None:
            print(
                "ERROR: '" +
                content_base_path +
                "' couldn't be created as content base path."
            )
            return

        excerpts_path = FILEHANDLING_CONFIG['excerpts_path']
        if (
                ensure_path_exists(excerpts_path) is None
        ):
            print(
                "ERROR: '" +
                excerpts_path +
                "' couldn't be created for excerpts."
            )
            return

        # create excerpt paths with filenames
        excerpts_filepath_relative = os.path.join(excerpts_path, filename)
        excerpts_filepath = os.path.join(
            content_base_path,
            excerpts_filepath_relative
        )

        # create fringerprint from audio file
        # using echoprint-codegen and relate to the score
        print('-' * 80)
        print("test query with excerpt file " + excerpts_filepath)
        proc = subprocess.Popen(
            ["echoprint-codegen", excerpts_filepath],
            stdout=subprocess.PIPE)
        json_meta_fp = proc.communicate()[0]
        fpcode_pos = json_meta_fp.find('"code":')
        if fpcode_pos > 0 and len(json_meta_fp) > 80:
            print(
                "Got from codegen:" +
                json_meta_fp[:fpcode_pos+40] +
                "....." + json_meta_fp[-40:])

            meta_fp = json.loads(json_meta_fp)

            try:
                query_request = requests.get(
                    ECHOPRINT_URL + "/query?fp_code=" +
                    meta_fp[0]['code'].encode('utf8'),
                    verify=False,  # TO DO: remove when cert. is updated
                )
            except Exception:
                print(
                    "ERROR: '" +
                    excerpts_filepath_relative +
                    "' cloudn't be test-queried on the EchoPrint server.")
                return

            print()
            print(
                "Server response: ",
                query_request.status_code,
                query_request.reason)
            print()
            print(
                "Body: " +
                (query_request.text[:500] + '...' + query_request.text[-1500:]
                 if len(query_request.text) > 2000 else query_request.text)
            )
            if query_request.status_code != 200:
                print(
                    "ERROR: '" +
                    srcdir +
                    "' cloudn't be test-queried on the EchoPrint server.")
            else:
                qresult = json.loads(query_request.text)
                score = qresult['score']
                if qresult['match']:
                    track_id_from_test_query = (
                        qresult['track_id'][:8] +
                        '-' +
                        qresult['track_id'][8:12] +
                        '-' +
                        qresult['track_id'][12:16] +
                        '-' +
                        qresult['track_id'][16:])
                    # similiar_artist = qresult['artist']
                    # similiar_track = qresult['track']
        else:
            print("Got from codegen:" + json_meta_fp)

        # check and update content processing state
        if matching_content.processing_state != 'checksummed':
            print(
                "WARNING: File '" +
                filename +
                "' in the checksummed folder had status '" +
                matching_content.processing_state +
                "'.")
        matching_content.processing_state = 'fingerprinted'
        matching_content.processing_hostname = HOSTNAME
        matching_content.path = filepath.replace(
            STORAGE_BASE_PATH +
            os.sep, '')  # relative path
        matching_content.post_ingest_excerpt_score = score
        if track_id_from_test_query:
            most_similar_content = trytonAccess.get_content_by_filename(
                track_id_from_test_query)
            if most_similar_content is None:
                print(
                    "ERROR: Couldn't find content entry " +
                    "of most similar content for '" +
                    filename +
                    "' in database. EchoPrint server seems " +
                    "out of sync with database.")
                reject_file(
                    filepath,
                    'missing_database_record',
                    "File name: " +
                    filepath)
            else:
                if (
                    track_id_from_test_query
                    ==
                    matching_content.most_similiar_content.uuid
                ):
                    matching_content.pre_ingest_excerpt_score = 0

        matching_content.save()

        # TO DO: user access control
        FingerprintLog = Model.get('content.fingerprintlog')
        new_logentry = FingerprintLog()
        user = Model.get('res.user')
        matching_users = user.find(['login', '=', 'admin'])
        if not matching_users:
            return

        new_logentry.user = matching_users[0]
        new_logentry.content = matching_content
        new_logentry.timestamp = datetime.datetime.now()
        new_logentry.fingerprinting_algorithm = 'EchoPrint'
        if fpcode_pos > 0 and len(json_meta_fp) > 80:
            new_logentry.fingerprinting_version = str(
                meta_fp[0]['metadata']['version'])
        else:
            new_logentry.fingerprinting_version = (
                "unknown (check if echoprint access token was set properly!)")
        new_logentry.entity_origin = 'direct'
        Party = Model.get('party.party')
        party = Party.find(['name', '=', 'C3S SCE'])[0]
        new_logentry.entity_creator = party
        new_logentry.save()

        # TO DO: check newly ingested fingerprint using the excerpt
        # Response codes:
        #     0 = NOT_ENOUGH_CODE,
        #     1 = CANNOT_DECODE,
        #     2 = SINGLE_BAD_MATCH,
        #     3 = SINGLE_GOOD_MATCH,
        #     4 = NO_RESULTS,
        #     5 = MULTIPLE_GOOD_MATCH_HISTOGRAM_INCREASED,
        #     6 = MULTIPLE_GOOD_MATCH_HISTOGRAM_DECREASED,
        #     7 = MULTIPLE_BAD_HISTOGRAM_MATCH,
        #     8 = MULTIPLE_GOOD_MATCH

    # move file to fingerprinted directory
    if move_file(filepath, destdir + os.sep + filename) is False:
        print(
            "ERROR: '" +
            filepath +
            "' couldn't be moved to '" +
            destdir +
            os.sep +
            filename +
            "'.")
        return


def drop_audiofile(srcdir, destdir, filename):
    """
    Does nothing but setting the processing step from fingerprinted to dropped.
    """

    filepath = os.path.join(srcdir, filename)

    # find content in database from filename
    matching_content = trytonAccess.get_content_by_filename(filename)
    if matching_content is None:
        print(
            "ERROR: Orphaned file " +
            filename +
            " (no DB entry) -- rejecting!")
        reject_file(
            filepath,
            'missing_database_record',
            "There was no content database record for " +
            filename)
        return  # shouldn't normally happen

    # move file to checksummed directory
    if move_file(filepath, destdir + os.sep + filename) is False:
        print(
            "ERROR: '" +
            filename +
            "' couldn't be moved to '" +
            destdir +
            "'.")
        return

    # overwrite file content with its filename
    # (so it generates different hash values)
    if FILEHANDLING_CONFIG['disembody_dropped_files'] == 'yes':
        overwritefile = open(destdir + os.sep + filename, 'w+')
        if (overwritefile is not None):
            overwritefile.write(filename)
        overwritefile.close()

    # check and update content processing status
    if (matching_content.processing_state != 'fingerprinted' and
            matching_content.category == 'audio'):
        print(
            "WARNING: File '" +
            filename +
            "' in the fingerprinted folder had status '" +
            matching_content.processing_state + "'.")
    if (matching_content.processing_state != 'fingerprinted' and
            matching_content.processing_state != 'checksummed' and
            matching_content.category == 'sheet'):
        print(
            "WARNING: File '" +
            filename +
            "' in the fingerprinted folder had status '" +
            matching_content.processing_state + "'.")
    matching_content.processing_state = 'dropped'
    matching_content.processing_hostname = HOSTNAME
    matching_content.path = filepath.replace(
        STORAGE_BASE_PATH +
        os.sep, '')  # relative path
    matching_content.save()


# --- Helper functions ---


def directory_walker(processing_step_func, args):
    """
    Walks through the specified directory tree.

    Applies the specified repertoire processing step for each file.

    Example: directory_walker(fingerprint_audiofile, (sourcedir, destdir))
    """

    startpath = args[0]
    destdir = args[1]
    processing_message = "Processing " + startpath
    processing_did_some_work = False
    if ensure_path_exists(destdir) is None:
        print(
            "ERROR: '" +
            destdir +
            "' couldn't be created.")
        return

    uuid4rule = (
        '^[0-9A-F]{8}-[0-9A-F]{4}-[4][0-9A-F]{3}'
        '-[89AB][0-9A-F]{3}-[0-9A-F]{12}$')
    uuid4hex = re.compile(uuid4rule, re.I)
    for root, _, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        if level == 1:
            for audiofile in files:
                if uuid4hex.match(audiofile) is not None:
                    # only uuid4 compilant filenames
                    destsubdir = root.replace(args[0], destdir)
                    if ensure_path_exists(destsubdir) is None:
                        # ensure user subfolder exists
                        print(
                            "ERROR: '" +
                            destdir +
                            "' couldn't be created.")
                        continue

                    # lock file
                    try:
                        audiofilepath = os.path.join(root, audiofile)
                        lockfilename = audiofilepath + '.lock'
                        lockfile = open(lockfilename, 'w+')
                        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)

                        # after successful locking,
                        # make sure the audiofile is still there ...
                        if os.path.isfile(audiofilepath):
                            # ... and process file
                            print(processing_message)
                            processing_did_some_work = True
                            processing_step_func(root, destsubdir, audiofile)

                        # unlock file
                        fcntl.flock(lockfile, fcntl.LOCK_UN)
                        lockfile.close()
                        # try:
                        os.remove(lockfilename)
                        # except OSError:
                        #    pass

                    except IOError:
                        print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
                        print("LOCKED: " + audiofile)
                        # pass

                    finally:
                        if lockfile:
                            lockfile.close()

    if processing_did_some_work:
        print("Finished processing " + startpath)


def move_file(source, target):
    """
    Moves a file from one path to another.
    """
    # check file
    if not os.path.isfile(source):
        return False
    if os.path.isfile(target):
        return False
    # move file
    try:
        # shutil.copyfile(source, target)
        # shutil.copyfile(source + ".checksums", target + ".checksums")
        # os.remove(source)
        # os.remove(source + ".checksums")
        # print "Moving files " + source + "* to " + target + "*."
        if os.path.isfile(source + ".checksums"):
            os.rename(source + ".checksums", target + ".checksums")
        if os.path.isfile(source + ".checksum"):
            os.rename(source + ".checksum", target + ".checksum")
        os.rename(source, target)
        # suppose we only have one mounted filesystem
    except IOError as e:
        print(e)
    return os.path.isfile(target) and not os.path.isfile(source)


def ensure_path_exists(path):
    """
    If path doesn't exist, create directory.
    """
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except IOError:
            pass
    return os.path.exists(path)


def reject_file(source, reason, reason_details):
    """
    Moves a file to the 'rejected' folder
    and writes the reject reason to the database.
    """

    # check file
    if not os.path.isfile(source):
        return False

    storage_base_path = FILEHANDLING_CONFIG['storage_base_path']
    if ensure_path_exists(storage_base_path) is None:
        print(
            "ERROR: '" +
            storage_base_path +
            "' couldn't be created as content base path.")
        return

    rejected_path = FILEHANDLING_CONFIG['rejected_path']
    if ensure_path_exists(rejected_path) is None:
        print(
            "ERROR: '" +
            rejected_path +
            "' couldn't be created for rejected files.")
        return

    filename = os.sep.join(
        source.rsplit(os.sep, 2)[-2:])
    # get user-id/filename from source path

    rejected_filepath_relative = os.path.join(
        rejected_path, filename)
    rejected_filepath = os.path.join(
        storage_base_path,
        rejected_filepath_relative)

    move_file(source, rejected_filepath)

    # TODO: cleanup possible preview and excerpt files

    # find content in database from filename
    slash_pos = filename.find(os.sep)
    if slash_pos > 0:
        matching_content = trytonAccess.get_content_by_filename(
            filename[slash_pos+1:])
    else:
        matching_content = trytonAccess.get_content_by_filename(filename)
    if matching_content is None:
        # print(
        #    "ERROR: Couldn't find content entry for '" +
        #    rejected_filepath_relative +
        #    "' in database. But no problem: " +
        #    "I'm about to reject the file anyway...")
        pass
        return

    # check and update content processing status,
    # save some pydub metadata to database
    matching_content.processing_state = 'rejected'
    matching_content.processing_hostname = HOSTNAME
    matching_content.path = rejected_filepath_relative
    matching_content.rejection_reason = reason
    matching_content.rejection_reason_details = reason_details
    matching_content.save()


# --- Click Commands ---


@click.group()
def repro():
    """
    Repertoire Processor command line tool.
    """


@repro.command('preview')
# @click.pass_context
def preview():
    """
    Get files from uploaded_path and creates a low quality audio snippet of it.
    """
    directory_walker(
        preview_audiofile,
        (
            os.path.join(STORAGE_BASE_PATH,
                         FILEHANDLING_CONFIG['uploaded_path']),
            os.path.join(STORAGE_BASE_PATH,
                         FILEHANDLING_CONFIG['previewed_path'])
        )
    )


@repro.command('checksum')
# @click.pass_context
def checksum():
    """
    Get files from previewed_path and hash them.
    """
    directory_walker(
        checksum_audiofile, (
            os.path.join(STORAGE_BASE_PATH,
                         FILEHANDLING_CONFIG['previewed_path']),
            os.path.join(STORAGE_BASE_PATH,
                         FILEHANDLING_CONFIG['checksummed_path'])
        )
    )


@repro.command('fingerprint')
# @click.pass_context
def fingerprint():
    """
    Get files from checksummed_path and fingerprint them.
    """
    directory_walker(
        fingerprint_audiofile, (
            os.path.join(STORAGE_BASE_PATH,
                         FILEHANDLING_CONFIG['checksummed_path']),
            os.path.join(STORAGE_BASE_PATH,
                         FILEHANDLING_CONFIG['fingerprinted_path'])))


@repro.command('drop')
# @click.pass_context
def drop():
    """
    Get files from fingerprinted_path and 'drop' them for archiving.

    This command does nothing with the files
    and is rather a mere abstraction
    in case there will at some point
    be another processing step after fingerprint.
    """
    directory_walker(
        drop_audiofile, (
            os.path.join(STORAGE_BASE_PATH,
                         FILEHANDLING_CONFIG['fingerprinted_path']),
            os.path.join(STORAGE_BASE_PATH,
                         FILEHANDLING_CONFIG['dropped_path'])))


@repro.command('delete')
# @click.pass_context
def delete():
    """
    delete a fingerprint from the echoprint server
    """

    # utilizations = Model.get('creation.utilisation.imp')
    # result = utilizations.find(['title', "=", "999,999"])
    # if not result:
    #     sys.exit()
    # code = result.fingerprint

    url = ECHOPRINT_URL + "/delete"
    var_id = "track_id"
    track = "TRWIZHB123E858D912"

    query_request = requests.post(url, data={var_id: track}, verify=False)

    print("status code: " + str(query_request.status_code) + " -- " +
          query_request.reason)


@repro.command('all')
@click.pass_context
def all(ctx):
    """
    Apply all processing steps.

    Looks for new files to be previed after each processing step.
    """
    ctx.invoke(preview)
    ctx.invoke(checksum)
    ctx.invoke(preview)
    ctx.invoke(fingerprint)
    ctx.invoke(drop)
    ctx.invoke(preview)


@repro.command('loop')
@click.pass_context
def loop(ctx):
    """
    Apply all processing steps in an endless loop.
    """
    while True:
        ctx.invoke(all)
        time_to_wait_between_cycles = 10
        print(
            'Waiting for ' +
            str(time_to_wait_between_cycles) +
            'seconds...')
        time.sleep(time_to_wait_between_cycles)
        print('entering new processing cycle')


def connect_db():
    """
    get access to database
    """
    max_tries = 3
    tries = 0
    # As XMLRPC has no disconnect method (should be stateless), but leaves
    # a connection to postgres open, the postgres backend has to
    # disconnect them via pg_terminate_backend in order to be able to drop
    # the database (testing).
    # The proteus config on the other hand seems to cache some connection
    # data, as the first connection results in an unauthorized error, so
    # a second try has to be added.
    while tries < max_tries:
        SCHEMA = "https"
        if os.environ.get('ENVIRONMENT') in ['development', 'testing']:
            SCHEMA = "http"
        try:
            config.set_xmlrpc(
                SCHEMA + "://" +
                PROTEUS_CONFIG['user'] + ":" +
                PROTEUS_CONFIG['password'] +
                "@" + PROTEUS_CONFIG['host'] +
                ":" + PROTEUS_CONFIG['port'] +
                "/" + PROTEUS_CONFIG['database'] + "/"
            )
            break
        except Exception as e:
            tries += 1
            if tries == max_tries:
                exit(
                    "Database connection could not be established "
                    "(yet), skipping file processing ... %s" % e)
            time.sleep(1)


if __name__ == '__main__':

    # ensure storage path
    if ensure_path_exists(STORAGE_BASE_PATH) is None:
        print(
            "ERROR: '" +
            STORAGE_BASE_PATH +
            "' couldn't be created as storage base path.")

        exit()

    # connect db
    connect_db()

    # execute repro
    repro()
