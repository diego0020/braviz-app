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


import savReaderWriter
from braviz.readAndFilter import tabular_data

__author__ = 'da.angulo39'


def parse_spss_file(file_name, do_save=False):
    reader = savReaderWriter.SavReader(file_name, verbose=True, )
    info = reader.getSavFileInfo()
    descriptions = info[5]
    labels = info[6]
    for k, v in descriptions.iteritems():
        save_description(k, v, do_save)
    for k, v in labels.iteritems():
        save_labels(k, v, do_save)


def save_description(var_name, desc, do_save=False):
    print "%s : %s" % (var_name, desc)
    try:
        desc2 = unicode(desc, errors="ignore")
        if do_save:
            tabular_data.save_var_description_by_name(var_name, desc2)
    except Exception as e:

        print e.message
        raise


def save_labels(var_name, labels, do_save=False):
    print "==============="
    print var_name
    print
    #save var as nominal
    var_idx = tabular_data.get_var_idx(var_name)
    # verify labels have values
    good_labels = [l for l in labels.itervalues() if len(l) > 1]
    if len(good_labels) < 2:
        print "NOT GOOD LABELS FOUND, Assuming real"
        return
    if do_save and var_idx is None:
        print "VARIABLE NOT FOUND"
        return
    if do_save:
        tabular_data.save_is_real(var_idx, False)
    tuples = [(int(k), unicode(v, errors="ignore")) for k, v in labels.iteritems()]
    print tuples
    if do_save:
        tabular_data.save_nominal_labels(var_idx, tuples)


if __name__ == "__main__":
    import sys

    args = sys.argv
    if len(args) < 2:
        print "Usage:"
        print "%s <spss file> [save_labels]" % args[0]
        print
        print "spss file : Path to an spss file"
        print "save labels : By default labels and description are echoed to the terminal, if this"
        print "is 'yes' then they will be saved to the current database"
        sys.exit(0)
    file_name = args[1]
    do_save = len(args) > 2 and args[2] == "yes"
    parse_spss_file(file_name, do_save)