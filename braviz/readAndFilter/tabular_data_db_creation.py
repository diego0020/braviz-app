##############################################################################
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


from __future__ import division, print_function

__author__ = 'Diego'

import pandas as pd
import StringIO
import os
import sqlite3
import braviz.readAndFilter.tabular_data


def read_csv_file(path=None):
    if path is None:
        import braviz

        dummy_reader = braviz.readAndFilter.BravizAutoReader()
        path = os.path.join(dummy_reader.get_data_root(), "test_small.csv")
    # Replace , for .
    with open(path) as csv_file:
        file_buffer = csv_file.read()
    file_buffer = file_buffer.replace(',', '.')
    file_s_io = StringIO.StringIO(file_buffer)
    data = pd.read_csv(file_s_io, sep=";", header=0, index_col="code", na_values="#NULL!", keep_default_na=True,
                       encoding='latin-1', dtype={"code": object})
    return data


def create_directories():
    import os
    path = os.path.join(
        braviz.readAndFilter.braviz_auto_dynamic_data_root(), "braviz_data")
    try:
        os.mkdir(path)
    except Exception:
        pass
    scenarios = os.path.join("scenarios")
    try:
        os.mkdir(scenarios)
    except Exception:
        pass


def create_data_base(path=None, conn=None):
    if path is None:
        import braviz
        path = os.path.join(braviz.readAndFilter.braviz_auto_dynamic_data_root(
        ), "braviz_data", "tabular_data.sqlite")

    if conn is None:
        conn = sqlite3.connect(path)

    # enable foreign keys
    conn.execute("PRAGMA foreign_keys= ON;")
    conn.execute("pragma case_sensitive_like=ON;")
    # create subjects table
    query = """CREATE TABLE IF NOT EXISTS subjects
    (subject INTEGER PRIMARY KEY);
    """
    conn.execute(query)
    conn.commit()

    # create variables table
    query = """CREATE TABLE IF NOT EXISTS variables
    (var_idx INTEGER PRIMARY KEY,
    var_name  TEXT UNIQUE,
    is_real INTEGER -- 0 if nominal, 1 if real
    );
    """
    conn.execute(query)
    conn.commit()

    # create nominal variables meta data
    query = """
    CREATE TABLE IF NOT EXISTS nom_meta
    (var_idx INTEGER REFERENCES variables(var_idx),
    label INTEGER,
    name TEXT,
    PRIMARY KEY (var_idx,label)
    );
    """
    conn.execute(query)
    conn.commit()
    query = """
    CREATE INDEX IF NOT EXISTS nominal_var_idx ON nom_meta(var_idx);
    """
    conn.execute(query)
    conn.commit()

    # create rational variables meta data
    query = """
    CREATE TABLE IF NOT EXISTS ratio_meta
    (var_idx INTEGER REFERENCES variables(var_idx),
    min_val REAL,
    max_val REAL,
    optimum_val REAL,
    PRIMARY KEY (var_idx)
    );
    """
    conn.execute(query)
    conn.commit()

    # create values table
    query = """
    CREATE TABLE IF NOT EXISTS var_values
    (var_idx INTEGER REFERENCES variables(var_idx),
    subject INTEGER REFERENCES subjects(subject),
    value NUMERIC,
    PRIMARY KEY (var_idx,subject)
    );
    """
    conn.execute(query)
    conn.commit()

    query = """
    CREATE INDEX IF NOT EXISTS subj_value_idx ON var_values(subject);
    """
    conn.execute(query)
    conn.commit()

    query = """
    CREATE INDEX IF NOT EXISTS var_value_idx ON var_values(var_idx);
    """
    conn.execute(query)
    conn.commit()

    # create variable description table
    query = """
    CREATE TABLE IF NOT EXISTS var_descriptions
    (var_idx INTEGER REFERENCES variables(var_idx) PRIMARY KEY,
    description TEXT )
    ;
    """
    conn.execute(query)

    conn.commit()


def populate_db_from_csv(csv_file, db_file):
    data = read_csv_file(csv_file)
    conn = sqlite3.connect(db_file)

    # populate subjects:

    subjects = data.index
    subj_iter = ((str(i),) for i in subjects)
    conn.executemany("INSERT OR IGNORE INTO subjects VALUES (?)", subj_iter)
    conn.commit()

    # populate variables
    columns = data.columns
    conn.executemany(
        "INSERT OR IGNORE INTO variables(var_name) VALUES (?)", ((c,) for c in columns))
    conn.commit()

    # populate values
    for var_name in data.columns:
        str_iter = ((var_name, str(k), str(v))
                    for k, v in data[var_name].iterkv())
        query = """INSERT OR IGNORE INTO var_values VALUES
        ( (select var_idx from variables where var_name = ? ) ,?,?)"""
        conn.executemany(query, str_iter)
    conn.commit()

    # image_codes
    query = """INSERT INTO variables (var_name, is_real) VALUES ("Images_codes",1)"""
    conn.execute(query)

    tuples = ((s, s) for s in subjects)

    query = """INSERT OR REPLACE INTO var_values (var_idx,subject,value)
        VALUES ( (SELECT var_idx FROM variables WHERE var_name = "Images_codes"),
        ? , ?)"""
    conn.executemany(query, tuples)
    manual_fixes = [(812, 182)]
    conn.executemany(query, manual_fixes)
    conn.commit()


def tms_vars_descriptions():
    description_tuples = [
        (258, r"Excitability (Basic level = 100% - motor threshold)"),
        (259, r"Excitability (Basic level = 100% - motor threshold)"),
        (260, r"Synchronization (Corticospinal efficiency, msec)"),
        (261, r"Synchronization (Corticospinal efficiency, msec)"),
        (248, r"Level of Inhibition (GABAa synapses = 100% - cond*100/test)"),
        (249, r"Level of Inhibition (GABAa synapses = 100% - cond*100/test)"),
        (250,
         r"Level of Facilitation (Glumatate synapses = cond*100/test - 100%)"),
        (251,
         r"Level of Facilitation (Glumatate synapses = cond*100/test - 100%)"),
        (262,
         r"Frequency (frequency of observation of an inhibition triggered by the other hemisphere)"),
        (263,
         r"Frequency (frequency of observation of an inhibition triggered by the other hemisphere)"),
        (252,
         r"Transfer time (time for the transfer of the inhibition triggered by the other hemisphere)"),
        (253,
         r"Transfer time (time for the transfer of the inhibition triggered by the other hemisphere)"),
        (254,
         r"Duration (duration of the inhibition triggered by the other hemisphere)"),
        (255,
         r"Duration (duration of the inhibition triggered by the other hemisphere)"),
    ]
    conn = braviz.readAndFilter.tabular_data._get_connection()
    q = """INSERT OR REPLACE INTO var_descriptions (var_idx,description)
        VALUES (?,? )"""
    conn.executemany(q, description_tuples)
    conn.commit()


if __name__ == "__main__":
    print("This module shouldn't be excecuted")
