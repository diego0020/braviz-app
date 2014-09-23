from braviz.readAndFilter import tabular_data
import logging


__author__ = 'diego'


def verify_db_completeness():
    conn = tabular_data.get_connection()
    #user db
    if not check_tables(conn,("applications","scenarios","vars_scenarios","subj_samples")):
        from braviz.readAndFilter import user_data_db_creation
        user_data_db_creation.create_tables()
        user_data_db_creation.add_current_applications()

    if not check_application_names():
        from braviz.readAndFilter import user_data_db_creation
        user_data_db_creation.update_current_applications()

    #bundles db
    if not check_tables(conn,("fiber_bundles",)):
        from braviz.readAndFilter import bundles_db_creation
        bundles_db_creation.create_bundles_table()
        bundles_db_creation.add_named_bundes_to_table()

    #geom db
    if not check_tables(conn,("geom_rois","geom_spheres","geom_lines",)):
        from braviz.readAndFilter import geometry_db_creation
        geometry_db_creation.create_geom_rois_tables()
        geometry_db_creation.create_lines_table()
        geometry_db_creation.create_spheres_table()

def check_table(conn,table_name):
    q="SELECT count(*) FROM sqlite_master WHERE type='table' and name = ? "
    cur = conn.execute(q,(table_name,))
    res = cur.fetchone()[0]
    return res>0

def check_tables(conn,tables):
    import logging
    for t in tables:
        if not check_table(conn,t):
            logging.warning("Table %s not found"%t)
            return False
    return True

def check_application_names():
    pass

if __name__ == "__main__":
    from braviz.utilities import configure_console_logger
    configure_console_logger("check_db_integrity")
    verify_db_completeness()