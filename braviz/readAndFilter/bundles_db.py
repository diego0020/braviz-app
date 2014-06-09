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

    data = buffer(cPickle.dumps(checkpoints,2))
    q="""INSERT OR FAIL INTO fiber_bundles (bundle_name, bundle_type, bundle_data) VALUES (?,?,?) """
    conn = get_connection()
    conn.execute(q,(bundle_name,btype,data))
    conn.commit()

def save_logic_bundle(bundle_name,logic_tree_dict):
    tree_blob = buffer(cPickle.dumps(logic_tree_dict,2))
    q = """INSERT OR FAIL INTO fiber_bundles (bundle_name, bundle_type, bundle_data) VALUES (?,10,?) """
    con = get_connection()
    con.execute(q,(bundle_name,tree_blob))
    con.commit()

def get_bundles_list(bundle_type=None):
    con = get_connection()
    if bundle_type is None:
        q = "SELECT bundle_name FROM fiber_bundles"
        cur = con.execute(q)
        res = list(map(lambda x: x[0],cur.fetchall()))
        return res
    else:
        q = "SELECT bundle_name FROM fiber_bundles WHERE bundle_type = ?"
        cur = con.execute(q,(bundle_type,))
        res = list(map(lambda x: x[0],cur.fetchall()))
        return res

def get_logic_bundle_dict(bundle_id = None,bundle_name = None):
    con = get_connection()
    if bundle_id is None:
        q = "SELECT bundle_data FROM fiber_bundles WHERE bundle_name = ?"
        cur = con.execute(q,(bundle_name,))
    else:
        q = "SELECT bundle_data FROM fiber_bundles WHERE bundle_id = ?"
        cur = con.execute(q,(bundle_id,))
    r1 = cur.fetchone()
    if r1 is None:
        raise Exception("Fiber doesn't exist")
    data_buf = r1[0]
    data_dict = cPickle.loads(str(data_buf))
    return data_dict
