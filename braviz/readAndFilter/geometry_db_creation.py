

from braviz.readAndFilter.tabular_data import _get_connection

__author__ = 'Diego'

def create_geom_rois_tables():
    """
    geom types
    0 : spheres
    1[0|1|2|3] : lines
        0 : Sagital
        1 : Coronal
        2 : Axial
        3 : Free
    coordiate systems
    0 : World
    1 : Talairach
    2 : Dartel
    """
    q="""CREATE TABLE IF NOT EXISTS geom_rois (
    roi_id INTEGER PRIMARY KEY ,
    roi_name TEXT UNIQUE,
    roi_type INTEGER, -- 0 : sphere, 1? : line
    roi_desc TEXT,
    roi_coords INT -- 0:World,1:Talairach,2:Dartel
    );"""
    conn=_get_connection()
    conn.execute(q)
    conn.commit()

def create_spheres_table():
    q="""CREATE TABLE IF NOT EXISTS geom_spheres (
    sphere_id INTEGER,
    subject REFERENCES subjects(subject),
    radius NUMERIC,
    ctr_x NUMERIC,
    ctr_y NUMERIC,
    ctr_z NUMERIC,
    PRIMARY KEY (sphere_id,subject)
    )
    """
    conn=_get_connection()
    conn.execute(q)
    conn.commit()

def create_lines_table():
    """
    Creates a table for storing measurement lines
    :return Nothing:
    """
    q="""CREATE TABLE IF NOT EXISTS geom_lines (
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
    conn=_get_connection()
    conn.execute(q)
    conn.commit()
    q="""CREATE INDEX IF NOT EXISTS
    line_lengths ON geom_lines (line_id,subject,length)
    """
    conn.execute(q)
    conn.commit()

if __name__ == "__main__":
    print "This module should never be excecuted"

