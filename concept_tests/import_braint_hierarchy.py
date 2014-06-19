__author__ = 'Diego'
import os
from braviz.utilities import remove_non_ascii
from braviz.readAndFilter import braint_db
os.chdir(r"C:\Users\Diego\Dropbox\Base Uniandes\18-Junio")
last_in_level = {0 : None}
with open("Jerarquia.csv") as jer_file:
    for line in jer_file:
        tokens = line.split(";")
        for i,t in enumerate(tokens):
            t2 = remove_non_ascii(t)
            t2 = t2.rstrip().lstrip()

            if len(t2)>0:
                print "%s : father %s"%(t2,last_in_level[i])
                braint_db.add_variable(last_in_level[i],t2)
                v_id=braint_db.get_var_id(t2)
                last_in_level[i+1]=v_id




# link with tab_sata
q="""
INSERT or IGNORE into braint_tab
SELECT braint_var.var_id as braint_var_id, variables.var_idx as tab_var_id
FROM variables join braint_var WHERE variables.var_name = braint_var.label
"""