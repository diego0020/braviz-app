from __future__ import division
import vtk
import numpy as np

__author__ = 'Diego'

def get_column(file_name,name,numeric=False):
    try:
        csv_file=open(file_name)
    except IOError:
        print "couldn't open file "+file_name
        raise

    headers=csv_file.readline()
    headers=headers.rstrip('\n')
    headers=headers.split(';')
    if name not in headers:
        print "column %s not found in file"%name
        return None
    idx=headers.index(name)
    column=[]
    for l in iter(csv_file.readline,''):
        l2=l.rstrip('\n')
        l2=l2.split(';')
        item=l2[idx]
        if numeric:
            try:
                num=float(item)
            except ValueError:
                try:
                    #some decimals number saved using a comma
                    item=item.replace(',','.')
                    num=float(item)
                except:
                    num=float('nan')
            item=num
        column.append(item)
    csv_file.close()
    return column

def get_headers(file_name):
    try:
        csv_file=open(file_name)
    except IOError:
        print "couldn't open file "+file_name
        raise
    headers=csv_file.readline()
    headers=headers.rstrip('\n')
    headers=headers.split(';')
    csv_file.close()
    return headers

def column_to_vtk_array(col,name='unknown'):
    if not isinstance(col[0],str):
        array=vtk.vtkFloatArray()
        array.InsertNextValue(col[0])
    else:
        array=vtk.vtkStringArray()
        array.InsertNextValue(col[0])
    for item in col:
        array.InsertNextValue(item)
        #print "adding %s"%item
    array.SetName(name)
    return array