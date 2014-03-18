__author__ = 'Diego'

import sqlite3
from itertools import izip
import os

from pandas.io import sql
import pandas as pd


def get_variables(reader=None):
    conn = get_connection(reader)
    data = sql.read_sql("SELECT var_name from variables;", conn)
    conn.close()
    return data


def get_connection(reader=None):
    if reader is None:
        from braviz.readAndFilter import kmc40AutoReader

        reader = kmc40AutoReader()
    path = os.path.join(reader.getDataRoot(), "braviz_data", "tabular_data.sqlite")
    conn = sqlite3.connect(path)
    return conn


def get_data_frame_by_name(columns, reader=None):
    """Warning, names may change, consider using get_data_frame_by_index"""
    if isinstance(columns, basestring):
        columns = (columns,)
    conn = get_connection(reader)
    data = sql.read_sql("SELECT subject from SUBJECTS", conn, index_col="subject")
    for var in columns:
        query = """SELECT subject, value
        FROM subjects NATURAL JOIN var_values
        WHERE var_idx = (SELECT var_idx FROM variables WHERE var_name = ?)
        """
        col = sql.read_sql(query, conn, index_col="subject", params=(str(var),), coerce_float=True)
        data[var] = col.astype(pd.np.float64)

    conn.close()
    return data


def get_data_frame_by_index(columns, reader=None):
    if not hasattr(columns, "__iter__"):
        columns = (columns,)

    conn = get_connection(reader)
    data = sql.read_sql("SELECT subject from SUBJECTS", conn, index_col="subject")
    col_names = []
    for i in columns:
        name = conn.execute("SELECT var_name FROM variables WHERE var_idx = ?", (int(i),)).fetchone()[0]
        col_names.append(name)

    for var_idx, var_name in izip(columns, col_names):
        query = """SELECT subject, value
        FROM subjects NATURAL JOIN var_values
        WHERE var_idx = ?
        """
        col = sql.read_sql(query, conn, index_col="subject", params=(int(var_idx),), coerce_float=True)
        data[var_name] = col.astype(pd.np.float64)

    conn.close()
    return data


def is_variable_real(var_idx):
    conn = get_connection()
    cur = conn.execute("SELECT is_real FROM variables WHERE var_idx = ?", (str(var_idx),))
    return False if cur.fetchone()[0] == 0 else 1


def is_variable_nominal(var_idx):
    return not is_variable_real(var_idx)


def is_variable_name_real(var_name):
    conn = get_connection()
    cur = conn.execute("SELECT is_real FROM variables  WHERE var_name = ?", (str(var_name),))
    return False if cur.fetchone()[0] == 0 else 1


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
    cur = conn.execute("SELECT label, name FROM nom_meta WHERE var_idx = ?", (str(var_idx),))
    ans_dict = dict(cur)
    return ans_dict


def get_names_label_dict(var_name):
    conn = get_connection()
    cur = conn.execute("SELECT label, name FROM nom_meta NATURAL JOIN variables WHERE var_name = ?", (str(var_name),))
    ans_dict = dict(cur)
    return ans_dict


def get_var_name(var_idx):
    conn = get_connection()
    cur = conn.execute("SELECT var_name FROM variables WHERE var_idx = ?", (str(var_idx),))
    return cur.fetchone()[0]


def get_var_idx(var_name):
    conn = get_connection()
    cur = conn.execute("SELECT var_idx FROM variables WHERE var_name = ?", (str(var_name),))
    return cur.fetchone()[0]


def get_maximum_value(var_idx):
    conn = get_connection()
    cur = conn.execute("SELECT max_val FROM ratio_meta WHERE var_idx = ?", (str(var_idx),))
    res = cur.fetchone()
    if res is None:
        q = """select MAX(value) from (select * from var_values where value != "nan")
        where var_idx = ? group by var_idx"""
        cur = conn.execute(q, (str(var_idx),))
        res = cur.fetchone()
    return res

def get_minumum_value(var_idx):
    conn = get_connection()
    cur = conn.execute("SELECT min_val FROM ratio_meta WHERE var_idx = ?", (str(var_idx),))
    res = cur.fetchone()
    if res is None:
        q = """select Min(value) from (select * from var_values where value != "nan")
        where var_idx = ? group by var_idx"""
        cur = conn.execute(q, (str(var_idx),))
        res = cur.fetchone()
    return res

def get_min_max_values(var_idx):
    conn = get_connection()
    cur = conn.execute("SELECT min_val, max_val FROM ratio_meta WHERE var_idx = ?", (str(var_idx),))
    res = cur.fetchone()
    if res is None:
        q = """select MIN(value), MAX(value) from (select * from var_values where value != "nan")
        where var_idx = ? group by var_idx"""
        cur = conn.execute(q, (str(var_idx),))
        res = cur.fetchone()
    return res

def get_min_max_values_by_name(var_name):
    conn = get_connection()
    cur = conn.execute("SELECT min_val, max_val FROM ratio_meta NATURAL JOIN variables WHERE var_name = ?", (str(var_name),))
    res = cur.fetchone()
    if res is None:
        q = """select MIN(value), MAX(value) from (select * from var_values where value != "nan")
        where var_idx = (SELECT var_idx FROM variables WHERE var_name = ?) group by var_idx"""
        cur = conn.execute(q, (str(var_name),))
        res = cur.fetchone()
    return res

def get_subject_variables(subj_code, var_codes):
    """Returns a data frame with two columns, variable_name, value... with var_codes as index,
     the values are for the current subject, or NAN if subj is invalid
    """
    conn = get_connection()
    names=[]
    values=[]
    for idx in var_codes:
        cur=conn.execute("SELECT var_name, is_real FROM variables WHERE var_idx = ?",(int(idx),))
        var_name, is_real = cur.fetchone()
        if subj_code is None :
            value = "Nan"
        elif (is_real is None) or (is_real >0):
            cur=conn.execute("SELECT value FROM var_values WHERE var_idx = ? and subject = ?",
                             (int(idx),int(subj_code)))
            value=cur.fetchone()[0]
        else:
            q="""SELECT name FROM var_values NATURAL JOIN nom_meta
            WHERE subject = ? and var_idx = ? and var_values.value == nom_meta.label"""
            cur=conn.execute(q,(int(subj_code),int(idx)))
            value = cur.fetchone()[0]
        names.append(var_name)
        values.append(value)
    output=pd.DataFrame({"name" : names, "value" : values},index=var_codes)
    return output