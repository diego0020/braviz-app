__author__ = 'Diego'

import pandas
import sqlite3
from pandas.io import sql
import os
import pandas as pd

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

def get_data_frame(columns,reader=None):
    if type(columns) in (str,unicode):
        columns=(columns,)
    conn=get_connection(reader)
    data=col=sql.read_sql("SELECT subject from SUBJECTS",conn,index_col="subject")
    for var in columns:
        query="""SELECT subject, value
        FROM subjects NATURAL JOIN var_values
        WHERE var_idx = (SELECT var_idx FROM variables WHERE var_name = ?)
        """
        col=sql.read_sql(query,conn,index_col="subject",params=(var,),coerce_float=True)
        data[var]=col.astype(pd.np.float64)

    conn.close()
    return data