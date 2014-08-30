from __future__ import division
import braviz
from braviz.readAndFilter import tabular_data, bundles_db
from braviz.interaction.structure_metrics import get_scalar_from_fiber_ploydata


__author__ = 'da.angulo39'

def track2db(track_id):
    reader = braviz.readAndFilter.BravizAutoReader()
    track_name = bundles_db.get_bundle_name(track_id)
    measures = {"fa":("fa_p","mean_color"),"md":("md_p","mean_color"),"length":("fa_p","mean_length")}
    subjects = tabular_data.get_subjects()[:10]
    for m in measures:
        scalar,operation = measures[m]
        var_name = track_name+"_"+m
        for subj in subjects:
            img_code = tabular_data.get_var_value(tabular_data.IMAGE_CODE,subj)
            try:
                fibs = reader.get("fibers",img_code,db_id=track_id,scalars=scalar)
                v = get_scalar_from_fiber_ploydata(fibs,operation)
                print "%s \t %s \t %.3g"%(var_name,subj,v)
            except Exception:
                pass

if __name__ == "__main__":
    track2db(8)


