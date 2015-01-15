##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


import os
import savReaderWriter
from braviz.readAndFilter import tabular_data

__author__ = 'da.angulo39'

DO_SAVE = True

def parse_spss_file(file_name):
    reader = savReaderWriter.SavReader(file_name,verbose=True,)
    info=reader.getSavFileInfo()
    descriptions = info[5]
    labels =info[6]
    for k,v in descriptions.iteritems():
        save_description(k,v)
    for k,v in labels.iteritems():
        save_labels(k,v)


def save_description(var_name,desc):
    print "%s : %s"%(var_name,desc)
    try:
        desc2 = unicode(desc,errors="ignore")
        if DO_SAVE:
            tabular_data.save_var_description_by_name(var_name,desc2)
    except Exception as e:

        print e.message
        raise

def save_labels(var_name,labels):
    print "==============="
    print var_name
    print
    #save var as nominal
    var_idx = tabular_data.get_var_idx(var_name)
    # verify labels have values
    good_labels = [l for l in labels.itervalues() if len(l)>1]
    if len(good_labels)<2:
        print "NOT GOOD LABELS FOUND, Assuming real"
        return
    if DO_SAVE and var_idx is None:
        print "VARIABLE NOT FOUND"
        return
    if DO_SAVE:
        tabular_data.save_is_real(var_idx,False)
    tuples = [(int(k),unicode(v,errors="ignore")) for k,v in labels.iteritems()]
    print tuples
    if DO_SAVE:
        tabular_data.save_nominal_labels(var_idx,tuples)





if __name__ == "__main__":
    os.chdir(r"C:\Users\da.angulo39\Downloads")
    file_name = "basepilotoTMScondatospernitales.sav"
    parse_spss_file(file_name)