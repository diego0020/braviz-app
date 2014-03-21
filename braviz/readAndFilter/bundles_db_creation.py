__author__ = 'Diego'

import braviz
from braviz.readAndFilter.tabular_data import get_connection

def __create_bundles_table():
    """Tract bundle types:
    0 : Named tracts, refer to python functions and are accessed via the reader.get interface, data contains 'name' argument
    1 : Checkpoint tracts where the operation is 'and', data contains the pickled list of checkpoints
    2 : Checkpoint tracts where the operation is 'or', data contains the pickled list of checkpoints
    """
    q="""CREATE TABLE IF NOT EXISTS fiber_bundles (
    bundle_id INTEGER PRIMARY KEY ,
    bundle_name TEXT UNIQUE,
    bundle_type INTEGER,
    bundle_data TEXT
    );"""
    conn=get_connection()
    conn.execute(q)
    conn.commit()


def __add_named_bundes_to_table():
    reader = braviz.readAndFilter.kmc40AutoReader()
    named_tracts = reader.get("FIBERS","093",index=True)
    print named_tracts
    conn=get_connection()
    tuples=( (name,0,name) for name in named_tracts)
    q = """INSERT INTO fiber_bundles (bundle_name, bundle_type, bundle_data) VALUES (?,?,?);"""
    conn.executemany(q,tuples)
    conn.commit()

