from braviz.readAndFilter.tabular_data import get_connection
__author__ = 'Diego'

def add_variable(father_id,pretty_name,tab_var_id=None):
    father_level = get_var_level(father_id)
    if father_level is None:
        var_level = 1
    else:
        var_level = father_level+1
    q = """
    INSERT INTO braint_var (label,father,level)
    VALUES
    (?,?,?)
    """
    conn = get_connection()
    cur = conn.execute(q,(pretty_name,father_id,var_level))
    conn.commit()
    row_id = cur.lastrowid
    if tab_var_id is not None:
        q2 = "INSERTO into braint_tab VALUES (?,?)"
        conn.execute(q2,(row_id,tab_var_id))
        conn.commit()
    return row_id

def get_var_level(var_id):
    conn = get_connection()
    q="SELECT level FROM braint_var WHERE var_id = ?"
    cur = conn.execute(q,(var_id,))
    ans = cur.fetchone()
    if ans is not None:
        return ans[0]
    else:
        return None

def get_all_variables():
    conn = get_connection()
    q = "SELECT var_id,label,father FROM braint_var"
    cur = conn.execute(q)
    return list(cur.fetchall())

def delete_node_aux(conn,var_idx):
    pass
    #check there are no relations
    #TODO
    #delete kids
    kids = get_sons(var_idx)
    for k in kids:
        delete_node_aux(conn,k)
    #delete from braint_tab
    q="DELETE FROM braint_tab WHERE braint_var_id = ?"
    conn.execute(q,(var_idx,))
    #delete me
    q="DELETE FROM braint_var WHERE var_id = ?"
    conn.execute(q,(var_idx,))


def delete_node(var_idx):
    conn = get_connection()

    delete_node_aux(conn,var_idx)
    conn.commit()




def get_sons(var_idx,recursive=False):
    if recursive is True:
        raise NotImplementedError
    conn = get_connection()
    q = "SELECT var_id FROM braint_var WHERE father = ?"
    cur = conn.execute(q,(var_idx,))
    ans = [x[0] for x in cur.fetchall()]
    return ans

def get_var_parent(var_idx):
    conn = get_connection()
    q="select father FROM braint_var WHERE var_id = ?"
    cur = conn.execute(q,(var_idx,))
    ans = cur.fetchone()
    if ans is not None:
        return ans[0]
    return None


