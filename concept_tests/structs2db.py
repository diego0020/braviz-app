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
    tuples = []

    for m in measures:
        for s in structs:
            var_name = "bvz_str_"+s+"_"+m
            vi=tabular_data.get_var_idx(var_name)
            img = measures[m]
            var_id = vi
            try:
                v = mean_inside(reader,subj,s,img)
                print "%s \t %s \t %.3g"%(var_name,subj,v)
                #tabular_data.updata_variable_value(var_id,subj,float(v))
                tuples.append((var_id,subj,float(v)))
            except Exception as e:
                print e.message
    reader.clear_mem_cache()
    written = False
    while not written:
        try:
            tabular_data.update_multiple_variable_values(tuples)
        except Exception as e:
            print "sleeping"
        else:
            written = True

def get_variables(structs):
    name2code = {}
    measures = {"fa":"FA","md":"MD"}

    for m in measures:
        for s in structs:
            var_name = "bvz_str_"+s+"_"+m
            vi=tabular_data.get_var_idx(var_name)
            name2code[var_name]=vi
            if vi is None:
                print "-\t %s"%var_name
            else:
                print "%d:\t %s"%(vi,var_name)

    return name2code

def reset_variables(vars):
    for var_name,var_code in vars.iteritems():
        if var_code is not None:
            #delete old variable
            tabular_data.recursive_delete_variable(var_code)
        tabular_data.register_new_variable(var_name)

if __name__ == "__main__":
    import sys
    try:
        n_procs = int(sys.argv[1])
    except Exception:
        n_procs = 4
    subjs = [ 8, 9, 15, 19, 25, 29, 31, 35, 44, 51, 53, 54, 56, 64, 65, 69, 71, 72, 73, 75, 83, 90, 93, 95, 107, 108, 113, 119, 121, 123, 124, 125, 128, 129, 134, 138, 141, 143, 144, 145, 149, 151, 153, 154, 156, 157, 161, 165, 172, 173, 175, 176, 177, 182, 185, 186, 195, 197, 198, 201, 202, 205, 208, 210, 212, 216, 219, 221, 225, 227, 230, 231, 232, 235, 237, 253, 256, 259, 261, 263, 264, 266, 277, 288, 292, 293, 300, 301, 304, 307, 310, 312, 313, 314, 319, 320, 322, 327, 331, 332, 333, 344, 346, 348, 353, 355, 356, 357, 358, 364, 369, 371, 374, 381, 390, 396, 399, 402, 409, 413, 416, 417, 423, 424, 426, 427, 429, 431, 432, 440, 452, 456, 458, 464, 469, 472, 478, 480, 483, 484, 485, 491, 496, 499, 504, 517, 526, 532, 535, 536, 537, 542, 544, 545, 547, 548, 549, 552, 566, 568, 576, 577, 579, 580, 592, 593, 595, 598, 599, 600, 602, 610, 611, 615, 616, 619, 623, 625, 630, 631, 645, 650, 651, 662, 665, 670, 675, 678, 684, 686, 689, 691, 694, 696, 712, 715, 734, 739, 748, 752, 754, 761, 765, 769, 783, 784, 786, 789, 790, 791, 795, 799, 804, 806, 815, 818, 821, 829, 840, 841, 848, 850, 861, 863, 868, 869, 874, 876, 877, 878, 879, 884, 891, 892, 893, 894, 898, 905, 906, 912, 913, 914, 918, 928, 934, 935, 939, 940, 942, 953, 954, 965, 966, 971, 982, 984, 992, 994, 996, 1005, 1006, 1021, 1026, 1039, 1049, 1063, 1076, 1077, 1212, 1213, 1218, 1221, 1224, 1227, 1232, 1234, 1237, 1239, 1242, 1244, 1247, 1249, 1251, 1253, 1260, 1262, 1265, 1267, 1268, 1269, 1271, 1278, 1283, 1291, 1304, 1318, 1320, 1322, 1326, 1333, 1336, 1337, 1338, 1340, 1357, ]
    structs = ['wm-lh-inferiortemporal', 'wm-lh-precentral', 'wm-rh-inferiorparietal', 'CC_Anterior', 'CC_Central', 'CC_Mid_Anterior', 'CC_Mid_Posterior', 'CC_Posterior', 'wm-lh-insula', 'wm-lh-isthmuscingulate', 'wm-lh-lateraloccipital', 'wm-lh-lateralorbitofrontal', 'wm-lh-lingual', 'wm-lh-medialorbitofrontal', 'wm-lh-middletemporal', 'wm-lh-paracentral', 'wm-lh-parahippocampal', 'wm-lh-parsopercularis', 'wm-lh-parsorbitalis', 'wm-lh-parstriangularis', 'wm-lh-pericalcarine', 'wm-lh-postcentral', 'wm-lh-posteriorcingulate', 'wm-lh-precuneus', 'wm-lh-rostralanteriorcingulate', 'wm-lh-rostralmiddlefrontal', 'wm-lh-superiorfrontal', 'wm-lh-superiorparietal', 'wm-lh-superiortemporal', 'wm-lh-supramarginal', 'wm-lh-temporalpole', 'wm-lh-transversetemporal', 'wm-rh-bankssts', 'wm-rh-caudalanteriorcingulate', 'wm-rh-caudalmiddlefrontal', 'wm-rh-cuneus', 'wm-rh-entorhinal', 'wm-rh-frontalpole', 'wm-rh-fusiform', 'wm-rh-inferiortemporal', 'wm-rh-insula', 'wm-rh-isthmuscingulate', 'wm-rh-lateraloccipital', 'wm-rh-lateralorbitofrontal', 'wm-rh-lingual', 'wm-rh-medialorbitofrontal', 'wm-rh-middletemporal', 'wm-rh-paracentral', 'wm-rh-parahippocampal', 'wm-rh-parsopercularis', 'wm-rh-parsorbitalis', 'wm-rh-parstriangularis', 'wm-rh-pericalcarine', 'wm-rh-postcentral', 'wm-rh-posteriorcingulate', 'wm-rh-precentral', 'wm-rh-precuneus', 'wm-rh-rostralanteriorcingulate', 'wm-rh-rostralmiddlefrontal', 'wm-rh-superiorfrontal', 'wm-rh-superiorparietal', 'wm-rh-superiortemporal', 'wm-rh-supramarginal', 'wm-rh-temporalpole', 'wm-rh-transversetemporal', 'wm-lh-bankssts', 'wm-lh-caudalanteriorcingulate', 'wm-lh-caudalmiddlefrontal', 'wm-lh-cuneus', 'wm-lh-entorhinal', 'wm-lh-frontalpole', 'wm-lh-fusiform', 'wm-lh-inferiorparietal']
    vars_dict = get_variables(structs)
    reset_variables(vars_dict)
    vars_dict = get_variables(structs)

    pool=Pool(n_procs)
    f= partial(struct2db,structs)
    pool.map(f,subjs,10)





