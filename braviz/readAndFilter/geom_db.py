from __future__ import division
from braviz.readAndFilter.tabular_data import _get_connection
import numpy as np
from pandas.io import sql

__author__ = 'Diego'

_ROI_TYPES_I = {
    "sphere": 0,
    "line_sagital": 10,
    "line_coronal": 11,
    "line_axial": 12,
    "line_free": 13,
}

_ROI_TYPES = {
    0: "sphere",
    10: "line_sagital",
    11: "line_coronal",
    12: "line_axial",
    13: "line_free",
}


_COORDINATES_I = {
    "world": 0,
    "talairach": 1,
    "dartel": 2,
}

_COORDINATES = {
    0: "world",
    1: "talairach",
    2: "dartel",
    }


def roi_name_exists(name):
    """
    Check if a roi with the given name exists

    Args:
        name (str) : Roi name

    Returns:
        ``True`` if a roi with the given name exists in the database, ``False`` otherwise.
    """
    con = _get_connection()
    cur = con.execute("SELECT count(*) FROM geom_rois WHERE roi_name = ?", (name,))
    n = cur.fetchone()[0]
    return n > 0


def create_roi(name, roi_type, coords, desc=""):
    """
    Creates a new roi

    Args:
        name (str) : Roi Name
        roi_type (str) : Roi type, current options are

            - sphere
            - line_sagital
            - line_coronal
            - line_axial
            - line_free

        coords (str) : coordinate system, options are

            - world
            - talairach
            - dartel

        desc (str) : Roi description

    Returns:
        Id of roi in the database

    """
    con = _get_connection()
    coords = coords.lower()
    coords_key = _COORDINATES_I[coords]
    roi_type_key = _ROI_TYPES_I[roi_type]
    q = "INSERT INTO geom_rois (roi_name,roi_type,roi_desc,roi_coords) VALUES(?,?,?,?)"
    cur = con.execute(q, (name, roi_type_key, desc, coords_key))
    con.commit()
    return cur.lastrowid


def get_available_spheres_df():
    """
    Get available spheres

    Returns:
        :class:`~pandas.DataFrame` with columns for sphere id, and number of subjects with the roi defined; indexed
        by name
    """
    con = _get_connection()
    q = """
        SELECT roi_name as name, roi_desc as description, num as quantity
        FROM geom_rois JOIN
        (SELECT sphere_id, count(*) as num FROM geom_spheres group by sphere_id
        UNION
        SELECT roi_id as sphere_id, 0 as num FROM geom_rois WHERE sphere_id not in (select sphere_id FROM geom_spheres)
        )
        ON roi_id = sphere_id
        WHERE roi_type = 0
        """
    df = sql.read_sql(q, con, index_col="name")
    return df


def get_available_lines_df():
    """
    Get available lines

    Returns:
        :class:`~pandas.DataFrame` with columns for line id, and number of subjects with the roi defined; indexed
        by name
    """
    con = _get_connection()
    q = """
        SELECT roi_name as name, roi_desc as description, num as quantity
        FROM geom_rois JOIN
        (SELECT line_id, count(*) as num FROM geom_lines group by line_id
        UNION
        SELECT roi_id as line_id, 0 as num FROM geom_rois WHERE line_id not in (select line_id FROM geom_lines)
        )
        ON roi_id = line_id
        WHERE roi_type >= 10 and roi_type < 20
        """
    df = sql.read_sql(q, con, index_col="name")
    return df


def get_roi_space(name=None, roi_id=None):
    """
    Retrieve the coordinate systems of a Roi

    Only one of the two arguments is required, roi_id is preferred

    Args:
        name (str) : Roi name
        roi_id (int) : Roi id

    Returns:
        coordinate system as a string, see :func:`create_roi` for options
    """
    con = _get_connection()

    if roi_id is None:
        q = "SELECT roi_coords FROM geom_rois WHERE roi_name = ?"
        cur = con.execute(q, (name,))
        idx = cur.fetchone()[0]
    else:
        q = "SELECT roi_coords FROM geom_rois WHERE roi_id = ?"
        cur = con.execute(q, (roi_id,))
        idx = cur.fetchone()[0]
    return _COORDINATES[idx]


def get_roi_id(roi_name):
    """
    Find the id of a Roi

    Args:
        roi_name (str) :  Roi Name

    Returns:
        Roi id in the database
    """
    con = _get_connection()
    q = "SELECT roi_id FROM geom_rois WHERE roi_name = ?"
    cur = con.execute(q, (roi_name,))
    idx = cur.fetchone()[0]
    return idx


def get_roi_name(roi_id):
    """
    Find the name of a roi

    Args:
        roi_id (int) : Roi id

    Returns:
        roi name
    """
    con = _get_connection()
    q = "SELECT roi_name FROM geom_rois WHERE roi_id = ?"
    cur = con.execute(q, (roi_id,))
    name = cur.fetchone()[0]
    return name


