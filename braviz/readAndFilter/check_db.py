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


"""
Checks completeness of the braviz database
"""

__author__ = 'diego'

from braviz.readAndFilter import tabular_data

import logging
import sqlite3


def verify_db_completeness(database_file=None):
    """
    Verifies that all tables exist in the braviz data base.
    If any are missing they are constructed.

    Args:
        database_file (str) : Path of the database file that should be ckecked, if None, the database defined
            by the configuration file will be used.
    """
    if database_file is None:
        conn = tabular_data._get_connection()
    else:
        conn = sqlite3.connect(database_file)

    # tabular data
    from braviz.readAndFilter import tabular_data_db_creation
    if not _check_tables(conn, ("variables", "subjects", "var_descriptions", "var_values", "nom_meta", "ratio_meta")):
        tabular_data_db_creation.create_data_base(conn=conn)

    # user db
    from braviz.readAndFilter import user_data_db_creation

    if not _check_tables(conn, ("applications", "scenarios", "vars_scenarios", "subj_samples", "subj_comments",)):
        user_data_db_creation.create_tables(conn)
    user_data_db_creation.update_current_applications(conn)

    # bundles db
    if not _check_tables(conn, ("fiber_bundles",)):
        from braviz.readAndFilter import bundles_db_creation
        bundles_db_creation.create_bundles_table(conn)
        bundles_db_creation.add_named_bundes_to_table(conn)
    _check_named_tracts(conn)

    # geom db
    if not _check_tables(conn, ("geom_rois", "geom_spheres", "geom_lines",)):
        from braviz.readAndFilter import geometry_db_creation
        geometry_db_creation.create_geom_rois_tables(conn)
        geometry_db_creation.create_lines_table(conn)
        geometry_db_creation.create_spheres_table(conn)


def _check_table(conn, table_name):
    q = "SELECT count(*) FROM sqlite_master WHERE type='table' and name = ? "
    cur = conn.execute(q, (table_name,))
    res = cur.fetchone()[0]
    return res > 0


def _check_named_tracts(conn):
    import braviz.readAndFilter
    r = braviz.readAndFilter.BravizAutoReader()
    named_tracts = r.get("FIBERS", None, index=True)
    existing_tracts = {b[0] for b in conn.execute(
        "SELECT bundle_name FROM fiber_bundles").fetchall()}
    for n in named_tracts:
        if not n in existing_tracts:
            q = """INSERT INTO fiber_bundles (bundle_name, bundle_type, bundle_data) VALUES (?, 0, ?) """
            with conn:
                conn.execute(q, (n, n))


def _check_tables(conn, tables):
    import logging
    for t in tables:
        if not _check_table(conn, t):
            logging.warning("Table %s not found" % t)
            return False
    return True


if __name__ == "__main__":
    from braviz.utilities import configure_logger_from_conf
    configure_logger_from_conf("check_db_integrity")
    verify_db_completeness()
