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
from braviz.readAndFilter.tabular_data import get_connection
import datetime
import os
import json

_date_format = "%d-%m-%Y %H-%M"
_active_session = None

def start_session(session_name = None):
    global _active_session
    now = datetime.datetime.now()
    if session_name is None:
        session_name = "%s session"%(now.strftime(_date_format))
    q = """INSERT  OR ABORT INTO sessions (start_date, name)
            VALUES ( ?, ? )"""
    conn = get_connection()
    with conn:
        cur = conn.execute(
            q,(now,session_name))
        res = cur.lastrowid
        _active_session = res
    return res

def set_session_description(session_idx, description):
    conn = get_connection()
    q = """UPDATE OR ABORT sessions set description = ? WHERE session_idx = ?"""
    with conn:
        cur = conn.execute(
            q,(session_idx,description))

def set_session_name(session_idx, name):
    conn = get_connection()
    q = """UPDATE OR ABORT sessions set name = ? WHERE session_idx = ?"""
    with conn:
        cur = conn.execute(
            q,(session_idx,name))

def add_event(application_script, instance_id, event_text, state=None, screenshot=None ):

    q = """INSERT  OR ABORT INTO events (event_date, session_id, event_text, event_state,
          event_screenshot, application, instance_id)
            VALUES ( ?, ?, ?, ?, ?, (SELECT app_idx FROM applications WHERE exec_name = ?)
            ,?)"""

    if _active_session is None:
        start_session()

    if state is not None and not isinstance(state,basestring):
        state = json.dumps(state)
    now = datetime.datetime.now()
    normal_exec_name = os.path.basename(application_script).split(".")[0]

    conn = get_connection()
    with conn:
        cur = conn.execute(
            q,(now,_active_session, event_text, state, screenshot, normal_exec_name,instance_id ))
