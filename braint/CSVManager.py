'''
Created on 9/11/2013

@author: jc.forero47
'''


def get_column_from_csv(file_name, name, numeric=False):
    csv_file=open(file_name)
    headers=csv_file.readline()
    headers=headers.rstrip('\n')
    headers=headers.split(';')
    if name not in headers:
        raise  Exception("column %s not found in file %s"%(name,file_name))
    idx=headers.index(name)
    column=[]
    for l in iter(csv_file.readline,''):
        l2=l.rstrip('\n')
        l2=l2.split(';')
        item=l2[idx]
        if numeric:
            try:
                if ',' in item:
                    item = item.replace(",",".")
                num=float(item)
            except ValueError:
                num=float('nan')
            item=num
        column.append(item)
    csv_file.close()
    return column

def get_column_range_from_csv(file_name, name, numeric=False):
    column = get_column_from_csv(file_name, name, True);
    column_range = [0,0]
    column_range[0] = float(column[0])
    column_range[1] = float(column[0])
    for i in range(1,len(column)):
        if float(column[i]) < column_range[0]:
            column_range[0] = float(column[i])
        if float(column[i]) > column_range[1]:
            column_range[1] = float(column[i])
    return column_range