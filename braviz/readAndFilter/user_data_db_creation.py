__author__ = 'Diego'

import sys

from braviz.readAndFilter.tabular_data import get_connection


if __name__ == "__main__":
    print "This file is not meant to be executed"
    sys.exit(0)

def create_tables():
    conn = get_connection()

    #applications table
    q="""CREATE TABLE IF NOT EXISTS applications (
    app_idx INTEGER PRIMARY KEY,
    exec_name TEXT
    );"""

    conn.execute(q)
    conn.commit()

    #scenarios table
    q="""CREATE TABLE IF NOT EXISTS scenarios (
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
    q="""
    CREATE TABLE IF NOT EXISTS vars_scenarios (
    var_idx INTEGER REFERENCES variables(var_idx),
    scn_id INTEGER REFERENCES scenarios(scn_id)
    );
    """

    conn.execute(q)
    conn.commit()


def add_current_applications():
    apps = ("subject_overview","anova","sample_overview")
    conn = get_connection()
    q="""INSERT OR IGNORE INTO applications (exec_name) VALUES (?) """
    tuples = ( (a,) for a in apps)
    conn.executemany(q,tuples)
    conn.commit()

