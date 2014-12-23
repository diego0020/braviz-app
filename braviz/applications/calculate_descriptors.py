import braviz
import braviz.utilities
from braviz.interaction import descriptors, structure_metrics
import sqlite3
import os
import logging
from multiprocessing import Pool
__author__ = 'Diego'


def create_db(path):
    conn = sqlite3.connect(path)
    q = """CREATE TABLE IF NOT EXISTS descriptors
        (subject integer not null,
        structure text not null,
        volume real,
        area real,
        d1 real,
        d2 real,
        d3 real,
        primary key (subject,structure)
        )
        """
    conn.execute(q)
    conn.commit()

def get_descriptor(subj,structure,aseg,reader):
    vol = reader.get("MODEL",subj,volume=True,name=structure)
    area = structure_metrics.get_struct_metric(reader,structure,subj,"area")
    label = int(reader.get("MODEL",subj,name=structure,label=True))
    d1,d2,d3 = descriptors.get_descriptors(aseg,(label,))
    return vol,area,d1,d2,d3

def get_agg_descriptor(subj,structures,aseg,reader):
    vols = []
    labels = []
    for s in structures:
        vols.append(reader.get("MODEL",subj,volume=True,name=s))
        labels.append(int(reader.get("MODEL",subj,name=s,label=True)))
    d1,d2,d3 = descriptors.get_descriptors(aseg,labels)
    vol = sum(vols)
    return vol,float("nan"),d1,d2,d3

def save_descs_in_db(conn,subj,name,descs):
    vals = (int(subj),name,descs[0],descs[1],descs[2],descs[3],descs[4])
    q = "INSERT OR REPLACE into descriptors VALUES (?,?, ?,?, ?,?,?)"
    conn.execute(q,vals)
    conn.commit()



def save_subj_descs(subj):
    print "subject = %s"%subj
    braviz.utilities.configure_console_logger("descriptors")
    log = logging.getLogger(__name__)
    reader = braviz.readAndFilter.BravizAutoReader(max_cache=1000)
    db_name = os.path.join(reader.get_dyn_data_root(),"descriptors.sqlite")
    try:
        structs = reader.get("MODEL",subj,index=True)
        aseg = reader.get("APARC",subj,space="world")
        #wmaseg = reader.get("WMPARC",subj,space="world")
    except Exception as e:
        log.exception(e.message)
        return
    for s in structs:

        try:
            if s.startswith("wm-"):
                descs = None
                #skip wm
                #d1 =  get_descriptor(subj,s,wmaseg,reader)
            elif s.startswith("ctx-"):
                #continue
                # not skip ctx
                descs =  get_descriptor(subj,s,aseg,reader)
            else:
                descs =  get_descriptor(subj,s,aseg,reader)

        except Exception as e:
            log.exception(e.message)
            descs = None

        if descs is not None:
            try:
                conn = sqlite3.connect(db_name,timeout=600,isolation_level="EXCLUSIVE")
                save_descs_in_db(conn,subj,s,descs)
                conn.close()
            except Exception as e:
                log.exception(e)

    cc = ['CC_Anterior', 'CC_Central', 'CC_Mid_Anterior', 'CC_Mid_Posterior', 'CC_Posterior']
    try:
        d2 = get_agg_descriptor(subj,cc,aseg,reader)
        conn = sqlite3.connect(db_name,timeout=600,isolation_level="EXCLUSIVE")
        save_descs_in_db(conn,subj,"CC-Full",d2)
        conn.close()
    except Exception as e:
        log.exception(e)
    reader.clear_cache()

