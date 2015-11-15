from __future__ import division

import braviz
from braviz.readAndFilter import tabular_data

def check_max_min():
    all_vars = tabular_data.get_variables_and_type()
    real_vars = all_vars.index[all_vars["is_real"]>0]
    for v in real_vars:
        df = tabular_data.get_data_frame_by_index(v)
        s = df.iloc[:,0].dropna()
        if len(s) == 0:
            continue
            # No values
        values_min, values_max = s.min(), s.max()
        db_min, db_max = tabular_data.get_min_max_values(v)

        if values_min < db_min:
            print("possible min problem with %d"%v)

        if values_max < db_max:
            print("possible max problem with %d"%v)


        if (db_max != db_min) and not (0.1<(values_max - values_min)/(db_max-db_min)<10):
            print("possible range problem with %d"%v)

if __name__ == "__main__":
    check_max_min()
