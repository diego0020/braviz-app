
from __future__ import division

__author__ = 'Diego'

from pandas.io import sql
import pandas as pd
import cPickle
import logging
import os
import braviz.readAndFilter
from braviz.readAndFilter.tabular_data import _get_connection
import sqlite3



def save_scenario(application, scenario_name, scenario_description, scenario_data):
    """
    Save application state

    Args:
        application (str) : Name of application script (without extension)
        scenario_name (str) : Name for the scenario
        scenario_description (str) : Description for the scenario
        scenario_data (dict) : Appliation state

    Returns:
        The database id of the saved scenario. Use this to save the corresponding screen-shot

    """
    if not isinstance(scenario_data,basestring):
        scenario_data=cPickle.dumps(scenario_data,2)
    scenario_data = buffer(scenario_data)
    conn = _get_connection()
    q = """INSERT  OR ABORT INTO scenarios
    (app_idx,scn_name,scn_desc,scn_data)
    VALUES ( (SELECT app_idx FROM applications WHERE exec_name == ?),
    ?,?,?)"""
    cur = conn.execute(q, (application, scenario_name, scenario_description, scenario_data))
    conn.commit()
    res = cur.lastrowid
    return res


def update_scenario(scenario_id, name=None, description=None, scenario_data=None, application=None):
    """
    Update scenario information in the database

    Args:
        scenario_id (int) : Scenario id
        name (str) : Optional, new name for the scenario
        description (str) : Optional, new description for the scenario
        scenario_data (dict) : Optional, new application state dictionary
        application (str) : Optional, new application script name, without extension
    """
    conn = _get_connection()
    if name is not None:
        conn.execute("UPDATE scenarios SET scn_name = ? WHERE scn_id = ?", (name, scenario_id))
    if description is not None:
        conn.execute("UPDATE scenarios SET scn_desc = ? WHERE scn_id = ?", (description, scenario_id))
    if scenario_data is not None:
        scenario_data = buffer(cPickle.dumps(scenario_data))
        conn.execute("UPDATE scenarios SET scn_data = ? WHERE scn_id = ?", (scenario_data, scenario_id))
    if application is not None:
        q = "UPDATE scenarios SET app_idx = (SELECT app_idx FROM applications WHERE exec_name == ?) WHERE scn_id = ?"
        conn.execute(q, (application, scenario_id))
    conn.commit()


def get_scenarios_data_frame(app_name=None):
    """
    Get available scenarios

    Args:
        app_name (str) : Optional, restrict list to a given application, it should be the base name of the
            application script
    Returns:
        :class:`~pandas.DataFrame` with columns for date, name and description. The index will be scenario indexes
    """
    conn = _get_connection()
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


def _get_scenario_data(scn_id):
    conn = _get_connection()
    q = "SELECT scn_data FROM scenarios WHERE scn_id = ?"
    res = conn.execute(q, (scn_id,))
    res = res.fetchone()
    if res is None:
        log = logging.getLogger(__name__)
        log.error("scenario not found")
        raise Exception("scenario not found")
    return res[0]

def get_scenario_data_dict(scn_id):
    """
    Get application state dict from the database

    Args:
        scn_id (int) : Scenario id

    Returns:
        Dictionary with application state
    """
    res = _get_scenario_data(scn_id)
    scn_dict = cPickle.loads(str(res))
    return scn_dict

def link_var_scenario(var_idx, scn_idx):
    """
    Links a variable to a scenario

    Args:
        var_idx (int) : Variable index
        scn_idx (int) : Scenario index
    """
    conn = _get_connection()
    q = "INSERT INTO vars_scenarios VALUES (?,?)"
    conn.execute(q, (var_idx, scn_idx))
    conn.commit()


def get_variable_scenarios(var_idx):
    """
    Get scenarios linked to a variable

    Args:
        var_idx (int) : Variable index

    Returns:
        A dictionary whose keys are scenario ids and values are scenario_names for scenarios linked to the
            given variable
    """
    conn = _get_connection()
    q = "SELECT scn_id,scn_name FROM scenarios NATURAL JOIN vars_scenarios WHERE var_idx = ?"
    cur = conn.execute(q, (var_idx,))
    return dict(cur.fetchall())


