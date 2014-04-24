from __future__ import division
from collections import namedtuple
import logging

import vtk


__author__ = 'Diego'


def get_column(file_name, name, numeric=False,nan_value=float('nan')):
    log = logging.getLogger(__name__)
    try:
        with open(file_name) as csv_file:
            headers = csv_file.readline()
            headers = headers.rstrip('\n')
            headers = headers.split(';')
            if name not in headers:
                log.error("column %s not found in file" % name)
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
                        except Exception:
                            num =nan_value
                    item = num
                column.append(item)
    except IOError:
        log.error("couldn't open file " + file_name)
        raise
    return column

def get_tuples_dict(file_name,key_col,columns,numeric=False,nan_value=float('nan')):
    output_dict={}
    if type(numeric) is bool:
        numeric=[numeric]*len(columns)
    try:
        with open(file_name) as csv_file:
            headers = csv_file.readline()
            headers = headers.rstrip('\n')
            headers = headers.split(';')
            try:
                key_index=headers.index(key_col)
                if type(columns) is str:
                    col_idx=(headers.index(columns),)
                    row_tuple=lambda x:x
                else:
                    col_idx = [headers.index(name) for name in columns ]
                    row_tuple = namedtuple('row_tuple', columns)
            except ValueError as ve:
                log = logging.getLogger(__name__)
                log.error("%s , headers of file %s" % (ve.message,file_name))
                raise Exception("%s , headers of file %s" % (ve.message,file_name))

            for l in iter(csv_file.readline, ''):
                l2 =  l.rstrip('\n')
                l2 =  l2.split(';')
                key = l2[key_index]
                row_list=[]
                #go through columns
                for i,idx in enumerate(col_idx):
                    item = l2[idx]
                    if numeric[i]:
                        try:
                            num = float(item)
                        except ValueError:
                            try:
                                #some decimals number saved using a comma
                                item = item.replace(',', '.')
                                num = float(item)
                            except Exception:
                                num =nan_value
                        item = num
                    row_list.append(item)
                output_dict[key]=row_tuple(*row_list)
    except IOError:
        log = logging.getLogger(__name__)
        log.error("couldn't open file " + file_name)
        raise
    return output_dict

def get_headers(file_name):
    try:
        with open(file_name) as csv_file:
            headers = csv_file.readline()
            headers = headers.rstrip('\n')
            headers = headers.split(';')
    except IOError:
        log = logging.getLogger(__name__)
        log.error("couldn't open file " + file_name)
        raise
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
    log = logging.getLogger(__name__)
    try:
        with open(file_name) as fs_file:
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
                        if row == 'headers':
                            fs_file.close()
                            return col_headers
                        else:
                            try:
                                search_col_index = col_headers.index(search_col)
                            except ValueError:
                                log.error("column %s not found" % search_col)
                                log.info("avaiable columns are %s" % col_headers)
                                raise
                            if col is not None:
                                try:
                                    result_col_index = col_headers.index(col)
                                except ValueError:
                                    log.error("column %s not found" % search_col)
                                    log.info("avaiable columns are %s" % col_headers)
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

    except IOError:
        log.error("couldn't open file " + file_name)
        raise