def get_roi_type(name=None, roi_id=None):
    """
    Get the type of a roi

    Only one of the two arguments is required, roi_id is preferred

    Args:
        name (str) : Roi name
        roi_id (int) : Roi id

    Returns:
        roi type as a string, see :func:`create_roi` for options
    """
    con = _get_connection()
    if roi_id is None:
        q = "SELECT roi_type FROM geom_rois WHERE roi_name = ?"
        cur = con.execute(q, (name,))
        roi_type_key = cur.fetchone()[0]
    else:
        q = "SELECT roi_type FROM geom_rois WHERE roi_id = ?"
        cur = con.execute(q, (roi_id,))
        roi_type_key = cur.fetchone()[0]
    return _ROI_TYPES[roi_type_key]


def subjects_with_sphere(sphere_id):
    """
    Get subjects who have a certain sphere defined

    Args:
        sphere_id (int) :  Roi id

    Returns:
        A set of subjects with the sphere defined
    """
    con = _get_connection()
    q = "SELECT subject FROM geom_spheres WHERE sphere_id = ?"
    cur = con.execute(q, (sphere_id,))
    rows = cur.fetchall()
    subjs = set(r[0] for r in rows)
    return subjs


def subjects_with_line(line_id):
    """
    Get subjects who have a certain line defined

    Args:
        sphere_id (int) :  Roi id

    Returns:
        A set of subjects with the line defined
    """
    con = _get_connection()
    q = "SELECT subject FROM geom_lines WHERE line_id = ?"
    cur = con.execute(q, (line_id,))
    rows = cur.fetchall()
    subjs = set(r[0] for r in rows)
    return subjs


def save_sphere(sphere_id, subject, radius, center):
    """
    Save a sphere for a given subject into the database

    Args:
        sphere_id (int) : Roi id
        subject  : subject id
        radius (float) : sphere radius in mm.
        center (tuple) : The three coordinates for the sphere center in mm.
    """
    x, y, z = center
    con = _get_connection()
    q = "INSERT OR REPLACE INTO geom_spheres VALUES (?,?,?,?,?,?)"
    con.execute(q, (sphere_id, subject, radius, x, y, z))
    con.commit()


def load_sphere(sphere_id, subject):
    """
    Loads a sphere for a subject

    Args:
        sphere_id (int) :  Roi  id
        subject : subject id

    Returns:
        ``(r,x,y,z)`` where r is the radius of the sphere and (x,y,z) is its center.
    """
    q = "SELECT radius,ctr_x,ctr_y,ctr_z FROM geom_spheres WHERE sphere_id = ? and subject = ?"
    con = _get_connection()
    cur = con.execute(q, (int(sphere_id), int(subject)))
    res = cur.fetchone()
    return res


def get_all_spheres(sphere_id):
    """
    Get a DataFrame of all the subjects spheres with a given id

    Args:
        sphere_id (int) :  Roi id

    Returns:
        :class:`pandas.DataFrame` with columns for radius, center x, center y and center z; indexed by subject
    """
    q = "SELECT subject,radius,ctr_x,ctr_y,ctr_z FROM geom_spheres WHERE sphere_id = ?"
    con = _get_connection()
    df = sql.read_sql(q, con, index_col="subject", params=(sphere_id,))
    return df


def save_line(line_id, subject, point1, point2):
    """
    Save a line from a given subject into the database

    Args:
        line_id (int) :  Roi id
        subject : subject id
        point1 (tuple) : coordinates (xo,yo,zo) of the line origin
        point2 (tuple) : coordinates (xf,yf,zf) of the line end
    """
    p1 = np.array(point1)
    p2 = np.array(point2)
    length = np.linalg.norm(p1 - p2)

    q = "INSERT OR REPLACE INTO geom_lines VALUES (?,?, ?,?,?, ?,?,?, ?)"
    con = _get_connection()
    con.execute(q, (line_id, subject, p1[0], p1[1], p1[2], p2[0], p2[1], p2[2], length))
    con.commit()


def load_line(line_id, subject):
    """
    Retrieves a line for a given subject

    Args:
        line_id (int) : Roi id
        subject : subject id

    Returns
        ``(xo,yo,zo,xf,yf,zf)`` where (xo,yo,zo) is the line origin and (xf,yf,zf) is the end.
    """
    q = "SELECT p1_x,p1_y,p1_z,p2_x,p2_y,p2_z FROM geom_lines WHERE line_id = ? and subject = ?"
    con = _get_connection()
    cur = con.execute(q, (int(line_id), int(subject)))
    res = cur.fetchone()
    return res


def copy_spheres(orig_id, dest_id):
    """
    Copies spheres from one roi to another

    Copies the definitions of spheres for each subject from one roi to another roi

    Args:
        origi_id (int) : roi id of the source spheres
        dest_id (int) : roi id into which the spheres will be copied
    """
    q = """INSERT OR REPLACE INTO geom_spheres
    SELECT ? as sphere_id , subject, radius, ctr_x, ctr_y, ctr_z
    FROM geom_spheres
    WHERE sphere_id = ?"""
    con = _get_connection()
    con.execute(q, (dest_id, orig_id))
    con.commit()