def count_variable_scenarios(var_idx):
    """
    Get the amount of scenarios linked to a given variable

    Args:
        var_idx (int) : Variable index

    Returns:
        The number of scenarios linked to the given variable
    """
    conn = _get_connection()
    q = "SELECT count(*) FROM vars_scenarios WHERE var_idx == ?;"
    cur = conn.execute(q, (var_idx,))
    return cur.fetchone()[0]


def save_sub_sample(name, elements, description):
    """
    Save a sub sample into the database

    Args:
        name (str) : Name for the subsample
        elements (set) : Subjects in the subsample
        description (str) : Description of the subsample
    """
    name = str(name)
    description = str(description)
    size = len(elements)
    str_data = cPickle.dumps(elements, 2)
    str_data = buffer(str_data)
    conn = _get_connection()
    q = "INSERT INTO subj_samples (sample_name, sample_desc, sample_data, sample_size) VALUES (?,?,?,?)"
    conn.execute(q, (name, description, str_data,size))
    conn.commit()


def get_comment(subj):
    """
    Retrieve the comment about a subject

    Args:
        subj : Subject id

    Returns:
        A string with the comment about the subject
    """
    conn = _get_connection()
    q = "SELECT comment FROM subj_comments WHERE subject = ?"
    cur = conn.execute(q,(subj,))
    res = cur.fetchone()
    if res is None:
        return ""
    return res[0]

def update_comment(subj,comment):
    """
    Update the comment about a subject

    Args:
        subj : Subject id
        comment (str) : subject comment

    """
    conn = _get_connection()
    q = "INSERT OR REPLACE into subj_comments (subject,comment) VALUES (?,?)"
    with conn:
        cur = conn.execute(q,(subj,comment))


def get_samples_df():
    """
    Get available samples

    Returns:
        A class:`~pandas.DataFrame` with columns for sample name, sample description, and sample size;
         indexed by the sample index

    """
    conn = _get_connection()
    q = "SELECT sample_idx, sample_name, sample_desc, sample_size FROM subj_samples"
    data = sql.read_sql(q, conn, index_col="sample_idx", coerce_float=False)
    return data

def sample_name_existst(sample_name):
    """
    Check if a sample with a given name exists

    Args:
        sample_name (str) : Sample name

    Returns:
        ``True`` if a sample with this name exists in the database, ``False`` otherwise.
    """
    conn = _get_connection()
    q="SELECT count(*) FROM subj_samples WHERE sample_name = ?"
    cur = conn.execute(q,(sample_name,))
    res = cur.fetchone()
    return res[0] > 0

def get_sample_data(sample_idx):
    """
    Retrieve the sample data from the database

    Args:
        sample_idx (int) :  Sample id

    Returns:
        The set of subjects in the sample
    """
    conn=_get_connection()
    q = "SELECT sample_data FROM subj_samples WHERE sample_idx = ?"
    cur = conn.execute(q,(sample_idx,))
    res = cur.fetchone()
    if res is None:
        raise Exception("Invalid sample index")
    data_str = res[0]
    data = cPickle.loads(str(data_str))
    return data

def delete_scenario(scn_id):
    """
    Delete a scenario from the database

    It is also unlinked from variables, and if a screenshot is found it is deleted. This is not reversible.

    Args:
        scn_id (int) :  Scenario id

    """
    conn = _get_connection()
    try:
        with conn:
            #delete vars_scenarios
            q = "DELETE FROM vars_scenarios WHERE scn_id = ?"
            conn.execute(q,(scn_id,))
            #delete scenario
            q = "DELETE FROM scenarios WHERE scn_id = ?"
            conn.execute(q,(scn_id,))
    except sqlite3.IntegrityError as e:
        print e
        print "DataBase not modified"
        raise
    else:
        #delete screenshot
        scenario_dir = os.path.join(braviz.readAndFilter.braviz_auto_dynamic_data_root(),"braviz_data","scenarios")
        scenario_name = "scenario_%d.png"%scn_id
        full_name = os.path.join(scenario_dir,scenario_name)
        print full_name
        if os.path.isfile(full_name):
            os.remove(full_name)
