from __future__ import division

__author__ = 'Diego'

from pandas.io import sql
import pandas as pd

from braviz.readAndFilter.tabular_data import get_connection


def save_scenario(application,scenario_name,scenario_description,scenario_data):
    """
    application: Name of executable
    scenario_name :  Name for the current scenario, may already exist, the date will differentiate them
    scenario_description: Description of the current scenario
    scenario_data : Binary data for the current scenario
    """
    conn = get_connection()
    q="""INSERT  OR ABORT INTO scenarios
    (app_idx,scn_name,scn_desc,scn_data)
    VALUES ( (SELECT app_idx FROM applications WHERE exec_name == ?),
    ?,?,?)"""

    conn.execute(q,(application,scenario_name,scenario_description,scenario_data))
    conn.commit()

def get_scenarios_data_frame(app_name):
    conn = get_connection()
    q="""
    SELECT scn_id, datetime(scn_date,'localtime') as scn_date ,scn_name,scn_desc FROM scenarios NATURAL JOIN applications WHERE exec_name = ?
    """
    data = sql.read_sql(q, conn, index_col="scn_id",coerce_float=False,params=(app_name,))
    data["scn_date"] = pd.to_datetime(data["scn_date"],format="%Y-%m-%d %H:%M:%S")
    return data

def get_scenario_data(scn_id):
    conn = get_connection()
    q = "SELECT scn_data FROM scenarios WHERE scn_id = ?"
    res = conn.execute(q,(scn_id,))
    res = res.fetchone()
    if res is None:
        raise Exception("scenario not found")
    return res[0]
