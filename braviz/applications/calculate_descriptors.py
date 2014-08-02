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
    q = "INSERT OR IGNORE into descriptors VALUES (?,?, ?,?, ?,?,?)"
    conn.execute(q,vals)
    conn.commit()



def save_subj_descs(subj):
    print "subject = %s"%subj
    braviz.utilities.configure_console_logger("descriptors")
    log = logging.getLogger(__name__)
    reader = braviz.readAndFilter.BravizAutoReader(max_cache=500)
    db_name = os.path.join(reader.getDynDataRoot(),"descriptors.sqlite")
    create_db(db_name)
    conn = sqlite3.connect(db_name)
    try:
        structs = reader.get("MODEL",subj,index=True)
        aseg = reader.get("APARC",subj)
        wmaseg = reader.get("WMPARC",subj)
    except Exception as e:
        log.exception(e.message)
        return
    for s in structs:
        try:
            if s.startswith("wm-"):
                d1 =  get_descriptor(subj,s,wmaseg,reader)
            else:
                d1 =  get_descriptor(subj,s,aseg,reader)
        except Exception as e:
            log.exception(e.message)
        else:
            save_descs_in_db(conn,subj,s,d1)
    cc = ['CC_Anterior', 'CC_Central', 'CC_Mid_Anterior', 'CC_Mid_Posterior', 'CC_Posterior']
    try:
        d2 = get_agg_descriptor(subj,cc,aseg,reader)
        save_descs_in_db(conn,subj,"CC-Full",d2)
    except Exception as e:
        log.exception(e.message)

def save_for_all(processes=1):
    reader=braviz.readAndFilter.BravizAutoReader(max_cache=500)
    ids=reader.get('ids')
    create_db(os.path.join(reader.getDynDataRoot(),"descriptors.sqlite"))
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
    procs = 1
    if len(sys.argv)>=2:
        procs = int(sys.argv[1])
    save_for_all(procs)
