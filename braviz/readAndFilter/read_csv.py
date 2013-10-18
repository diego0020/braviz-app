from __future__ import division
import vtk
import numpy as np

__author__ = 'Diego'


def get_column(file_name, name, numeric=False,nan_value=float('nan')):
    try:
        csv_file = open(file_name)
    except IOError:
        print "couldn't open file " + file_name
        raise

    headers = csv_file.readline()
    headers = headers.rstrip('\n')
    headers = headers.split(';')
    if name not in headers:
        print "column %s not found in file" % name
        return None
    idx = headers.index(name)
    column = []
    for l in iter(csv_file.readline, ''):
        l2 = l.rstrip('\n')
        l2 = l2.split(';')
        item = l2[idx]
        if numeric:
            try:
                num = float(item)
            except ValueError:
                try:
                    #some decimals number saved using a comma
                    item = item.replace(',', '.')
                    num = float(item)
                except:
                    num =nan_value
            item = num
        column.append(item)
    csv_file.close()
    return column


def get_headers(file_name):
    try:
        csv_file = open(file_name)
    except IOError:
        print "couldn't open file " + file_name
        raise
    headers = csv_file.readline()
    headers = headers.rstrip('\n')
    headers = headers.split(';')
    csv_file.close()
    return headers


def column_to_vtk_array(col, name='unknown'):
    if not isinstance(col[0], str):
        array = vtk.vtkFloatArray()
        array.InsertNextValue(col[0])
    else:
        array = vtk.vtkStringArray()
        array.InsertNextValue(col[0])
    for item in col:
        array.InsertNextValue(item)
        #print "adding %s"%item
    array.SetName(name)
    return array


def read_free_surfer_csv_file(file_name, row, search_col=None, col=None):
    """reads from a free surfer stats file. If row is headers returns a list of file headers
    Otherwise: a single row will be selected based on the row value and the search_col value.
    The function will return the row where the value under column with header search_col matches row
    if col is given, only the value under the column with this header will be returned"""
    try:
        fs_file = open(file_name)
    except IOError:
        print "couldn't open file " + file_name
        raise
    col_headers = None
    search_col_index = None
    result_col_index = None
    for l in iter(fs_file.readline, ''):
        l = l.rstrip('\n')
        #search for the heades comment
        if col_headers is None:
            if l[:12] == '# ColHeaders':
                #found it
                l2 = l[13:]
                col_headers = l2.split()
                #col_headers = l2.split(' ')
                #col_headers = filter(lambda x: len(x) > 0, col_headers)
                if row == 'headers':
                    fs_file.close()
                    return col_headers
                else:
                    try:
                        search_col_index = col_headers.index(search_col)
                    except:
                        print "column %s not found" % search_col
                        print "avaiable columns are %s" % col_headers
                        raise
                    if col is not None:
                        try:
                            result_col_index = col_headers.index(col)
                        except:
                            print "column %s not found" % search_col
                            print "avaiable columns are %s" % col_headers
                            raise

        else:
            #Now we must parse each line
            l2 = l.split(' ')
            #remove empty
            l2 = filter(lambda x: len(x) > 0, l2)
            #compare with row
            if l2[search_col_index] == row:
                if col is None:
                    return l2
                else:
                    return l2[result_col_index]







