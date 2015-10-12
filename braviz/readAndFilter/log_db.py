# #############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


from __future__ import print_function
import sqlite3
import datetime
import os
import json
import threading
from collections import namedtuple

import braviz.readAndFilter

_pretty_date_format = "%d-%m-%Y %I:%M %p"
_db_date_format = "%Y-%m-%d %H:%M:%S.%f"

_log_connections = {}


def get_log_connection():
    """
    Gets the sqlite3 connection object for this thread.

    Notice that for performance reason only the log concentrator should access this database for writing.
    The only exception should be starting a new session before the concentrator is launched. Also the web
    client may access this database for reading and writing metadata.
    """
    global _log_connections

    thread_id = threading.current_thread()
    connection_obj = _log_connections.get(thread_id)
    if connection_obj is not None:
        return connection_obj

    data_root = braviz.readAndFilter.braviz_auto_dynamic_data_root()
    path = os.path.join(data_root, "braviz_data", "log_db.sqlite")

    conn = sqlite3.connect(path,  detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("pragma busy_timeout = 10000")
    _log_connections[thread_id] = conn
    return conn

def start_session(session_name=None):
    now = datetime.datetime.now()
    if session_name is None:
        session_name = "%s session" % (now.strftime(_pretty_date_format))
    q = """INSERT  OR ABORT INTO sessions (start_date, name)
            VALUES ( ?, ? )"""
    conn = get_log_connection()
    with conn:
        cur = conn.execute(
            q, (now, session_name))
        res = cur.lastrowid
    return res


def set_session_description(session_id, description):
    conn = get_log_connection()
    q = """UPDATE OR ABORT sessions SET description = ? WHERE session_id = ?"""
    with conn:
        cur = conn.execute(
            q, (description, session_id))


def set_session_name(session_idx, name):
    conn = get_log_connection()
    q = """UPDATE OR ABORT sessions SET name = ? WHERE session_id = ?"""
    with conn:
         conn.execute( q, (name, session_idx))

def set_session_favorite(session_id, favorite):
    conn = get_log_connection()
    q = """UPDATE OR ABORT sessions SET favorite = ? WHERE session_id = ?"""
    fav=bool(favorite)
    with conn:
        cur = conn.execute(
            q, (fav, session_id))

def get_active_session():
    q = "SELECT session_id FROM sessions ORDER BY start_date desc LIMIT 1"
    conn = get_log_connection()
    ac=conn.execute(q).fetchone()
    if ac is not None:
        ac = ac[0]
    return ac

def add_event(application_script, instance_id, event_text, state=None, screenshot=None):
    q = """INSERT  OR ABORT INTO events (event_date, session_id, event_text, event_state,
          event_screenshot, application_name, instance_id)
            VALUES ( ?,
              (SELECT session_id FROM sessions ORDER BY start_date desc LIMIT 1),
             ?, ?, ?,
              ?
            ,?)"""
    if state is not None and not isinstance(state, basestring):
        state = json.dumps(state)
    now = datetime.datetime.now()
    normal_exec_name = os.path.basename(application_script).split(".")[0]

    conn = get_log_connection()
    with conn:
        cur = conn.execute(
            q, (now, event_text, state, screenshot, normal_exec_name, instance_id))


session_factory = namedtuple("Session", ["index", "name", "description", "start_date", "end_date", "duration","favorite"])


def get_sessions():
    q = """SELECT sessions.session_id, name, description, start_date, last_date, favorite
           FROM sessions LEFT JOIN
              (SELECT session_id, max(event_date) AS last_date
                FROM  events GROUP BY  session_id
              ) AS end_dates
           ON (sessions.session_id = end_dates.session_id)
           ORDER BY start_date DESC
           """

    def format_tuple(t):
        # unpack
        index, name, description, start_date, end_date, favorite = t
        start_date = datetime.datetime.strptime(start_date, _db_date_format)
        if end_date is not None:
            end_date = datetime.datetime.strptime(end_date, _db_date_format)
        else:
            end_date = start_date
        duration = end_date - start_date
        if name is None: name = ""
        if description is None: description = ""
        return session_factory(index, name, description, start_date, end_date, duration, favorite)

    conn = get_log_connection()
    sessions = [format_tuple(t) for t in conn.execute(q).fetchall()]
    return sessions


events_factory = namedtuple("Event", ["index", "date", "action", "screenshot_data", "application_name", "instance_id"])


def get_events(session_id):
    q = """SELECT  event_id, event_date, event_text, event_screenshot, application_name, instance_id
    FROM events
    WHERE session_id = ?
    ORDER BY event_date ASC
    """

    def format_event_tuple(t):
        event_idx, event_date, event_text, event_screenshot, application, instance_id = t
        event_date = datetime.datetime.strptime(event_date, _db_date_format)
        return events_factory(event_idx, event_date, event_text, event_screenshot, application, instance_id)

    conn = get_log_connection()
    sessions = [format_event_tuple(t) for t in conn.execute(q, (session_id,)).fetchall()]
    return sessions


def delete_session(session_id):
    # Delete events
    q1 = """
        DELETE FROM events WHERE session_id = ?
    """
    # Delete session
    q2 = """
        DELETE FROM sessions WHERE session_id = ?
    """
    conn = get_log_connection()
    with conn:
        conn.execute(q1, (session_id,))
        conn.execute(q2, (session_id,))
    return
