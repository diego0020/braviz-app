__author__ = 'Diego'

import sqlite3
from itertools import izip,repeat
import os
import platform
import logging

from pandas.io import sql
import pandas as pd

import braviz
from braviz.utilities import remove_non_ascii

from braviz.readAndFilter import PROJECT
if PROJECT == "kmc400":
    LATERALITY = 1423
else:
    LATERALITY = 6

IMAGE_CODE = 273

_connection = None

def get_variables(reader=None,mask=None):
    conn = get_connection(reader)
    if mask is None:
        data = sql.read_sql("SELECT var_idx, var_name from variables;", conn,index_col="var_idx")
    else:
        data = sql.read_sql("SELECT var_idx, var_name from variables WHERE var_name like ?;", conn,params=(mask,),
                            index_col="var_idx")
    return data


def get_connection(reader=None):
    if _connection is not None:
        return _connection

    node = platform.node()
    if node == "archi5":
        path = os.path.join("/home/diego/braviz_data", "tabular_data.sqlite")
    else:
        data_root = braviz.readAndFilter.braviz_auto_dynamic_data_root()
        path = os.path.join(data_root, "braviz_data", "tabular_data.sqlite")
    conn = sqlite3.connect(path)
    __connection = conn
    return conn


def get_laterality(subj_id):
    conn = get_connection()
    subj_id = int(subj_id)
    cur = conn.execute("SELECT value FROM var_values WHERE var_idx = ? and subject = ?",(LATERALITY,subj_id))
    res = cur.fetchone()
    if res is None:
        raise Exception("Unknown laterality")
    if res[0]==1:
        return 'r'
    else:
        return 'l'


def get_data_frame_by_name(columns, reader=None):
    """Warning, names may change, consider using get_data_frame_by_index"""
    if isinstance(columns, basestring):
        columns = (columns,)
    conn = get_connection(reader)
    data = sql.read_sql("SELECT subject from SUBJECTS", conn, index_col="subject")
    for var in columns:
        # language=SQLite
        query = """SELECT subject, value
        FROM subjects NATURAL JOIN var_values
        WHERE var_idx = (SELECT var_idx FROM variables WHERE var_name = ?)
        """
        col = sql.read_sql(query, conn, index_col="subject", params=(str(var),), coerce_float=True)
        data[var] = col.astype(pd.np.float64)

    return data


def get_data_frame_by_index(columns, reader=None,col_name_index=False):
    if not hasattr(columns, "__iter__"):
        columns = (columns,)

    conn = get_connection(reader)
    data = sql.read_sql("SELECT subject from SUBJECTS", conn, index_col="subject")
    col_names = []
    for i in columns:
        name = conn.execute("SELECT var_name FROM variables WHERE var_idx = ?", (int(i),))
        name1 = name.fetchone()
        if name1 is not None:
            name = name1[0]
            col_names.append(name)
        else:
            col_names.append("Var_%d"%i)

    for var_idx, var_name in izip(columns, col_names):
        query = """SELECT subject, value
        FROM subjects NATURAL JOIN var_values
        WHERE var_idx = ?
        """
        col = sql.read_sql(query, conn, index_col="subject", params=(int(var_idx),), coerce_float=True)
        if col_name_index is True:
            data[var_idx] = col.astype(pd.np.float64)
        else:
            data[var_name] = col.astype(pd.np.float64)

    return data


def is_variable_real(var_idx):
    """
    All variables are assumed real by default
    """
    conn = get_connection()
    cur = conn.execute("SELECT is_real FROM variables WHERE var_idx = ?", (int(var_idx),))
    res = cur.fetchone()
    if res is None:
        return True
    return False if res[0] == 0 else True

def does_variable_name_exists(var_name):
    conn = get_connection()
    cur = conn.execute("SELECT count(*) FROM variables WHERE var_name = ?", (var_name,))
    return False if cur.fetchone()[0] == 0 else True
def is_variable_nominal(var_idx):
    return not is_variable_real(var_idx)


def is_variable_name_real(var_name):
    conn = get_connection()
    cur = conn.execute("SELECT is_real FROM variables  WHERE var_name = ?", (unicode(var_name),))
    return False if cur.fetchone()[0] == 0 else True


def is_variable_name_nominal(var_name):
    return not is_variable_name_real(var_name)


def are_variables_real(var_idxs):
    return dict((idx, is_variable_real(idx)) for idx in var_idxs)


def are_variables_nominal(var_idxs):
    return dict((idx, not is_variable_real(idx)) for idx in var_idxs)


def are_variables_names_real(var_names):
    return dict((name, is_variable_name_real(name)) for name in var_names)


def are_variables_names_nominal(var_names):
    return dict((name, not is_variable_name_nominal(name)) for name in var_names)


