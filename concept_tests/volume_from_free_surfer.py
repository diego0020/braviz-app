from braviz.readAndFilter.read_csv import read_free_surfer_csv_file
import os
import braviz
__author__ = 'Diego'
os.chdir(r'C:\Users\Diego\Documents\kmc40-db\KAB-db\093\Models\stats')
file_name1='aseg.stats'

print read_free_surfer_csv_file(file_name1,'headers')

file_name2='lh.aparc.stats'
print read_free_surfer_csv_file(file_name2,'headers')


print read_free_surfer_csv_file(file_name1,'CC_Posterior','StructName','Volume_mm3')
print read_free_surfer_csv_file(file_name2,'cuneus','StructName','GrayVol')

reader=braviz.readAndFilter.kmc40AutoReader()
def get_volume(subject,model_name):
    data_root=reader.getDataRoot()
    data_dir=os.path.join(data_root,subject,'Models','stats')
    if model_name[:3] =='ctx':
        #we are dealing with a cortex structure
        hemisphere=model_name[4]
        name=model_name[7:]
        file_name='%sh.aparc.stats'%hemisphere
        complete_file_name=os.path.join(data_dir,file_name)
        vol=read_free_surfer_csv_file(complete_file_name,name,'StructName','GrayVol')
    else:
        #we are dealing with a normal structure
        name=model_name
        file_name='aseg.stats'
        complete_file_name = os.path.join(data_dir, file_name)
        vol = read_free_surfer_csv_file(complete_file_name, name, 'StructName', 'Volume_mm3')
    if vol is None:
        vol=0
    return float(vol)

models=reader.get('model','093',index=1)

volumes={}

#sanity check
for m in models:
    volumes[m]=get_volume('093',m)

