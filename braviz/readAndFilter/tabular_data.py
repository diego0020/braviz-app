# #############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


from __future__ import print_function
import sqlite3
from itertools import izip, repeat
import os
import threading
import logging

from pandas.io import sql
import pandas as pd

import braviz
from braviz.utilities import remove_non_ascii, show_error
from braviz.readAndFilter.config_file import get_apps_config

__author__ = 'Diego'

LATERALITY = None
LEFT_HANDED = None
UBICAC = None

_connections = dict()

def get_connection():
    """
    Gets the sqlite3 connection object for this thread.

    Also initializes module variables LATERALITY, LEFT_HANDED and UBICAC
    """
    global _connections
    global LATERALITY, LEFT_HANDED

    thread_id = threading.current_thread()
    connection_obj = _connections.get(thread_id)
    if connection_obj is not None:
        return connection_obj

    data_root = braviz.readAndFilter.braviz_auto_dynamic_data_root()
    path = os.path.join(data_root, "braviz_data")
    db_name = os.path.join(path, "tabular_data.sqlite")
    if not os.path.isdir(data_root):
        show_error("Couldn't open database file\n%s" % path)
        raise IOError("Couldn't open database location:\n%s"%path)

    conn = sqlite3.connect(db_name,  detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("pragma busy_timeout = 10000")
    _connections[thread_id] = conn
    if LATERALITY is None:
        try:
            _conf = get_apps_config()
            _lat_name, _left_labell = _conf.get_laterality()
            cur = conn.execute(
                "SELECT var_idx from variables where var_name = ?", (_lat_name,))
            res = cur.fetchone()
            LATERALITY = res[0]
            LEFT_HANDED = _left_labell
        except Exception as e:
            pass
    return conn



def get_variables(mask=None):
    """
    Gets available variables

    Args:
        mask (str) : If not None, limit answer to results whose name match the given mask (sql ``like`` syntax)

    Returns:
        :class:`pandas.DataFrame` with variable indexes as index, and a single column with variable names
    """
    conn = get_connection()
    if mask is None:
        data = sql.read_sql(
            "SELECT var_idx, var_name from variables;", conn, index_col="var_idx")
    else:
        data = sql.read_sql("SELECT var_idx, var_name from variables WHERE var_name like ?;", conn, params=(mask,),
                            index_col="var_idx")
    return data

def get_variables_and_type(mask=None):
    """
    Gets available variables

    Args:
        mask (str) : If not None, limit answer to results whose name match the given mask (sql ``like`` syntax)

    Returns:
        :class:`pandas.DataFrame` with variable indexes as index, a column with variable names, and a with ``1`` for
            numerical values and ``0`` for nominal variables
    """
    conn = get_connection()
    if mask is None:
        data = sql.read_sql(
            "SELECT var_idx, var_name, is_real  from variables;", conn, index_col="var_idx")
    else:
        data = sql.read_sql("SELECT var_idx, var_name, is_real from variables WHERE var_name like ?;", conn, params=(mask,),
                            index_col="var_idx")
    return data



def _reset_connection():
    """
    Resests existing connection for this thread
    """
    global _log_connections
    log = logging.getLogger(__name__)
    thread_id = threading.current_thread()
    connection_obj = _connections.get(thread_id)
    if connection_obj is None:
        return
    else:
        try:
            connection_obj.close()
        except Exception as e:
            log.exception(e)
        del _connections[thread_id]


def get_laterality(subj_id):
    """
    Gets the laterality for a given subject

    Args:
        subj_id : The id of the subject

    Returns:
        "l" for a left handed subject, "r" otherwise
    """
    conn = get_connection()
    subj_id = int(subj_id)
    cur = conn.execute(
        "SELECT value FROM var_values WHERE var_idx = ? and subject = ?", (LATERALITY, subj_id))
    res = cur.fetchone()
    if res is None:
        raise Exception("Unknown laterality")
    if res[0] != LEFT_HANDED:
        return 'r'
    else:
        return 'l'


def get_data_frame_by_name(columns, ):
    """
    A data frame containing one column for each variable name in columns

    Args:
        columns (list) : Variable names

    Returns:
        :class:`pandas.DataFrame` with subject ids as index and one column for each variable

    """
    if isinstance(columns, basestring):
        columns = (columns,)
    conn = get_connection()
    data = sql.read_sql(
        "SELECT subject from SUBJECTS", conn, index_col="subject")
    for var in columns:
        # language=SQLite
        query = """SELECT subject, value
        FROM subjects NATURAL JOIN var_values
        WHERE var_idx = (SELECT var_idx FROM variables WHERE var_name = ?)
        """
        col = sql.read_sql(
            query, conn, index_col="subject", params=(unicode(var),), coerce_float=True)
        data[var] = col.astype(pd.np.float64)

    return data


def get_data_frame_by_index(columns, col_name_index=False):
    """
    A data frame containing one column for each variable index in columns

    Args:
        columns (list) : Variable indexes

    Returns:
        :class:`pandas.DataFrame` with subject ids as index and one column for each variable

    """
    if not hasattr(columns, "__iter__"):
        columns = (columns,)

    conn = get_connection()
    data = sql.read_sql(
        "SELECT subject from SUBJECTS", conn, index_col="subject")
    col_names = []
    for i in columns:
        name = conn.execute(
            "SELECT var_name FROM variables WHERE var_idx = ?", (int(i),))
        name1 = name.fetchone()
        if name1 is not None:
            name = name1[0]
            col_names.append(name)
        else:
            col_names.append("Var_%d" % i)

    for var_idx, var_name in izip(columns, col_names):
        query = """SELECT subject, value
        FROM subjects NATURAL JOIN var_values
        WHERE var_idx = ?
        """
        col = sql.read_sql(
            query, conn, index_col="subject", params=(int(var_idx),), coerce_float=True)
        if col_name_index is True:
            data[var_idx] = col.astype(pd.np.float64)
        else:
            data[var_name] = col.astype(pd.np.float64)

    return data


def is_variable_real(var_idx):
    """
    Find if the variable is real or nominal

    Args:
        var_idx (int) : Variable index

    Returns:
        ``False`` if the variable is Nominal,
        ``True`` otherwise

    """
    conn = get_connection()
    cur = conn.execute(
        "SELECT is_real FROM variables WHERE var_idx = ?", (int(var_idx),))
    res = cur.fetchone()
    if res is None:
        return True
    return False if res[0] == 0 else True


def does_variable_name_exists(var_name):
    """
    Find if the a variable with the given name exists in the database

    Args:
        var_name (str) : Variable name

    Returns:
        ``True`` if a variable with the given name exists,
        ``False`` otherwise
    """
    conn = get_connection()
    cur = conn.execute(
        "SELECT count(*) FROM variables WHERE var_name = ?", (var_name,))
    return False if cur.fetchone()[0] == 0 else True


def is_variable_nominal(var_idx):
    """
    Find if the variable is real or nominal

    Args:
        var_idx (int) : Variable index

    Returns:
        ``True`` if the variable is Nominal,
        ``False`` otherwise

    """

    return not is_variable_real(var_idx)


def is_variable_name_real(var_name):
    """
    Find if the variable is real or nominal

    Args:
        var_name (str) : Variable name

    Returns:
        ``False`` if the variable is Nominal,
        ``True`` otherwise

    """
    conn = get_connection()
    cur = conn.execute(
        "SELECT is_real FROM variables  WHERE var_name = ?", (unicode(var_name),))
    return False if cur.fetchone()[0] == 0 else True


def is_variable_name_nominal(var_name):
    """
    Find if the variable is real or nominal

    Args:
        var_name (str) : Variable name

    Return:
        ``True`` if the variable is Nominal,
        ``False`` otherwise

    """
    return not is_variable_name_real(var_name)


def are_variables_real(var_idxs):
    """
    For each variable in a list, find if it is real

    Args:
        var_idxs (list) : variable indexes

    Returns:
        A dictionary with variable indexes as keys, and booleans as values as in
        :func:`~.is_variable_real`

    """
    return dict((idx, is_variable_real(idx)) for idx in var_idxs)


def are_variables_nominal(var_idxs):
    """
    For each variable in a list, find if it is real

    Args:
        var_idxs (list) : variable indexes

    Returns:
        A dictionary with variable indexes as keys, and booleans as values as in
        :func:`~.is_variable_nominal`

    """
    return dict((idx, not is_variable_real(idx)) for idx in var_idxs)


def are_variables_names_real(var_names):
    """
    For each variable in a list, find if it is real

    Args:
        var_names (list) : variable names

    Returns:
        A dictionary with variable names as keys, and booleans as values as in
        :func:`~.is_variable_name_real`
    """
    return dict((name, is_variable_name_real(name)) for name in var_names)


def are_variables_names_nominal(var_names):
    """
    For each variable in a list, find if it is real

    Args:
        var_names (list) : variable names

    Returns:
        A dictionary with variable names as keys, and booleans as values as in
        :func:`~.is_variable_name_nominal`
    """
    return dict((name, not is_variable_name_nominal(name)) for name in var_names)


def get_labels_dict(var_idx=None, var_name=None):
    """
    Map numerical labels to strings in nominal variables

    Args:
        var_idx (int) : Variable Index

    Returns:
        A dictionary with numerical labels as keys, and the text for each label as
        values.
    """
    if var_idx is None :
        if var_name is None:
            raise Exception("var_idx or var_name is required")
        var_idx = get_var_idx(var_name)

    conn = get_connection()
    q = """
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
    cur = conn.execute(q, (int(var_idx), int(var_idx),))
    ans_dict = dict(cur)

    return ans_dict


def get_labels_dict_by_name(var_name):
    """
    Map numerical labels to strings in nominal variables

    Args:
        var_name (str) : Variable name

    Returns:
        A dictionary with numerical labels as keys, and the text for each label as
        values.
    """
    conn = get_connection()
    q = """
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
    cur = conn.execute(q, (unicode(var_name), unicode(var_name)))
    ans_dict = dict(cur.fetchall())
    return ans_dict


def get_var_name(var_idx):
    """
    Name of variable with given index

    Args:
        var_idx (int) : Variable index

    Returns:
        Variable name if it exists, ``"?"`` otherwise

    """
    conn = get_connection()
    cur = conn.execute(
        "SELECT var_name FROM variables WHERE var_idx = ?", (int(var_idx),))
    ans = cur.fetchone()
    if ans is None:
        return "?"
    return ans[0]


def get_var_idx(var_name):
    """
    Index of variable with given name

    Args:
        var_name (str) : Variable name

    Returns:
        Index of variable with the given name if it exists, ``None`` otherwise

    """
    conn = get_connection()
    cur = conn.execute(
        "SELECT var_idx FROM variables WHERE var_name = ?", (unicode(var_name),))
    res = cur.fetchone()
    if res is None:
        return None
    return res[0]


def get_maximum_value(var_idx):
    """
    Gets the maximum value for a real variable as recorded in meta-data

    If there is no metadata, it is calculated from the existing values

    Args:
        var_idx (int) : Variable index

    Returns:
        Maximum values as recorded in the metadata,
         if there is no metadata, maximum from existing values.

    """
    conn = get_connection()
    cur = conn.execute(
        "SELECT max_val FROM ratio_meta WHERE var_idx = ?", (int(var_idx),))
    res = cur.fetchone()
    if res is None:
        q = """select MAX(value) from (select * from var_values where value != "nan")
        where var_idx = ? group by var_idx"""
        cur = conn.execute(q, (int(var_idx),))
        res = cur.fetchone()
    return res


def get_minimum_value(var_idx):
    """
    Gets the minimum value for a real variable as recorded in meta-data

    If there is no metadata, it is calculated from the existing values

    Args:
        var_idx (int) : Variable index

    Returns:
        Minimum values as recorded in the metadata,
         if there is no metadata, minimum from existing values.

    """
    conn = get_connection()
    cur = conn.execute(
        "SELECT min_val FROM ratio_meta WHERE var_idx = ?", (int(var_idx),))
    res = cur.fetchone()
    if res is None:
        q = """select Min(value) from (select * from var_values where value != "nan")
        where var_idx = ? group by var_idx"""
        cur = conn.execute(q, (int(var_idx),))
        res = cur.fetchone()
    return res


def get_min_max_values(var_idx):
    """
    Gets the minimum and maximum values for a real variable as recorded in meta-data

    If there is no metadata, they are calculated from the existing values

    Args:
        var_idx (int) : Variable index

    Returns:
        ``(min_val, max_val)``  values as recorded in the metadata,
         if there is no metadata, they are calculated from existing values

    """
    conn = get_connection()
    cur = conn.execute(
        "SELECT min_val, max_val FROM ratio_meta WHERE var_idx = ?", (int(var_idx),))
    res = cur.fetchone()
    if res is None:
        q = """select MIN(value), MAX(value) from (select * from var_values where value != "nan")
        where var_idx = ? group by var_idx"""
        cur = conn.execute(q, (int(var_idx),))
        res = cur.fetchone()
    return res


def get_min_max_values_by_name(var_name):
    """
    Gets the minimum and maximum values for a real variable as recorded in meta-data

    If there is no metadata, they are calculated from the existing values

    Args:
        var_name (str) : Variable name

    Returns:
        ``(min_val, max_val)``  values as recorded in the metadata,
         if there is no metadata, they are calculated from existing values

    """
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
    """
    Gets the minimum, maximum and optimal values for a real variable as recorded in meta-data

    If there is no metadata, they are calculated from the existing values

    Args:
        var_name (str) : Variable name

    Returns:
        ``(min_val, max_val, optimum_val)``  values as recorded in the metadata,
         if there is no metadata, they are calculated from existing values. In this case the optimum will
         be the mean of existing values.

    """
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
    """
    Get several values for one subjects

    Args:
        subj_code : Subject id
        var_codes (list) : Variable codes

    Returns:
        :class:`pandas.DataFrame` with two columns: Variable name, and variable value; for each index in var_codes,
        which will be used as indexes in the DataFrame.

    """
    conn = get_connection()
    names = []
    values = []
    for idx in var_codes:
        cur = conn.execute(
            "SELECT var_name, is_real FROM variables WHERE var_idx = ?", (int(idx),))
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
            if ans is None or ans[0] is None:
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
    """
    Get a list subjects which exist in the database
    """
    conn = get_connection()
    cur = conn.execute("SELECT subject FROM subjects ORDER BY subject")
    subj_list = [t[0] for t in cur.fetchall()]
    return subj_list


def get_var_description(var_idx):
    """
    Get description for a variable

    Args:
        var_idx (int) : Variable index

    Returns:
        A string containing the description of the variable.
    """
    conn = get_connection()
    q = "SELECT description FROM var_descriptions WHERE var_idx = ?"
    cur = conn.execute(q, (int(var_idx),))
    res = cur.fetchone()
    if res is None:
        return ""
    return res[0]

def get_descriptions_dict():
    """
    Get a dictionary with the descriptions of all variables

    Returns:
        A dictionary with variable indices as keys and description strings as values
    """
    conn = get_connection()
    q = "SELECT var_idx, description FROM var_descriptions"
    cur = conn.execute(q)
    res = dict(cur.fetchall())
    return res

def get_var_description_by_name(var_name):
    """
    Get description for a variable

    Args:
        var_name (str) : Variable name

    Returns:
        A string containing the description of the variable.
    """
    conn = get_connection()
    q = "SELECT description FROM var_descriptions NATURAL JOIN variables WHERE var_name = ?"
    cur = conn.execute(q, (unicode(var_name),))
    res = cur.fetchone()
    if res is None:
        return ""
    return res[0]


def save_is_real_by_name(var_name, is_real):
    """
    Update variable type in the metadata

    Args:
        var_name (str) :  Variable name
        is_real (bool) : If True the variable will be registered as real, otherwise it will be registered as nominal.
    """
    conn = get_connection()
    with conn:
        query = "UPDATE variables SET is_real = ? WHERE var_name = ?"
        conn.execute(query, (is_real, unicode(var_name)))



def save_is_real(var_idx, is_real):
    """
    Update variable type in the metadata

    Args:
        var_idx (int) :  Variable index
        is_real (bool) : If True the variable will be registered as real, otherwise it will be registered as nominal.
    """
    conn = get_connection()
    with conn:
        query = "UPDATE variables SET is_real = ? WHERE var_idx = ?"
        conn.execute(query, (is_real, int(var_idx)))



def save_real_meta_by_name(var_name, min_value, max_value, opt_value):
    """
    Update real variables' meta data

    Args:
        var_name (str) :  Variable name
        min_value (float) : Variables minimum value
        man_value (float) : Variables maximum value
        opt_value (float) : Variables optimum value
    """
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
    """
    Update real variables' meta data

    Args:
        var_idx (int) :  Variable index
        min_value (float) : Variables minimum value
        man_value (float) : Variables maximum value
        opt_value (float) : Variables optimum value
    """
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


def save_nominal_labels_by_name(var_name, label_name_tuples):
    """
    Update nominal variable labels

    Args:
        var_name (str) :  Variable name
        label_name_tuples (list) : List of tuples, the first component of each tuple is the numeric label, and the
            second component its meaning. For example ``(1, "male")``

    """
    mega_tuple = ((var_name, label, name) for label, name in label_name_tuples)
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


def save_nominal_labels(var_idx, label_name_tuples):
    """
    Update nominal variable labels

    Args:
        var_idx (int) :  Variable index
        label_name_tuples (list) : List of tuples, the first component of each tuple is the numeric label, and the
            second component its meaning. For example ``(1, "male")``

    """
    mega_tuple = ((var_idx, label, name) for label, name in label_name_tuples)
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


def save_var_description_by_name(var_name, description):
    """
    Save or overwrite description for a variable

    Args:
        var_name (str) : Variable Name
        description (str) : Variable description
    """
    conn = get_connection()
    query = """INSERT OR REPLACE INTO var_descriptions
    VALUES
    ((SELECT var_idx FROM variables WHERE var_name = ?), -- var_idx
    ?) -- desc """
    conn.execute(query, (var_name, description,))
    conn.commit()


def save_var_description(var_idx, description):
    """
    Save or overwrite description for a variable

    Args:
        var_idx (int) : Variable index
        description (str) : Variable description
    """
    conn = get_connection()
    query = """INSERT OR REPLACE INTO var_descriptions
    VALUES
    (?, -- var_idx
    ?) -- desc"""
    conn.execute(query, (var_idx, description,))
    conn.commit()


def register_new_variable(var_name, is_real=1):
    """
    Adds a new variable to the database

    Args:
        var_name (str) : Name for the new variable, should be unique
        is_real (bool) : Type of the new variable, ``True`` if it is real, ``False`` if it is nominal

    Returns:
        Database index of the new variable
    """
    var_name = unicode(var_name)
    conn = get_connection()
    try:
        with conn:
            if is_real:
                is_real = 1
            else:
                is_real = 0
            q = """INSERT INTO variables (var_name, is_real)
                 Values (? , ?)"""
            cur = conn.execute(q, (var_name, is_real))
            row_id = cur.lastrowid
        return row_id
    except sqlite3.IntegrityError:
        log = logging.getLogger(__name__)
        log.warning("Couldn't create new variable")
        return None


def update_variable_values(var_idx, tuples):
    """
    Updates values for one variable and some subjects

    Args:
        var_idx (int) : Variable index
        tuples (list) : Tuples of the form ``(subject,value)`` where subject is the subject id, and value
            is the new value for the variable.
    """
    conn = get_connection()
    super_tuples = ((var_idx, s, v) for s, v in tuples)
    q = """INSERT OR REPLACE INTO var_values VALUES (? ,?, ?)"""
    conn.executemany(q, super_tuples)
    conn.commit()


def update_multiple_variable_values(idx_subject_value_tuples):
    """
    Updates values for variables and subjects

    Args:
        idx_subject_value_tuples (list) : Tuples of the form ``(var_idx, subject, value)`` where var_idx and subject
            are the variable and subject for whom the new value will be set.
    """
    conn = get_connection()
    q = """INSERT OR REPLACE INTO var_values VALUES (? ,?, ?)"""
    conn.executemany(q, idx_subject_value_tuples)
    conn.commit()


def update_variable_value(var_idx, subject, new_value):
    """
    Updates a single value for a variable and a subject

    Args:
        var_idx (int) : Variable index
        subject : Subject id
        new_value : Value to be saved
    """
    conn = get_connection()
    q = """INSERT OR REPLACE INTO var_values VALUES (? ,?, ?)"""
    conn.execute(q, (int(var_idx), int(subject), new_value))
    conn.commit()


def get_var_value(var_idx, subject):
    """
    Gets a single variable value

    Args:
        var_idx (int) : Variable index
        subject : Subject id

    Returns:
        The numerical value for the given variable and subject
    """
    conn = get_connection()
    q = "SELECT value FROM var_values WHERE var_idx = ? and subject = ?"
    cur = conn.execute(q, (var_idx, subject))
    res = cur.fetchone()
    if res is None:
        log = logging.getLogger(__name__)
        log.error("%s not found for subject %s" % (var_idx, subject))
        raise Exception("%s not found for subject %s" % (var_idx, subject))
    return res[0]


def get_variable_normal_range(var_idx):
    """
    Get the range of a given variable for the reference population

    Args:
        var_idx : Variable index

    Returns:
        ``(min_val, max_val)`` calculated over the values the variable takes in the reference population.
    """
    global UBICAC
    conn = get_connection()
    # minimum,maximum
    q = """SELECT min(var_values.value), max(cast( var_values.value as numeric)) from var_values JOIN var_values as var_values2
     WHERE var_values.subject == var_values2.subject and var_values2.var_idx == ? and var_values2.value == ?
     and var_values.var_idx = ? and var_values.value notnull
        """
    if UBICAC is None:
        conf = get_apps_config()
        var_name, label = conf.get_reference_population()
        u_var_idx = get_var_idx(var_name)
        UBICAC = (u_var_idx, label)

    c = conn.execute(q, (UBICAC[0], UBICAC[1], var_idx))
    values = c.fetchone()
    if values is None:
        return float("nan"), float("nan")
    else:
        values = list(values)
        if values[0] is None:
            values[0] = float('nan')
        if values[1] is None:
            values[1] = float('nan')
        return values


def _float_or_nan(s):
    try:
        v = float(s)
    except ValueError:
        v = float("nan")
    return v


def add_data_frame(df):
    """
    Inserts a whole dataframe into the database

    Args:
        df ( pandas.DataFrame ) : DataFrame with subject ids as index, and one column for each new variable.
    """
    conn = get_connection()
    columns = df.columns
    columns = map(remove_non_ascii, columns)
    df.columns = columns
    tot_cols = len(columns)
    subjs = df.index.get_values().astype(int)
    # check if there are new subjects
    with conn:
        q = "INSERT OR IGNORE INTO subjects VALUES(?)"
        conn.executemany(q, ((s,) for s in subjs))

    for i, c in enumerate(columns):
        with conn:
            print("%d / %d : %s" % (i + 1, tot_cols, c))
            if does_variable_name_exists(c):
                var_idx = get_var_idx(c)
            else:
                q1 = "INSERT INTO variables (var_name) VALUES (?)"
                cur = conn.execute(q1, (c,))
                var_idx = cur.lastrowid
            col = df[c]
            try:
                vals = col.get_values().astype(float)
            except ValueError:
                vals = [_float_or_nan(s) for s in col.get_values()]
            q2 = """INSERT OR REPLACE INTO var_values (var_idx,subject,value)
            VALUES ( ?, ?,?)"""
            conn.executemany(q2, izip(repeat(var_idx), subjs, vals))
    print("done")


def recursive_delete_variable(var_idx):
    """
    Deletes a variable from all tables

    .. warning::

        This may affect large amounts of information and can't be reversed

    Some references to the variable may remain in scenario data or outside the database.

    Args:
        var_idx (int) : Variable index
    """
    conn = get_connection()
    try:
        with conn:
            # delete values
            q = "DELETE FROM var_values WHERE var_idx = ?"
            conn.execute(q, (var_idx,))
            # delete meta
            q1 = "DELETE FROM nom_meta WHERE var_idx = ?"
            q2 = "DELETE FROM ratio_meta WHERE var_idx = ?"
            conn.execute(q1, (var_idx,))
            conn.execute(q2, (var_idx,))
            # delete description
            q = "DELETE FROM var_descriptions WHERE var_idx = ?"
            conn.execute(q, (var_idx,))
            # delete vars_scenarios
            q = "DELETE FROM vars_scenarios WHERE var_idx = ?"
            conn.execute(q, (var_idx,))
            # delete variable
            q = "DELETE FROM variables WHERE var_idx = ?"
            conn.execute(q, (var_idx,))
    except sqlite3.IntegrityError as e:
        print(e.message)
        print("DataBase not modified")
    else:
        print("Done")


def recursive_delete_subject(subject):
    """
    Deletes a subject from the database

    .. warning::

        This may affect large amounts of information and can't be reversed

    Some references to the variable may remain in scenario data, subsamples or outside the database.
    There must not exist any geometrical structure (see :mod:`~braviz.readAndFilter.geom_db`) associated with
    the subject, if that is the case the operation will be aborted without modifying the database.

    Args:
        var_idx (int) : Variable index
    """
    conn = get_connection()
    try:
        with conn:
            # delete values
            q = "DELETE FROM var_values WHERE subject = ?"
            conn.execute(q, (subject,))
            # delete subject
            q = "DELETE FROM subjects WHERE subject = ?"
            conn.execute(q, (subject,))
    except sqlite3.IntegrityError as e:
        print(e.message)
        print("DataBase not modified")
    else:
        print("Done")


def initialize_database(path):
    """
    Create a new braviz database

    Args:
        path (str) : Name of the new sqlite file that will contain the braviz database
    """
    conn = sqlite3.connect(path)
    conn.close()
    from braviz.readAndFilter.check_db import verify_db_completeness

    verify_db_completeness(path)