def save_for_all(processes=1):
    reader=braviz.readAndFilter.BravizAutoReader(max_cache=500)
    #ids=reader.get('ids')
    ids=[9, 15, 19, 25, 29, 44, 51, 54, 56, 64, 65, 69, 71, 83, 107, 108, 113, 119, 121, 124, 125, 128, 138, 141, 143, 144, 145, 151, 153, 154, 156, 157, 165, 173, 175, 176, 177, 182, 185, 195, 197, 198, 201, 205, 216, 219, 221, 225, 227, 230, 231, 232, 235, 237, 253, 256, 263, 266, 277, 292, 293, 301, 307, 310, 313, 314, 320, 327, 331, 332, 333, 344, 346, 353, 356, 357, 364, 369, 371, 390, 409, 413, 416, 417, 423, 426, 427, 429, 431, 432, 440, 452, 469, 472, 478, 480, 483, 484, 485, 491, 500, 504, 526, 535, 536, 537, 542, 548, 549, 552, 566, 576, 579, 580, 592, 593, 595, 599, 600, 602, 610, 616, 619, 623, 625, 630, 631, 651, 665, 670, 675, 684, 686, 689, 712, 715, 734, 754, 761, 769, 783, 784, 789, 790, 791, 804, 806, 815, 818, 829, 840, 841, 848, 861, 863, 868, 869, 874, 876, 877, 878, 879, 884, 893, 894, 905, 906, 912, 918, 928, 934, 935, 939, 940, 942, 954, 965, 966, 971, 982, 984, 1005, 1006, 1021, 1026, 1049, 1077, 1212, 1221, 1232, 1242, 1253, 1260, 1265, 1320, 1326, 1333, 1338, 1340, 1357]
    #use ids from luis email 17/12/14
    ids=[1005 ,  1006 ,  1021 ,  1026 ,  1039 ,  1049 ,  107 ,  1077 ,  108 ,  113 ,  119 ,  1190 ,  121 ,  1212 ,  1221 ,  123 ,  1232 ,  124 ,  1242 ,  125 ,  1253 ,  1260 ,  1265 ,  128 ,  129 ,  1320 ,  1326 ,  1333 ,  1338 ,  1340 ,  1357 ,  138 ,  141 ,  143 ,  144 ,  145 ,  15 ,  151 ,  153 ,  154 ,  156 ,  157 ,  165 ,  173 ,  175 ,  176 ,  177 ,  182 ,  185 ,  186 ,  19 ,  195 ,  197 ,  198 ,  2 ,  20 ,  201 ,  202 ,  205 ,  216 ,  219 ,  221 ,  225 ,  227 ,  230 ,  231 ,  232 ,  235 ,  237 ,  25 ,  253 ,  256 ,  259 ,  263 ,  264 ,  266 ,  277 ,  29 ,  292 ,  293 ,  300 ,  301 ,  307 ,  31 ,  310 ,  312 ,  313 ,  314 ,  319 ,  320 ,  322 ,  327 ,  331 ,  332 ,  333 ,  344 ,  346 ,  348 ,  35 ,  353 ,  355 ,  356 ,  357 ,  358 ,  364 ,  369 ,  371 ,  374 ,  381 ,  390 ,  396 ,  399  ,  409 ,  413 ,  416 ,  417 ,  423 ,  426 ,  427 ,  429 ,  431 ,  432 ,  44 ,  440 ,  447 ,  452 ,  456 ,  458 ,  464 ,  469 ,  472 ,  478 ,  480 ,  483 ,  484 ,  485 ,  491 ,  499 ,  500 ,  504 ,  51 ,  517 ,  526 ,  532 ,  535 ,  536 ,  537 ,  539 ,  54 ,  542 ,  544 ,  545 ,  547 ,  548 ,  549 ,  552 ,  559 ,  56 ,  566 ,  576 ,  579 ,  580 ,  592 ,  593 ,  595 ,  599 ,  600 ,  602 ,  610 ,  611 ,  616 ,  619 ,  623 ,  625 ,  630 ,  631 ,  64 ,  645 ,  65 ,  651 ,  662 ,  665 ,  670 ,  675 ,  684 ,  686 ,  689 ,  69 ,  696 ,  71 ,  712 ,  715 ,  72 ,  73 ,  730 ,  734 ,  754 ,  761 ,  765 ,  769 ,  783 ,  784 ,  786 ,  789 ,  790 ,  791 ,  804 ,  806 ,  815 ,  818 ,  821 ,  829 ,  83 ,  840 ,  841 ,  848 ,  850 ,  861 ,  863 ,  868 ,  869 ,  874 ,  876 ,  877 ,  878 ,  879 ,  884 ,  891 ,  892 ,  893 ,  894 ,  898 ,  9 ,  905 ,  906 ,  912 ,  918 ,  928 ,  934 ,  935 ,  939 ,  940 ,  942 ,  95 ,  953 ,  954 ,  964 ,  965 ,  966 ,  971 ,  982 ,  984 ,  992 ,  994 ]
    create_db(os.path.join(reader.get_dyn_data_root(),"descriptors.sqlite"))
    del reader
    if processes<=1:
        for s in ids:
            save_subj_descs(s)
    else:
        proc_pool=Pool(processes=processes)
        proc_pool.map(save_subj_descs,ids)

if __name__ == "__main__":
    import sys
    braviz.utilities.configure_console_logger("descriptors")
    procs = 2
    if len(sys.argv)>=2:
        procs = int(sys.argv[1])
    save_for_all(procs)
