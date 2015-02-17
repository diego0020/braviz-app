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
from braviz.readAndFilter import tabular_data, user_data
import pandas as pd
import numpy as np


__author__ = 'da.angulo39'


def parse_spss_meta(file_name, do_save=False,verbose=False):
    reader = savReaderWriter.SavReader(file_name )
    with reader:
        info = reader.getSavFileInfo()
        descriptions = info[5]
        labels = info[6]
        print "Reading descriptions"
        for k, v in descriptions.iteritems():
            save_description(k, v, do_save,verbose)
        print "Reading labels"
        for k, v in labels.iteritems():
            save_labels(k, v, do_save,verbose)


def save_description(var_name, desc, do_save=False,verbose=False):
    if verbose or not do_save:
        print "%s : %s" % (var_name, desc)
    try:
        var_name2 = var_name.decode('latin-1', errors="ignore")
        desc2 = desc.decode('latin-1', errors="ignore")
        if do_save:
            tabular_data.save_var_description_by_name(var_name2, desc2)
    except Exception as e:

        print e.message
        raise

def read_spss_data(file_name,index_col=None,verbose=False):
    print "Reading data"
    reader = savReaderWriter.SavReader(file_name,recodeSysmisTo=float('nan') )
    with reader:
        var_names=reader.varNames
        all_data=reader.all()
    df=pd.DataFrame(all_data)
    df.columns = var_names
    if index_col is not None:
        df.index=df[index_col]
    print "post processing"
    post_process(df)
    return df

def post_process(data_frame,verbose=False):
    ttts=data_frame.dtypes.get_values()
    indeces = np.where(ttts==np.dtype('O'))
    names=data_frame.columns[indeces]
    for n in names:
        c=data_frame[n]
        try:
            valid=c.str.strip().str.len()>0
            c[valid]=c[valid].astype(np.float)
            c[np.logical_not( valid)] = np.nan
            data_frame[n]=c.astype(np.float)
        except ValueError:
            pass
        else:
            if verbose:
                print "%s is numeric"%n


def save_comments(data_frame,do_save=False,verbose=False):
    ttts=data_frame.dtypes.get_values()
    indeces = np.where(ttts==np.dtype('O'))
    names=data_frame.columns[indeces]
    comments = {}
    for c in names:
        col = data_frame[c].dropna()
        for i in col.index:
            com1 = comments.get(i)
            com = col[i].strip()
            if len(com)==0:
                continue
            com2 = ":\n".join((c,com))
            if com1 is not None:
                com3 = "\n\n".join((com1,com2))
            else:
                com3 = com2
            comments[i]=com3

    for k,v in comments.iteritems():
        if verbose or not do_save:
            print "%d : %s"%(k,v)
        if do_save:
            user_data.update_comment(int(k),v.decode("latin-1"))

def save_data_frame(data_frame,do_save=False,verbose=False):
    print "Processing numerical data"
    ttts=data_frame.dtypes.get_values()
    data_frame2=data_frame[data_frame.columns[ttts!=np.dtype('O')]]
    if verbose and do_save:
        print "The following variables will be updated"
        print ", ".join(sorted(data_frame2.columns))

    if not do_save or verbose:
        print data_frame2.head()

    if do_save:
        tabular_data.add_data_frame(data_frame2)
        print "done saving numerical data"



def save_labels(var_name, labels, do_save=False,verbose=False):
    if verbose:
        print "==============="
        print var_name
        print
    #save var as nominal
    var_idx = tabular_data.get_var_idx(var_name)
    # verify labels have values
    good_labels = [l for l in labels.itervalues() if len(l) > 1]
    if len(good_labels) < 2:
        if verbose:
            print "NOT GOOD LABELS FOUND, Assuming real"
        return
    if do_save and var_idx is None:
        if verbose:
            print "VARIABLE NOT FOUND"
        return
    if do_save:
        tabular_data.save_is_real(var_idx, False)
    tuples = [(int(k), unicode(v, errors="ignore")) for k, v in labels.iteritems()]
    if verbose or not do_save:
        print tuples
    if do_save:
        tabular_data.save_nominal_labels(var_idx, tuples)


if __name__ == "__main__":
    import argparse

    parser= argparse.ArgumentParser(description="Import data from spss files")
    parser.add_argument('-d','--data',action='store_true',
                        help="Read numerical data")
    parser.add_argument('-m','--meta',action='store_true',
                        help="Read variable descriptions, type, and labels for nominal variables")
    parser.add_argument('-c','--comments',action='store_true',
                        help="Read text variables as comments for each subject")
    parser.add_argument('-s','--save',action='store_true',
                        help="Add the read information to the database")
    parser.add_argument('-v','--verbose',action='store_true',
                        help="Print data to the terminal")
    parser.add_argument('spss_file',
                        help="Path to a spss file (usually with .sav extension)")

    parser.add_argument('index_col',
                        help="Variable containing subject indices")

    args = parser.parse_args()

    if args.verbose:
        print "Received arguments"
        print args

    if args.data or args.comments:
        df = read_spss_data(args.spss_file,args.index_col,args.verbose)
        if args.data:
            save_data_frame(df,args.save,args.verbose)
        if args.comments:
            save_comments(df,args.save,args.verbose)

    if args.meta:
        parse_spss_meta(args.spss_file,args.save,args.verbose)
