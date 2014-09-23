__author__ = 'Diego'

import sys

from braviz.readAndFilter.tabular_data import get_connection

if __name__ == "__main__":
    print "This file is not meant to be executed"
    sys.exit(0)


def create_tables():
    conn = get_connection()

    #applications table
    q = """CREATE TABLE IF NOT EXISTS applications (
    app_idx INTEGER PRIMARY KEY,
    exec_name TEXT
    );"""

    conn.execute(q)
    conn.commit()

    #scenarios table
    q = """CREATE TABLE IF NOT EXISTS scenarios (
    scn_id INTEGER PRIMARY KEY,
    app_idx INTEGER REFERENCES applications(app_idx),
    scn_name TEXT,
    scn_date  DATETIME DEFAULT CURRENT_TIMESTAMP,
    scn_desc TEXT,
    scn_data BLOB
    );
    """

    conn.execute(q)
    conn.commit()

    #variables and scenarios table
    q = """
    CREATE TABLE IF NOT EXISTS vars_scenarios (
    var_idx INTEGER REFERENCES variables(var_idx),
    scn_id INTEGER REFERENCES scenarios(scn_id)
    );
    """

    conn.execute(q)
    conn.commit()

    q = """
    CREATE TABLE IF NOT EXISTS subj_samples (
    sample_idx INTEGER PRIMARY KEY,
    sample_name TEXT,
    sample_desc TEXT,
    sample_data BLOB,
    sample_size INTEGER
    );
    """

    conn.execute(q)
    conn.commit()

    q = """
    CREATE TABLE IF NOT EXISTS subj_comments (
    subject INTEGER PRIMARY KEY,
    comment TEXT
    );
    """

    conn.execute(q)
    conn.commit()


def update_current_applications():
    applications = {
        1: "subject_overview",
        2: "anova_task",
        3: "sample_overview",
        4: "lm_task",
        5: "logic_bundles",
        6: "build_roi",
        7: "fmri_explorer",
        8: "measure_task",
        }
    conn = get_connection()
    q = "SELECT app_idx, exec_name FROM applications ORDER BY app_idx"
    cur = conn.execute(q)
    db_tuples = cur.fetchall()
    db_dict=dict(db_tuples)
    add_q = "INSERT INTO applications VALUES (?,?)"
    update_q = "UPDATE OR ABORT applications SET exec_name = ? WHERE app_idx = ?"
    with conn:
        for k,v in applications.iteritems():
            v2 = db_dict.get(k)
            if v2 is None:
                conn.execute(add_q,(k,v))
            elif (str(v) != str(v2)):
                conn.execute(update_q,(v,k))

