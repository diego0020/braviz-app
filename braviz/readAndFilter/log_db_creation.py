##############################################################################
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
import sys

from braviz.readAndFilter.log_db import get_log_connection


if __name__ == "__main__":
    print("This file is not meant to be executed")
    sys.exit(0)


def create_tables(conn=None):
    if conn is None:
        conn = get_log_connection()

    with conn:
        # sessions table
        q = """CREATE TABLE IF NOT EXISTS sessions (
        session_id INTEGER PRIMARY KEY,
        start_date DATETIME,
        name TEXT,
        description TEXT,
        favorite BOOLEAN DEFAULT 0
        );"""
        conn.execute(q)

        # events table
        q = """CREATE TABLE IF NOT EXISTS events (
        event_id INTEGER PRIMARY KEY,
        event_date DATETIME,
        session_id INTEGER REFERENCES sessions(session_id),
        event_text TEXT,
        event_state TEXT,
        event_screenshot BLOB,
        application_name TEXT,
        instance_id,
        favorite BOOLEAN DEFAULT 0
        );"""
        conn.execute(q)

        # annotations table
        q = """CREATE TABLE IF NOT EXISTS annotations (
        event_id INTEGER REFERENCES events(event_id),
        annotation_date DATETIME,
        annotation TEXT
        );"""
        conn.execute(q)

