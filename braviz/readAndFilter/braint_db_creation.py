from braviz.readAndFilter.tabular_data import get_connection
from itertools import izip
__author__ = 'Diego'

def create_braint_db():
    conn = get_connection()
    q="""CREATE TABLE IF NOT EXISTS hierarchy_levels
      (level_id INTEGER PRIMARY KEY ,
      level_name TEXT)"""
    conn.execute(q)
    q="""CREATE TABLE IF NOT EXISTS braint_var
      (var_id INTEGER PRIMARY KEY ,
      label TEXT,
      father INT,
      level REFERENCES hierarchy_levels(level_id)
      )"""
    conn.execute(q)
    q="""CREATE TABLE IF NOT EXISTS relations
    (origin_id REFERENCES braint_var(var_id),
    destination_id REFERENCES braint_vat(var_id),
    counter INTEGER,
    UNCLEAR INTEGER,
    PRIMARY KEY (origin_id,destination_id)
    )
    """
    conn.execute(q)
    q="""CREATE TABLE IF NOT EXISTS braint_tab
    (braint_var_id INTEGER PRIMARY KEY REFERENCES braint_var(var_id),
    tab_var_id INTEGER UNIQUE REFERENCES variables(var_id)
    )
    """
    conn.execute(q)
    conn.commit()
    hierarchy = ["Evaluation", "Test", "SubTest", "SubSubTest", "SubSubSubTest"]
    q="INSERT OR IGNORE INTO hierarchy_levels VALUES (?,?)"
    conn.executemany(q,((i+1,l) for i,l in enumerate(hierarchy)))
    conn.commit()






