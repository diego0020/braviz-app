from __future__ import division

__author__ = 'Diego'

from pandas.io import sql
import pandas as pd
import cPickle

from braviz.readAndFilter.tabular_data import get_connection


def save_scenario(application, scenario_name, scenario_description, scenario_data):
    """
    application: Name of executable
    scenario_name :  Name for the current scenario, may already exist, the date will differentiate them
    scenario_description: Description of the current scenario
    scenario_data : Binary data for the current scenario
    """
    scenario_data = buffer(scenario_data)
    conn = get_connection()
    q = """INSERT  OR ABORT INTO scenarios
    (app_idx,scn_name,scn_desc,scn_data)
    VALUES ( (SELECT app_idx FROM applications WHERE exec_name == ?),
    ?,?,?)"""
    cur = conn.execute(q, (application, scenario_name, scenario_description, scenario_data))
    conn.commit()
    res = cur.lastrowid
    return res


def update_scenario(scenario_id, name=None, description=None, scenario_data=None, application=None):
    conn = get_connection()
    if name is not None:
        conn.execute("UPDATE scenarios SET scn_name = ? WHERE scn_id = ?", (name, scenario_id))
    if description is not None:
        conn.execute("UPDATE scenarios SET scn_desc = ? WHERE scn_id = ?", (description, scenario_id))
    if scenario_data is not None:
        scenario_data = buffer(scenario_data)
        conn.execute("UPDATE scenarios SET scn_data = ? WHERE scn_id = ?", (scenario_data, scenario_id))
    if application is not None:
        q = "UPDATE scenarios SET app_idx = (SELECT app_idx FROM applications WHERE exec_name == ?) WHERE scn_id = ?"
        conn.execute(q, (application, scenario_id))
    conn.commit()


def get_scenarios_data_frame(app_name):
    conn = get_connection()
    if app_name is None:
        q = "SELECT scn_id,datetime(scn_date,'localtime') as scn_date,scn_name,scn_desc FROM scenarios"
        data = sql.read_sql(q, conn, index_col="scn_id", coerce_float=False)
    else:
        q = """
        SELECT scn_id, datetime(scn_date,'localtime') as scn_date ,scn_name,scn_desc
        FROM scenarios NATURAL JOIN applications WHERE exec_name = ?
        """
        data = sql.read_sql(q, conn, index_col="scn_id", coerce_float=False, params=(app_name,))
    data["scn_date"] = pd.to_datetime(data["scn_date"], format="%Y-%m-%d %H:%M:%S")
    return data


def get_scenario_data(scn_id):
    conn = get_connection()
    q = "SELECT scn_data FROM scenarios WHERE scn_id = ?"
    res = conn.execute(q, (scn_id,))
    res = res.fetchone()
    if res is None:
        raise Exception("scenario not found")
    return res[0]


def link_var_scenario(var_idx, scn_idx):
    conn = get_connection()
    q = "INSERT INTO vars_scenarios VALUES (?,?)"
    conn.execute(q, (var_idx, scn_idx))
    conn.commit()


def get_variable_scenarios(var_idx):
    conn = get_connection()
    q = "SELECT scn_id,scn_name FROM scenarios NATURAL JOIN vars_scenarios WHERE var_idx = ?"
    cur = conn.execute(q, (var_idx,))
    return dict(cur.fetchall())


def count_variable_scenarios(var_idx):
    conn = get_connection()
    q = "SELECT count(*) FROM vars_scenarios WHERE var_idx == ?;"
    cur = conn.execute(q, (var_idx,))
    return cur.fetchone()[0]


def save_sub_sample(name, elements, description):
    name = str(name)
    description = str(description)
    size = len(elements)
    str_data = cPickle.dumps(elements, 2)
    str_data = buffer(str_data)
    conn = get_connection()
    q = "INSERT INTO subj_samples (sample_name, sample_desc, sample_data, sample_size) VALUES (?,?,?,?)"
    conn.execute(q, (name, description, str_data,size))
    conn.commit()
    pass