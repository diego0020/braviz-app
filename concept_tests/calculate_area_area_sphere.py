from __future__ import division
import numpy as np
from braviz.readAndFilter import tabular_data


__author__ = 'da.angulo39'


def shape_factor(volume_array,area_array):
    curv_array = area_array/np.power((36*np.pi*np.square(volume_array)),1/3)
    return curv_array


def test():
    structs=['lh-entorhinal', 'lh-postcentral', 'rh-cuneus', 'rh-posteriorcingulate', 'lh-bankssts', 'lh-caudalanteriorcingulate', 'lh-caudalmiddlefrontal', 'lh-cuneus', 'rh-precentral', 'rh-precuneus', 'rh-rostralanteriorcingulate', 'rh-rostralmiddlefrontal', 'rh-superiorfrontal', 'rh-superiorparietal', 'rh-superiortemporal', 'rh-supramarginal', 'rh-temporalpole', 'rh-transversetemporal', 'rh-unknown', 'lh-frontalpole', 'lh-fusiform', 'lh-inferiorparietal', 'lh-inferiortemporal', 'lh-insula', 'lh-isthmuscingulate', 'lh-lateraloccipital', 'lh-lateralorbitofrontal', 'lh-lingual', 'lh-medialorbitofrontal', 'lh-middletemporal', 'lh-paracentral', 'lh-parahippocampal', 'lh-parsopercularis', 'lh-parsorbitalis', 'lh-parstriangularis', 'lh-pericalcarine', 'lh-posteriorcingulate', 'lh-precentral', 'lh-precuneus', 'lh-rostralanteriorcingulate', 'lh-rostralmiddlefrontal', 'lh-superiorfrontal', 'lh-superiorparietal', 'lh-superiortemporal', 'lh-supramarginal', 'lh-temporalpole', 'lh-transversetemporal', 'lh-unknown', 'rh-bankssts', 'rh-caudalanteriorcingulate', 'rh-caudalmiddlefrontal', 'rh-entorhinal', 'rh-frontalpole', 'rh-fusiform', 'rh-inferiorparietal', 'rh-inferiortemporal', 'rh-insula', 'rh-isthmuscingulate', 'rh-lateraloccipital', 'rh-lateralorbitofrontal', 'rh-lingual', 'rh-medialorbitofrontal', 'rh-middletemporal', 'rh-paracentral', 'rh-parahippocampal', 'rh-parsopercularis', 'rh-parsorbitalis', 'rh-parstriangularis', 'rh-pericalcarine', 'rh-postcentral'];
    df_out = tabular_data.get_data_frame_by_name([])
    for struct in structs:
        struct = struct.replace("-","_")
        area="GMPARC_%s_area"%struct
        volume="GMPARC_%s_volume"%struct
        out_var="JTHP-shape-%s"%struct
        df=tabular_data.get_data_frame_by_name((area,volume))
        print df.head()
        res=shape_factor(df[volume],df[area])
        print out_var
        df_out[out_var]=res
    print df_out.to_excel(r"C:\Users\da.angulo39\Documents\test.xlsx",merge_cells=False)

if __name__ == "__main__":
    test()