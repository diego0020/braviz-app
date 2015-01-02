__author__ = 'Diego'

import braviz
from braviz.readAndFilter.tabular_data import _get_connection


def create_bundles_table():
    """Tract bundle types:
    0 : Named tracts, refer to python functions and are accessed via the reader.get interface, data contains 'name' argument
    1 : Checkpoint tracts where the operation is 'and', data contains the pickled list of checkpoints
    2 : Checkpoint tracts where the operation is 'or', data contains the pickled list of checkpoints
    10: Logic bundles,
    """
    q="""CREATE TABLE IF NOT EXISTS fiber_bundles (
    bundle_id INTEGER PRIMARY KEY ,
    bundle_name TEXT UNIQUE,
    bundle_type INTEGER,
    bundle_data TEXT
    );"""
    conn=_get_connection()
    conn.execute(q)
    conn.commit()


def add_named_bundes_to_table():
    reader = braviz.readAndFilter.BravizAutoReader()
    named_tracts = reader.get("FIBERS",None,index=True)
    print named_tracts
    conn=_get_connection()
    tuples=( (name,0,name) for name in named_tracts)
    q = """INSERT INTO fiber_bundles (bundle_name, bundle_type, bundle_data) VALUES (?,?,?);"""
    conn.executemany(q,tuples)
    conn.commit()

if __name__ == "__main__":
    print "This module should never be excecuted"