__author__ = 'Diego'

import cPickle

from braviz.readAndFilter.tabular_data import get_connection


def get_bundle_ids_and_names():
    conn = get_connection()
    q="SELECT bundle_id, bundle_name FROM fiber_bundles"
    cur=conn.execute(q)
    return cur.fetchall()


def get_bundle_details(bundle_id):
    conn = get_connection()
    q="SELECT bundle_name, bundle_type, bundle_data FROM fiber_bundles WHERE bundle_id = ?"
    cur=conn.execute(q,(bundle_id,))
    res = cur.fetchone()
    return res

def get_bundle_name(bundle_id):
    conn = get_connection()
    q="SELECT bundle_name FROM fiber_bundles WHERE bundle_id = ?"
    cur=conn.execute(q,(bundle_id,))
    res = cur.fetchone()
    return res[0]

def check_if_name_exists(name):
    conn = get_connection()
    q="SELECT * FROM fiber_bundles WHERE bundle_name = ?"
    cur=conn.execute(q,(name,))
    res = cur.fetchone()
    return res is not None

def save_checkpoints_bundle(bundle_name,operation_is_and,checkpoints):
    checkpoints=tuple(checkpoints)
    if operation_is_and is True:
        btype=1
    else:
        btype=2

    data = cPickle.dumps(checkpoints)
    q="""INSERT OR FAIL INTO fiber_bundles (bundle_name, bundle_type, bundle_data) VALUES (?,?,?) """
    conn = get_connection()
    conn.execute(q,(bundle_name,btype,data))
    conn.commit()

