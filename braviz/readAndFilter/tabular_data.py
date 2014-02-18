__author__ = 'Diego'

import pandas
import sqlite3
from pandas.io import sql
import os

def get_variables(reader=None):

    conn=get_connection(reader)
    data=sql.read_sql("SELECT var_name from variables;",conn)
    conn.close()
    return data

def get_connection(reader=None):
    if reader is None:
        from braviz.readAndFilter import kmc40AutoReader
        reader=kmc40AutoReader()
    path=os.path.join(reader.getDataRoot(),"braviz_data","tabular_data.sqlite")
    conn=sqlite3.connect(path)
    return conn