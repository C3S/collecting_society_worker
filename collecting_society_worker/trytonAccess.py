#!/usr/bin/env python
# For copyright and license terms, see COPYRIGHT.rst (top level of repository)
# Repository: https://github.com/C3S/collecting_society_worker

"""
The one and only C3S proteus tools for accessing data in C3S tryton db
"""


from proteus import config, Model


def connect(pconfig):
    """
    get access to tryton database for processing state updates
    use http only on local test instance (and uncomment [ssl] entries in
    server side trytond.conf for using http)
    """
    config.set_xmlrpc(
        "http://" + pconfig["user"] + ":" + pconfig["password"]
        + "@" + pconfig["host"] + ":" + pconfig["port"] + "/"
        + pconfig["database"]
    )


def get_content_by_filename(filename):
    """
    Get a content by filename/uuid.
    """
    if not filename:
        return
    Content = Model.get('content')
    matching_contents = Content.find(['uuid', "=", filename])
    if len(matching_contents) == 0:
        print("ERROR: Wasn't able to find content entry in the database "
              "for '" + filename + "'.")
        return None
    if len(matching_contents) > 1:
        # unlikely with uuids, but we are
        # supersticious...
        print("WARNING: More than one content entry in the database for '"
              + filename + "'. Using the first one.")
    return matching_contents[0]


def get_creation_by_content(content):
    """
    Get a creation by content(.id).
    """
    Creation = Model.get('creation')
    matching_creations = Creation.find(['id', "=", content.id])
    if len(matching_creations) == 0:
        print("ERROR: Wasn't able to find creation entry in the database "
              "with id '" + str(content.id) + "' for file '"
              + content.uuid + "'.")
        return None
    if len(matching_creations) > 1:
        print("WARNING: More than one content entry in the database for '"
              + content.uuid + "'. Using the first one.")
    return matching_creations[0]


def insert_content_by_filename(filename, user, pstate):
    """
    insert an example content by filename/uuid.
    """
    Content = Model.get('content')
    new_content = Content()
    new_content.id < 0
    new_content.uuid = filename
    new_content.user = user
    new_content.processing_state = pstate
    new_content.save()


def update_content_pstate(filename, pstate):
    """
    update content's state by filename/uuid.
    """
    upd_content = get_content_by_filename(filename)
    upd_content.processing_state = pstate
    upd_content.save()


def get_or_insert_web_user(email):
    """
    Finds a web user by email;
    if she doesn't exist, she will be created and returned
    """
    WebUser = Model.get('web.user')
    matching_user = WebUser.find(['email', "=", email])
    if len(matching_user) == 0:
        new_user = WebUser()
        new_user.email = email
        new_user.save()
        return new_user
    return matching_user[0]


def delete_web_user(email):
    """
    deletes webuser by email

    .. caution:: Not yet functional!
    """
    # TODO: delete
    # WebUser = Model.get('web.user')
    # matching_user = WebUser.find(['email', "=", email])
    pass


def delete_content(filename):
    """
    deletes a content (file) record of an uploaded file (.wav, .pdf)

    .. caution:: Not yet functional!
    """
    # TODO: delete
    # Content = Model.get('content')
    # matching_content = Content.find(['uuid', "=", filename])
    pass


def get_obj_state(filename):
    """
    returns the state of objects inherited from the state mixin
    """
    matching_content = get_content_by_filename(filename)
    return matching_content.processing_state


def set_content_unknown(filename):
    """
    sets a content record's processing_state to unknown
    """
    matching_content = get_content_by_filename(filename)
    matching_content.processing_state = "unknown"
    matching_content.save()
