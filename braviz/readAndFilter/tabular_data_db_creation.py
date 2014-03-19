from __future__ import division

__author__ = 'Diego'

import pandas as pd
import StringIO
import os
import sqlite3


def read_csv_file(path=None):
    if path is None:
        import braviz

        dummy_reader = braviz.readAndFilter.kmc40AutoReader()
        path = os.path.join(dummy_reader.getDataRoot(), "test_small.csv")
    #Replace , for .
    with open(path) as csv_file:
        file_buffer = csv_file.read()
    file_buffer = file_buffer.replace(',', '.')
    file_s_io = StringIO.StringIO(file_buffer)
    data = pd.read_csv(file_s_io, sep=";", header=0, index_col="code", na_values="#NULL!", keep_default_na=True,
                       encoding='latin-1', dtype={"code": object})
    return data


def create_data_base(path=None):
    if path is None:
        import braviz

        dummy_reader = braviz.readAndFilter.kmc40AutoReader()
        path = os.path.join(dummy_reader.getDataRoot(), "braviz_data", "tabular_data.sqlite")
    conn = sqlite3.connect(path)

    #enable foreign keys
    conn.execute("PRAGMA foreign_keys= ON;")
    #create subjects table
    query = """CREATE TABLE IF NOT EXISTS subjects
    (subject INTEGER PRIMARY KEY);
    """
    conn.execute(query)
    conn.commit()

    #create variables table
    query = """CREATE TABLE IF NOT EXISTS variables
    (var_idx INTEGER PRIMARY KEY,
    var_name  TEXT,
    is_real INTEGER -- 0 if nominal, 1 if real
    );
    """
    conn.execute(query)
    conn.commit()

    #create nominal variables meta data
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
    CREATE INDEX nominal_var_idx ON nom_meta(var_idx);
    """
    conn.execute(query)
    conn.commit()

    #create rational variables meta data
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

    #create values table
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
    CREATE INDEX subj_value_idx ON var_values(subject);
    """
    conn.execute(query)
    conn.commit()

    query = """
    CREATE INDEX var_value_idx ON var_values(var_idx);
    """
    conn.execute(query)
    conn.commit()

    #create variable description table
    query = """
    CREATE TABLE IF NOT EXISTS var_descriptions
    (var_idx INTEGER REFERENCES variables(var_idx) PRIMARY KEY,
    description TEXT )
    PRIMARY KEY (var_idx)
    );
    """
    conn.execute(query)

    conn.commit()


def populate_db_from_csv(csv_file, db_file):
    data = read_csv_file(csv_file)
    conn = sqlite3.connect(db_file)

    #populate subjects:

    subjects = data.index
    subj_iter = ( (str(i),) for i in subjects)
    conn.executemany("INSERT OR IGNORE INTO subjects VALUES (?)", subj_iter)
    conn.commit()

    #populate variables
    columns = data.columns
    conn.executemany("INSERT OR IGNORE INTO variables(var_name) VALUES (?)", ( (c,) for c in columns))
    conn.commit()

    #populate values
    for var_name in data.columns:
        str_iter = ((var_name, str(k), str(v)) for k, v in data[var_name].iterkv())
        query = """INSERT OR IGNORE INTO var_values VALUES
        ( (select var_idx from variables where var_name = ? ) ,?,?)"""
        conn.executemany(query, str_iter)
    conn.commit()


    #image_codes
    query="""INSERT INTO variables (var_name, is_real) VALUES ("Images_codes",1)"""
    conn.execute(query)

    tuples= ( (s,s) for s in subjects)

    query = """INSERT OR REPLACE INTO var_values (var_idx,subject,value)
        VALUES ( (SELECT var_idx FROM variables WHERE var_name = "Images_codes"),
        ? , ?)"""
    conn.executemany(query,tuples)
    manual_fixes=[(812,182)]
    conn.executemany(query,manual_fixes)
    conn.commit()








