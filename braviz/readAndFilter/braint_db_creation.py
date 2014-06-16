from braviz.readAndFilter.tabular_data import get_connection

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
    (rel_id INTEGER PRIMARY KEY,
    origin_id REFERENCES braint_var(var_id),
    destination_id REFERENCES braint_vat(var_id),
    counter INTEGER,
    UNCLEAR INTEGER
    )
    """
    conn.execute(q)
    q="""CREATE TABLE IF NOT EXISTS braint_tab
    (braint_var_id REFERENCES braint_var(var_id),
    tab_var_id REFERENCES variables(var_id)
    )
    """
    conn.execute(q)
    conn.commit()





