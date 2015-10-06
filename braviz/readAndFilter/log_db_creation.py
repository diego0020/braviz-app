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

from braviz.readAndFilter.tabular_data import get_connection

__author__ = 'Profesor'


if __name__ == "__main__":
    print("This file is not meant to be executed")
    sys.exit(0)


def create_tables(conn=None):
    if conn is None:
        conn = get_connection()

    with conn:
        # sessions table
        q = """CREATE TABLE IF NOT EXISTS sessions (
        session_idx INTEGER PRIMARY KEY,
        start_date DATE,
        name TEXT,
        description TEXT
        );"""
        conn.execute(q)

        # events table
        q = """CREATE TABLE IF NOT EXISTS events (
        event_idx INTEGER PRIMARY KEY,
        event_date DATE,
        session_id INTEGER REFERENCES sessions(session_idx),
        event_text TEXT,
        event_state TEXT,
        event_screenshot BLOB,
        application INTEGER REFERENCES applications(app_idx),
        instance_id
        );"""
        conn.execute(q)

