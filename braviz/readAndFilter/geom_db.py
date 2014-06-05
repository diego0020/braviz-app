from __future__ import division
from braviz.readAndFilter.tabular_data import get_connection
from pandas.io import sql

__author__ = 'Diego'


def roi_name_exists(name):
    con = get_connection()
    cur = con.execute("SELECT count(*) FROM geom_rois WHERE roi_name = ?", (name,))
    n = cur.fetchone()[0]
    return n > 0


def create_roi(name, roi_type, coords, desc=""):
    con = get_connection()
    assert coords in {0, 1, 2}
    q = "INSERT INTO geom_rois (roi_name,roi_type,roi_desc,roi_coords) VALUES(?,?,?,?)"
    cur = con.execute(q, (name, roi_type, desc, coords))
    con.commit()
    return cur.lastrowid


def get_available_spheres_df():
    con = get_connection()
    q = """
        SELECT roi_name as name, roi_desc as description, num as number
        FROM geom_rois JOIN
        (SELECT sphere_id, count(*) as num FROM geom_spheres group by sphere_id
        UNION
        SELECT roi_id as sphere_id, 0 as num FROM geom_rois WHERE sphere_id not in (select roi_id FROM geom_spheres)
        )
        ON roi_id = sphere_id
        WHERE roi_type = 0
        """
    df = sql.read_sql(q, con, index_col="name")
    return df


COORDS = {0: "World", 1: "Talairach", 2: "Dartel"}


def get_roi_space(name=None, roi_id=None):
    con = get_connection()

    if roi_id is None:
        q = "SELECT roi_coords FROM geom_rois WHERE roi_name = ?"
        cur = con.execute(q, (name,))
        idx = cur.fetchone()[0]
    else:
        q = "SELECT roi_coords FROM geom_rois WHERE roi_id = ?"
        cur = con.execute(q, (roi_id,))
        idx = cur.fetchone()[0]
    return COORDS[idx]

def get_roi_id(roi_name):
    con = get_connection()
    q = "SELECT roi_id FROM geom_rois WHERE roi_name = ?"
    cur = con.execute(q, (roi_name,))
    idx = cur.fetchone()[0]
    return idx


def subjects_with_sphere(sphere_id):
    con = get_connection()
    q = "SELECT subject FROM geom_spheres WHERE sphere_id = ?"
    cur = con.execute(q, (sphere_id,))
    rows = cur.fetchall()
    subjs = set(r[0] for r in rows)
    return subjs