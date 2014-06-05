
from braviz.readAndFilter.tabular_data import get_connection

__author__ = 'Diego'

def _create_geom_rois_tables():
    """
    geom types
    0 : spheres

    coordiate systems
    0 : World
    1 : Talairach
    2 : Dartel
    """
    q="""CREATE TABLE IF NOT EXISTS geom_rois (
    roi_id INTEGER PRIMARY KEY ,
    roi_name TEXT UNIQUE,
    roi_type INTEGER, -- 0 : sphere
    roi_desc TEXT,
    roi_coords INT -- 0:World,1:Talairach,2:Dartel
    );"""
    conn=get_connection()
    conn.execute(q)
    conn.commit()

def _create_spheres_table():
    q="""CREATE TABLE IF NOT EXISTS geom_spheres (
    sphere_id INTEGER,
    subject REFERENCES subjects(subject),
    radius NUMERIC,
    ctr_x NUMERIC,
    ctr_y NUMERIC,
    ctr_z NUMERIC,
    PRIMARY KEY (sphere_id,radius)
    )
    """
    conn=get_connection()
    conn.execute(q)
    conn.commit()

if __name__ == "__main__":
    print "This module should never be excecuted"