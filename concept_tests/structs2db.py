from __future__ import division
import braviz
from braviz.readAndFilter import tabular_data, geom_db
from braviz.interaction.structure_metrics import mean_inside
from multiprocessing import Pool
from functools import partial

__author__ = 'da.angulo39'

def struct2db(structs,subj):
    reader = braviz.readAndFilter.BravizAutoReader(max_cache=1000)
    measures = {"fa":"FA","md":"MD"}

    for m in measures:
        for s in structs:
            var_name = "bvz_str_"+s+"_"+m
            try:
                vi=tabular_data.register_new_variable(var_name)
            except Exception:
                vi=tabular_data.get_var_idx(var_name)
            img = measures[m]
            var_id = vi
            try:
                v = mean_inside(reader,subj,s,img)
                print "%s \t %s \t %.3g"%(var_name,subj,v)
                tabular_data.updata_variable_value(var_id,subj,float(v))
            except Exception as e:
                print e.message
    reader.clear_mem_cache()


if __name__ == "__main__":
    subjs = [1026, 939, 9, 526, 15, 19, 535, 536, 537, 29, 542, 548, 549, 689, 552, 44, 861, 51, 1077, 566, 56, 576, 65, 579, 580, 69, 71, 592, 593, 83, 599, 600, 868, 602, 357, 610, 616, 619, 108, 623, 113, 630, 631, 121, 124, 125, 789, 128, 107, 876, 138, 651, 141, 143, 144, 145, 25, 665, 154, 156, 157, 670, 197, 675, 165, 625, 684, 173, 686, 175, 176, 177, 182, 185, 1212, 195, 1221, 198, 712, 201, 715, 205, 1232, 216, 804, 1242, 219, 221, 734, 225, 227, 1253, 230, 231, 232, 235, 1260, 237, 1265, 754, 761, 253, 256, 769, 263, 266, 783, 784, 984, 1049, 277, 790, 791, 292, 293, 806, 1320, 301, 1326, 815, 818, 307, 1333, 310, 313, 314, 1340, 829, 320, 54, 327, 840, 841, 331, 332, 1357, 848, 344, 346, 1338, 863, 353, 356, 869, 874, 364, 877, 878, 879, 369, 371, 884, 893, 894, 64, 390, 905, 906, 151, 912, 918, 153, 409, 413, 416, 417, 934, 423, 426, 427, 940, 429, 942, 431, 432, 935, 440, 954, 928, 452, 965, 966, 971, 333, 469, 982, 472, 478, 480, 483, 484, 485, 491, 1005, 1006, 595, 500, 504, 119, 1021]
    structs = ['wm-lh-inferiortemporal', 'wm-lh-precentral', 'wm-rh-inferiorparietal', 'CC_Anterior', 'CC_Central', 'CC_Mid_Anterior', 'CC_Mid_Posterior', 'CC_Posterior', 'wm-lh-insula', 'wm-lh-isthmuscingulate', 'wm-lh-lateraloccipital', 'wm-lh-lateralorbitofrontal', 'wm-lh-lingual', 'wm-lh-medialorbitofrontal', 'wm-lh-middletemporal', 'wm-lh-paracentral', 'wm-lh-parahippocampal', 'wm-lh-parsopercularis', 'wm-lh-parsorbitalis', 'wm-lh-parstriangularis', 'wm-lh-pericalcarine', 'wm-lh-postcentral', 'wm-lh-posteriorcingulate', 'wm-lh-precuneus', 'wm-lh-rostralanteriorcingulate', 'wm-lh-rostralmiddlefrontal', 'wm-lh-superiorfrontal', 'wm-lh-superiorparietal', 'wm-lh-superiortemporal', 'wm-lh-supramarginal', 'wm-lh-temporalpole', 'wm-lh-transversetemporal', 'wm-rh-bankssts', 'wm-rh-caudalanteriorcingulate', 'wm-rh-caudalmiddlefrontal', 'wm-rh-cuneus', 'wm-rh-entorhinal', 'wm-rh-frontalpole', 'wm-rh-fusiform', 'wm-rh-inferiortemporal', 'wm-rh-insula', 'wm-rh-isthmuscingulate', 'wm-rh-lateraloccipital', 'wm-rh-lateralorbitofrontal', 'wm-rh-lingual', 'wm-rh-medialorbitofrontal', 'wm-rh-middletemporal', 'wm-rh-paracentral', 'wm-rh-parahippocampal', 'wm-rh-parsopercularis', 'wm-rh-parsorbitalis', 'wm-rh-parstriangularis', 'wm-rh-pericalcarine', 'wm-rh-postcentral', 'wm-rh-posteriorcingulate', 'wm-rh-precentral', 'wm-rh-precuneus', 'wm-rh-rostralanteriorcingulate', 'wm-rh-rostralmiddlefrontal', 'wm-rh-superiorfrontal', 'wm-rh-superiorparietal', 'wm-rh-superiortemporal', 'wm-rh-supramarginal', 'wm-rh-temporalpole', 'wm-rh-transversetemporal', 'wm-lh-bankssts', 'wm-lh-caudalanteriorcingulate', 'wm-lh-caudalmiddlefrontal', 'wm-lh-cuneus', 'wm-lh-entorhinal', 'wm-lh-frontalpole', 'wm-lh-fusiform', 'wm-lh-inferiorparietal']


    pool=Pool(3)
    f= partial(struct2db,structs)
    pool.map(f,subjs,10)





