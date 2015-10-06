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
from braviz.readAndFilter.tabular_data import get_connection

__author__ = 'Diego'


def create_geom_rois_tables(conn=None):
    """
    geom types
    0 : spheres
    1[0|1|2|3] : lines
        0 : Sagital
        1 : Coronal
        2 : Axial
        3 : Free
    coordiate systems
    0 : subject
    1 : Talairach
    2 : Dartel
    """
    q = """CREATE TABLE IF NOT EXISTS geom_rois (
    roi_id INTEGER PRIMARY KEY ,
    roi_name TEXT UNIQUE,
    roi_type INTEGER, -- 0 : sphere, 1? : line
    roi_desc TEXT,
    roi_coords INT -- 0:subject,1:Talairach,2:Dartel
    );"""
    if conn is None:
        conn = get_connection()
    conn.execute(q)
    conn.commit()


def create_spheres_table(conn=None):
    q = """CREATE TABLE IF NOT EXISTS geom_spheres (
    sphere_id INTEGER,
    subject REFERENCES subjects(subject),
    radius NUMERIC,
    ctr_x NUMERIC,
    ctr_y NUMERIC,
    ctr_z NUMERIC,
    PRIMARY KEY (sphere_id,subject)
    )
    """
    if conn is None:
        conn = get_connection()
    conn.execute(q)
    conn.commit()


def create_lines_table(conn=None):
    """
    Creates a table for storing measurement lines
    :return Nothing:
    """
    q = """CREATE TABLE IF NOT EXISTS geom_lines (
    line_id INTEGER,
    subject REFERENCES subjects(subject),
    p1_x NUMERIC,
    p1_y NUMERIC,
    p1_z NUMERIC,
    p2_x NUMERIC,
    p2_y NUMERIC,
    p2_z NUMERIC,
    length NUMERIC,
    PRIMARY KEY (line_id,subject)
    )
    """
    if conn is None:
        conn = get_connection()
    conn.execute(q)
    conn.commit()
    q = """CREATE INDEX IF NOT EXISTS
    line_lengths ON geom_lines (line_id,subject,length)
    """
    conn.execute(q)
    conn.commit()

if __name__ == "__main__":
    print("This module should never be excecuted")
