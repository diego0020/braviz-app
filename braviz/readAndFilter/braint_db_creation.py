##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################

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






