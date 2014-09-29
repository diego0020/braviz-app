import os
import savReaderWriter
from braviz.readAndFilter import tabular_data

__author__ = 'da.angulo39'



def parse_spss_file(file_name):
    reader = savReaderWriter.SavReader(file_name,verbose=True,)
    info=reader.getSavFileInfo()
    descriptions = info[5]
    labels =info[6]
    #for k,v in descriptions.iteritems():
    #    save_description(k,v)
    for k,v in labels.iteritems():
        save_labels(k,v)


def save_description(var_name,desc):
    print "%s : %s"%(var_name,desc)
    try:
        tabular_data.save_var_description_by_name(var_name,desc)
    except Exception as e:
        print e.message

def save_labels(var_name,labels):
    print "==============="
    print var_name
    print
    #save var as nominal
    var_idx = tabular_data.get_var_idx(var_name)
    if var_idx is None:
        print "VARIABLE NOT FOUND"
        return
    tabular_data.save_is_real(var_idx,False)
    tuples = [(int(k),unicode(v,errors="ignore")) for k,v in labels.iteritems()]
    print tuples
    tabular_data.save_nominal_labels(var_idx,tuples)





if __name__ == "__main__":
    os.chdir(r"C:\Users\da.angulo39\Downloads")
    file_name = "baseRCT50.sav"
    parse_spss_file(file_name)