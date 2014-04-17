import sys
import os
from multiprocessing import Pool

import braviz
from braviz.readAndFilter.kmc40 import kmc40Reader


class ignoring_reader(kmc40Reader):
    def __init__(self,max_cache=500):
        auto_reader=braviz.readAndFilter.kmc40AutoReader(max_cache=1)
        path=auto_reader.getDataRoot()
        del auto_reader
        kmc40Reader.__init__(self, path, max_cache)
        self.get2=self.get
        print "ignoring reader initialized"
        def get(*args,**kw):
            try:
                ans=self.get2(*args,**kw)
            except Exception as e:
                print "ignoring exception"
                print e
                return None
            else:
                return ans
        self.get=get
        

#TODO: This should be inside the readAndFilter module
def clear_pickles():
    #pickles
    reader=braviz.readAndFilter.kmc40AutoReader(max_cache=500) #small cache
    data_root=reader.getDataRoot()
    del reader
    pickles_dir=os.path.join(data_root,'pickles')
    pickles_dir_list=os.listdir(pickles_dir)
    for pickle in pickles_dir_list:
        file_name=os.path.join(pickles_dir,pickle)
        os.remove(file_name)
    
    
def clear_cache(subj):
        
    reader=braviz.readAndFilter.kmc40AutoReader(max_cache=500) #small cache
    data_root=reader.getDataRoot()
    del reader
    #Dartel Transform
    print "removing %s: Dartel"%subj
    dartel_dir=os.path.join(data_root,'Dartel')
    filename='y_%s-back.vtk'%subj
    filename2='y_%s-forw.vtk'%subj
    
    for f in (filename,filename2):
        full_name=os.path.join(dartel_dir,f)
        os.remove(full_name)
    
    #FreeSurferSurface
    print "removing %s: Surfaces"%subj
    
    surf_dir=os.path.join(data_root,subj,'Surf')
    surfaces=('pial','white','orig','inflated','sphere')
    hemis=('l','r')
    for s in surfaces:
        for h in hemis:
            file_name='%sh.%s.vtk'%(h,s)
            full_name=os.path.join(surf_dir,file_name)
            os.remove(full_name)
    #Fibers
    
    
    
    print "removing %s: Colored Fibers"%subj
    fibers_dir=os.path.join(data_root,subj,'camino')
    
    colors=('fa','curv','y')
    for c in colors:
        file_name='streams_%s.vtk'%c
        full_name=os.path.join(fibers_dir,file_name)
        os.remove(full_name)
            
    #fMRI
    print "removing %s: fMRI"%subj        
    fmri_dir=os.path.join(data_root,subj,'spm')
    paradigms=('POWERGRIP','PRECISION')
    for p in paradigms:
        full_name=os.path.join(fmri_dir,p,'y_seg_forw.vtk')
        os.remove(full_name)
               
    print " %s: Done Removing "%subj

def clear_all():
    reader=braviz.readAndFilter.kmc40AutoReader(max_cache=500)
    ids=reader.get('ids')
    for i in ids:
        clear_cache(i)
    clear_pickles()

def populate_cache(subj):
    print "creating cache for subject %s"%subj    
    reader2=ignoring_reader(max_cache=500) #small cache
    #Dartel Transform
    print " %s: Dartel"%subj
    reader2.get('MRI',subj,format='vtk',space='Template')
    reader2.get('fibers',subj,space='template')

    #FreeSurferSurface
    print " %s: Surfaces"%subj
    surfaces=('pial','white','orig','inflated','sphere')
    hemis=('l','r')
    for s in surfaces:
        for h in hemis:
            reader2.get('SURF',subj,name=s,hemi=h)
    #Fibers
    print " %s: Colored Fibers"%subj
    reader2.get('fibers',subj,color='fa')
    reader2.get('fibers',subj,color='orient')
    reader2.get('fibers',subj,color='curv')
    reader2.get('fibers',subj,color='y')
    reader2.get('fibers',subj,scalars="fa_p")
    reader2.get('fibers',subj,scalars="fa_l")
    reader2.get('fibers',subj,scalars="md_l")
    reader2.get('fibers',subj,scalars="md_p")
    reader2.get('fibers',subj,scalars="length")

    waypoints=( 'Brain-Stem','CC_Anterior','CC_Central','CC_Mid_Anterior','CC_Mid_Posterior','CC_Posterior',
                'Left-Cerebellum-Cortex', 'Left-Cerebellum-White-Matter', 'Left-Cerebral-White-Matter',
                'Right-Cerebellum-Cortex', 'Right-Cerebellum-White-Matter', 'Right-Cerebral-White-Matter',
                'ctx-lh-precentral','ctx-rh-precentral')
    print " %s: Waypoints"%subj
    for w in waypoints:
        print " %s: Waypoints - %s"%(subj,w)
        reader2.get('fibers',subj,waypoint=w)
    print " %s: Done"%subj
    
    #fMRI
    paradigms=('POWERGRIP','PRECISION')
    for p in paradigms:
        print p
        reader2.get('fMRI',subj,format='vtk',name=p,space='world')
        reader2.get('MRI',subj,format='vtk',name=p,space='fmri_%s'%p)

    
    del(reader2)


def populate_all(processes=1):
    reader=braviz.readAndFilter.kmc40AutoReader(max_cache=500)
    ids=reader.get('ids')
    del(reader)
    if processes<=1:
        for i in ids:
            populate_cache(i)
    else:
        proc_pool=Pool(processes=processes)
        proc_pool.map(populate_cache,ids)

if __name__=='__main__':
    if len(sys.argv)<2:
        processes=1
    else:
        processes=int(sys.argv[1])
    print "using %d processes"%processes
    populate_all(processes)        