
from braviz.readAndFilter.tabular_data import _get_connection
from itertools import izip
__author__ = 'Diego'

def create_braint_db():
    conn = _get_connection()
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
    (origin_id INTEGER REFERENCES braint_var(var_id) ON DELETE CASCADE,
    destination_id INTEGER REFERENCES braint_var(var_id) ON DELETE CASCADE,
    counter INTEGER,
    UNCLEAR INTEGER,
    UNIQUE (origin_id,destination_id)
    )
    """
    conn.execute(q)
    q="""CREATE TABLE IF NOT EXISTS braint_tab
    (braint_var_id INTEGER PRIMARY KEY REFERENCES braint_var(var_id),
    tab_var_id INTEGER REFERENCES variables(var_idx)
    )
    """
    conn.execute(q)
    conn.commit()
    hierarchy = ["Evaluation", "Test", "SubTest", "SubSubTest", "SubSubSubTest"]
    q="INSERT OR IGNORE INTO hierarchy_levels VALUES (?,?)"
    conn.executemany(q,((i+1,l) for i,l in enumerate(hierarchy)))
    conn.commit()