def get_labels_dict(var_idx):
    conn = get_connection()
    q="""
    SELECT label2, name
    from
    (
    SELECT  distinct value as label2, var_idx as var_idx2
    FROM var_values
    WHERE var_idx = ?
    ) left outer join
    nom_meta ON (nom_meta.label = label2 and var_idx2 = nom_meta.var_idx)

    UNION
    SELECT label as label2, name FROM nom_meta WHERE var_idx =  ?

    ORDER BY label2
    """
    cur = conn.execute(q, (int(var_idx),int(var_idx),))
    ans_dict = dict(cur)
    return ans_dict


def get_names_label_dict(var_name):
    conn = get_connection()
    q="""
        SELECT label2, name
        from
        (
        SELECT  distinct value as label2, variables.var_idx as var_idx2
        FROM variables natural join var_values
        WHERE variables.var_name = ?
        ) left outer join
        nom_meta ON (nom_meta.label = label2 and var_idx2 = nom_meta.var_idx)

        UNION
        SELECT label as label2, name FROM nom_meta WHERE var_idx =  (select var_idx from variables WHERE var_name = ?)

        ORDER BY label2
        """
    cur = conn.execute(q, (unicode(var_name),unicode(var_name)))
    ans_dict = dict(cur.fetchall())
    return ans_dict


def get_var_name(var_idx):
    conn = get_connection()
    cur = conn.execute("SELECT var_name FROM variables WHERE var_idx = ?", (int(var_idx),))
    ans = cur.fetchone()
    if ans is None:
        return "?"
    return ans[0]


def get_var_idx(var_name):
    """
    Gets the index corresponding to the first occurrence of a given variable name, if it doesn't exist returns None
    """
    conn = get_connection()
    cur = conn.execute("SELECT var_idx FROM variables WHERE var_name = ?", (unicode(var_name),))
    res = cur.fetchone()
    if res is None:
        return None
    return res[0]


def get_maximum_value(var_idx):
    conn = get_connection()
    cur = conn.execute("SELECT max_val FROM ratio_meta WHERE var_idx = ?", (int(var_idx),))
    res = cur.fetchone()
    if res is None:
        q = """select MAX(value) from (select * from var_values where value != "nan")
        where var_idx = ? group by var_idx"""
        cur = conn.execute(q, (int(var_idx),))
        res = cur.fetchone()
    return res


def get_minumum_value(var_idx):
    conn = get_connection()
    cur = conn.execute("SELECT min_val FROM ratio_meta WHERE var_idx = ?", (int(var_idx),))
    res = cur.fetchone()
    if res is None:
        q = """select Min(value) from (select * from var_values where value != "nan")
        where var_idx = ? group by var_idx"""
        cur = conn.execute(q, (int(var_idx),))
        res = cur.fetchone()
    return res


def get_min_max_values(var_idx):
    conn = get_connection()
    cur = conn.execute("SELECT min_val, max_val FROM ratio_meta WHERE var_idx = ?", (int(var_idx),))
    res = cur.fetchone()
    if res is None:
        q = """select MIN(value), MAX(value) from (select * from var_values where value != "nan")
        where var_idx = ? group by var_idx"""
        cur = conn.execute(q, (int(var_idx),))
        res = cur.fetchone()
    return res


def get_min_max_values_by_name(var_name):
    conn = get_connection()
    cur = conn.execute("SELECT min_val, max_val FROM ratio_meta NATURAL JOIN variables WHERE var_name = ?",
                       (unicode(var_name),))
    res = cur.fetchone()
    if res is None:
        q = """select MIN(value), MAX(value) from (select * from var_values where value != "nan")
        where var_idx = (SELECT var_idx FROM variables WHERE var_name = ?) group by var_idx"""
        cur = conn.execute(q, (unicode(var_name),))
        res = cur.fetchone()
    return res

def get_min_max_opt_values_by_name(var_name):
    conn = get_connection()
    cur = conn.execute("SELECT min_val, max_val, optimum_val FROM ratio_meta NATURAL JOIN variables WHERE var_name = ?",
                       (unicode(var_name),))
    res = cur.fetchone()
    if res is None:
        q = """select MIN(value), MAX(value), AVG(VALUE) from (select * from var_values where value != "nan")
        where var_idx = (SELECT var_idx FROM variables WHERE var_name = ?) group by var_idx"""
        cur = conn.execute(q, (unicode(var_name),))
        res = cur.fetchone()
    return res

