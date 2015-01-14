##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################

"""
Checks completeness of the braviz database
"""

__author__ = 'diego'

from braviz.readAndFilter import tabular_data

import logging


def verify_db_completeness():
    """
    Verifies that all tables exist in the braviz data base.
    If any are missing they are constructed.
    """
    conn = tabular_data._get_connection()
    #user db
    from braviz.readAndFilter import user_data_db_creation

    if not _check_tables(conn,("applications","scenarios","vars_scenarios","subj_samples","subj_comments")):
        user_data_db_creation.create_tables()
    user_data_db_creation.update_current_applications()

    #bundles db
    if not _check_tables(conn,("fiber_bundles",)):
        from braviz.readAndFilter import bundles_db_creation
        bundles_db_creation.create_bundles_table()
        bundles_db_creation.add_named_bundes_to_table()

    #geom db
    if not _check_tables(conn,("geom_rois","geom_spheres","geom_lines",)):
        from braviz.readAndFilter import geometry_db_creation
        geometry_db_creation.create_geom_rois_tables()
        geometry_db_creation.create_lines_table()
        geometry_db_creation.create_spheres_table()

def _check_table(conn,table_name):
    q="SELECT count(*) FROM sqlite_master WHERE type='table' and name = ? "
    cur = conn.execute(q,(table_name,))
    res = cur.fetchone()[0]
    return res>0

def _check_tables(conn,tables):
    import logging
    for t in tables:
        if not _check_table(conn,t):
            logging.warning("Table %s not found"%t)
            return False
    return True


if __name__ == "__main__":
    from braviz.utilities import configure_logger_from_conf
    configure_logger_from_conf("check_db_integrity")
    verify_db_completeness()