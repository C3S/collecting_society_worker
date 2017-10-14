#!/usr/bin/python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: ...

"""
The one and only C3S proteus tools for accessing data in C3S tryton db
"""


import proteus


def connect(PROTEUS_CONFIG):
    proteus.config.set_xmlrpc(
        "http://" + PROTEUS_CONFIG['user'] + ":"
        + PROTEUS_CONFIG['password']
        + "@" + PROTEUS_CONFIG['host'] + ":"
        + PROTEUS_CONFIG['port'] + "/"
        + PROTEUS_CONFIG['database']
    )


def get_content_by_filename(filename):
    """
    Get a content by filename/uuid.
    """
    Content = proteus.Model.get('content')
    matching_contents = Content.find(['uuid', "=", filename])
    if len(matching_contents) == 0:
        print "ERROR: Wasn't able to find content entry in the database \
              for '" + filename + "'."
        return None
    if len(matching_contents) > 1:
        # unlikely with uuids, but we are
        # supersticious...
        print "WARNING: More than one content entry in the database for '" \
              + filename + "'. Using the first one."
    return matching_contents[0]


def get_creation_by_content(content):
    """
    Get a creation by content(.id).
    """
    Creation = Model.get('creation')
    matching_creations = Creation.find(['id', "=", content.id])
    if len(matching_creations) == 0:
        print "ERROR: Wasn't able to find creation entry in the database with id '" + \
              str(content.id) + "' for file '" + content.uuid + "'."
        return None
    if len(matching_creations) > 1:
        print "WARNING: More than one content entry in the database for '" + content.uuid + \
              "'. Using the first one."
    return matching_creations[0]


def insert_content_by_filename(filename, pstate):
    """
    insert an example content by filename/uuid.
    """
    Content = proteus.Model.get('content')
    new_content = Content()
    new_content.id < 0
    new_content.uuid = filename
    new_content.processing_state = pstate
    new_content.save()
 
def get_obj_state(filename):
    matching_content = get_content_by_filename(filename)
    return matching_content.processing_state


def set_content_unknown(filename):
    matching_content = get_content_by_filename(filename)
    matching_content.processing_state = "unknown"
    matching_content.save()