def get_subject_variables(subj_code, var_codes):
    """Returns a data frame with two columns, variable_name, value... with var_codes as index,
     the values are for the current subject, or NAN if subj is invalid
    """
    conn = get_connection()
    names = []
    values = []
    for idx in var_codes:
        cur = conn.execute("SELECT var_name, is_real FROM variables WHERE var_idx = ?", (int(idx),))
        ans = cur.fetchone()
        if ans is None:
            var_name, is_real = "<Unexistent>", 1
        else:
            var_name, is_real = ans
        if subj_code is None:
            value = "Nan"
        elif (is_real is None) or (is_real > 0):
            cur = conn.execute("SELECT value FROM var_values WHERE var_idx = ? and subject = ?",
                               (int(idx), int(subj_code)))
            ans = cur.fetchone()
            if ans is None:
                value = float("nan")
            else:
                value = ans[0]
        else:
            q = """SELECT name FROM var_values NATURAL JOIN nom_meta
            WHERE subject = ? and var_idx = ? and var_values.value == nom_meta.label"""
            cur = conn.execute(q, (int(subj_code), int(idx)))
            ans = cur.fetchone()
            if ans is None:
                value = "?"
            else:
                value = ans[0]
        names.append(var_name)
        values.append(value)
    output = pd.DataFrame({"name": names, "value": values}, index=var_codes)
    return output

def get_subjects():
    conn = get_connection()
    cur=conn.execute("SELECT subject FROM subjects ORDER BY subject")
    subj_list = [ t[0] for t in cur.fetchall()]
    return subj_list

def get_var_description(var_idx):
    conn = get_connection()
    q = "SELECT description FROM var_descriptions WHERE var_idx = ?"
    cur = conn.execute(q, (int(var_idx),))
    res = cur.fetchone()
    if res is None:
        return ""
    return res[0]


def get_var_description_by_name(var_name):
    conn = get_connection()
    q = "SELECT description FROM var_descriptions NATURAL JOIN variables WHERE var_name = ?"
    cur = conn.execute(q, (unicode(var_name),))
    res = cur.fetchone()
    if res is None:
        return ""
    return res[0]


def save_is_real_by_name(var_name, is_real):
    conn = get_connection()
    query = "UPDATE variables SET is_real = ? WHERE var_name = ?"
    conn.execute(query, (is_real, unicode(var_name)))
    conn.commit()


def save_is_real(var_idx, is_real):
    conn = get_connection()
    query = "UPDATE variables SET is_real = ? WHERE var_idx = ?"
    conn.execute(query, (is_real, int(var_idx)))
    conn.commit()


def save_real_meta_by_name(var_name, min_value, max_value, opt_value):
    conn = get_connection()
    query = """INSERT OR REPLACE INTO ratio_meta
    VALUES(
    (SELECT var_idx FROM variables WHERE var_name = ?),
    ? , ? , ? );
    """
    try:
        conn.execute(query,
                     (var_name, min_value,
                      max_value, opt_value)
        )
    except (KeyError, ValueError):
        pass
    else:
        conn.commit()

def save_real_meta(var_idx, min_value, max_value, opt_value):
    conn = get_connection()
    query = """INSERT OR REPLACE INTO ratio_meta
    VALUES(?, ? , ? , ? );
    """
    try:
        conn.execute(query,
                     (var_idx, min_value,
                      max_value, opt_value)
        )
    except (KeyError, ValueError):
        pass
    else:
        conn.commit()
def save_nominal_labels_by_name(var_name,label_name_tuples):
    mega_tuple=( (var_name, label, name) for label, name in label_name_tuples)
    con = get_connection()
    query = """INSERT OR REPLACE INTO nom_meta
    VALUES (
    (SELECT var_idx FROM variables WHERE var_name = ?),
    ?, -- label
    ? -- name
    );
    """
    con.executemany(query, mega_tuple)
    con.commit()

def save_nominal_labels(var_idx,label_name_tuples):
    mega_tuple=( (var_idx, label, name) for label,name in label_name_tuples)
    con = get_connection()
    query = """INSERT OR REPLACE INTO nom_meta
    VALUES (
    ?, --idx
    ?, -- label
    ? -- name
    );
    """
    con.executemany(query, mega_tuple)
    con.commit()

def save_var_description_by_name(var_name,description):
    conn = get_connection()
    query = """INSERT OR REPLACE INTO var_descriptions
    VALUES
    ((SELECT var_idx FROM variables WHERE var_name = ?), -- var_idx
    ?) -- desc """
    conn.execute(query, (var_name,description,))
    conn.commit()

def save_var_description(var_idx,description):
    conn = get_connection()
    query = """INSERT OR REPLACE INTO var_descriptions
    VALUES
    (?, -- var_idx
    ?) -- desc"""
    conn.execute(query, (var_idx,description,))
    conn.commit()

def register_new_variable(var_name,is_real=1):
    var_name = unicode(var_name)
    conn = get_connection()
    q1 = "SELECT var_idx from VARIABLES where var_name = ?"
    cur=conn.execute(q1,(var_name,))
    if cur.fetchone() is not None:
        raise Exception("Attempting to add duplicate variable")
    if is_real:
        is_real = 1
    else:
        is_real = 0
    q="""INSERT INTO variables (var_name, is_real)
         Values (? , ?)"""
    cur = conn.execute(q,(unicode(var_name),is_real))
    conn.commit()
    row_id = cur.lastrowid
    cur=conn.execute(q1,(var_name,))
    var_idx = cur.fetchone()
    if var_idx is None:
        log = logging.getLogger(__name__)
        log.error("Problem adding to Data Base")
    assert var_idx[0] == row_id
    return row_id

