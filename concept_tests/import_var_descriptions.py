import os
import pandas as pd
from braviz.readAndFilter import tabular_data
from braviz.utilities import remove_non_ascii
__author__ = 'Diego'

os.chdir(r"C:\Users\Diego\Dropbox\Base Uniandes\18-Junio")

df = pd.read_excel("Nombres_bonitos.xlsx",0)
df.dropna(inplace=True)


for i in xrange(len(df)):
    datum = df.iloc[i]
    name = remove_non_ascii(datum["name"])
    desc = remove_non_ascii(datum["desc"])
    if len(name)>0 and len(desc)>0:
        print "%s : %s"%(name,desc)
        try:
            tabular_data.save_var_description_by_name(name,desc)
            print "Found"
        except Exception:
            print "Not Found"