def update_variable_values(var_idx,tuples):
    """
    Tuples should be [(subj1,value1),(subj2,value2) ....]
    """
    conn=get_connection()
    super_tuples=((var_idx,s,v) for s,v in tuples)
    q="""INSERT OR REPLACE INTO var_values VALUES (? ,?, ?)"""
    conn.executemany(q,super_tuples)
    conn.commit()

def update_multiple_variable_values(idx_subject_value_tuples):
    """
    idx_subject_value_tuples is an iterable containing tuples of the form (var_idx,subj,value)
    """
    conn=get_connection()
    q="""INSERT OR REPLACE INTO var_values VALUES (? ,?, ?)"""
    conn.executemany(q,idx_subject_value_tuples)
    conn.commit()

def updata_variable_value(var_idx,subject,new_value):
    """
    Updates a single value for variable var_idx and subject
    """
    conn=get_connection()
    q="""INSERT OR REPLACE INTO var_values VALUES (? ,?, ?)"""
    conn.execute(q,(int(var_idx),int(subject),new_value))
    conn.commit()

def get_var_value(var_idx,subject):
    conn = get_connection()
    q="SELECT value FROM var_values WHERE var_idx = ? and subject = ?"
    cur=conn.execute(q,(var_idx,subject))
    res=cur.fetchone()
    if res is None:
        log = logging.getLogger(__name__)
        log.error("%s not found for subject %s"%(var_idx,subject))
        raise Exception("%s not found for subject %s"%(var_idx,subject))
    return res[0]

def get_image_code(subject):
    return get_var_value(IMAGE_CODE,subject)

def get_variable_normal_range(var_idx):
    conn = get_connection()
    #minimum,maximum
    # 10 = UBIC3
    q = """SELECT min(var_values.value), max(cast( var_values.value as numeric)) from var_values JOIN var_values as var_values2
     WHERE var_values.subject == var_values2.subject and var_values2.var_idx == 10 and var_values2.value == 3
     and var_values.var_idx = ?
        """
    c=conn.execute(q,(var_idx,))
    values = c.fetchone()
    if values is None:
        return (float("nan"),float("nan"))
    else:
        return values

def float_or_nan(s):
    try:
        v = float(s)
    except ValueError:
        v = float("nan")
    return v

def add_data_frame(df):
    conn = get_connection()
    columns = df.columns
    columns = map(remove_non_ascii,columns)
    df.columns = columns
    tot_cols = len(columns)
    subjs = df.index.get_values().astype(int)
    #check if there are new subjects
    print "updating subjects"
    with conn:
        q="INSERT OR IGNORE INTO subjects VALUES(?)"
        conn.executemany(q,( (s,) for s in subjs))

    for i, c in enumerate(columns):
        with conn:
            print "%d / %d : %s"%(i,tot_cols,c)
            q1 = "INSERT INTO variables (var_name) VALUES (?)"
            cur = conn.execute(q1,(c,))
            var_idx = cur.lastrowid
            col = df[c]
            try:
                vals = col.get_values().astype(float)
            except ValueError:
                vals = [float_or_nan(s) for s in col.get_values()]
            q2 = """INSERT OR REPLACE INTO var_values (var_idx,subject,value)
            VALUES ( ?, ?,?)"""
            conn.executemany(q2,izip(repeat(var_idx),subjs,vals))

def _recursive_delete_variable(var_idx):
    """
    Warning... scenario files may become invalid, this is not reversible
    """
    conn = get_connection()
    try:
        with conn:
            #delete values
            q = "DELETE FROM var_values WHERE var_idx = ?"
            conn.execute(q,(var_idx,))
            #delete meta
            q1 = "DELETE FROM nom_meta WHERE var_idx = ?"
            q2 = "DELETE FROM ratio_meta WHERE var_idx = ?"
            conn.execute(q1,(var_idx,))
            conn.execute(q2,(var_idx,))
            #delete description
            q = "DELETE FROM var_descriptions WHERE var_idx = ?"
            conn.execute(q,(var_idx,))
            #delete vars_scenarios
            q = "DELETE FROM vars_scenarios WHERE var_idx = ?"
            conn.execute(q,(var_idx,))
            #delete variable
            q = "DELETE FROM variables WHERE var_idx = ?"
            conn.execute(q,(var_idx,))
    except sqlite3.IntegrityError as e:
        print e.message
        print "DataBase not modified"
    else:
        print "Done"



