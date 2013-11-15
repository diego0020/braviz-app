from __future__ import division
from os.path import join as path_join
import cPickle
import random
import hashlib
import numpy as np

import braviz

__author__ = 'Diego'

def get_mult_struct_metric(reader,struct_names,code,metric='volume'):
    values=[]
    if metric in ('lfibers','fa_fibers','nfibers'):
        #we need to get all the fibers
        if metric == 'nfibers':
            result=get_fibers_metric(reader, struct_names, code, 'number')
        elif metric == 'lfibers':
            result=get_fibers_metric(reader, struct_names, code, 'mean_length')
        elif metric == 'fa_fibers':
            result=get_fibers_metric(reader, struct_names, code, 'mean_fa')
    elif metric in ('area','volume'):
        for struct in struct_names:
            value=get_struct_metric(reader,struct,code,metric)
            if np.isfinite(value):
                values.append(value)
        if len(values)>0:
            result=np.sum(values)
        else:
            result=float('nan')
    else:
        raise Exception('Unknown metric')
    return result


def get_struct_metric(reader,struct_name,code,metric='volume'):
    #print "calculating %s for %s (%s)"%(metric,struct_name,code)

    if metric=='volume':
        try:
            return reader.get('model',code,name=struct_name,volume=1)
        except IOError:
            return float('nan')
    #volume don't require the structure to exist
    if not struct_name.startswith('Fib'):
        try:
            model=reader.get('model',code,name=struct_name)
        except Exception:
            print "%s not found for subject %s"%(struct_name,code)
            return float('nan')
    if metric=='area':
        area, volume = braviz.interaction.compute_volume_and_area(model)
        return area
    elif metric=='nfibers':
        return get_fibers_metric(reader,struct_name,code,'number')
    elif metric=='lfibers':
        return get_fibers_metric(reader,struct_name,code,'mean_length')
    elif metric=='fa_fibers':
        return get_fibers_metric(reader,struct_name,code,'mean_fa')
    else:
        raise Exception("unknown metric %s"%metric)


def get_fibers_metric(reader, struct_name,code,metric='number',):
    #print "calculating for subject %s"%code
    n=0
    if hasattr(struct_name,"__iter__") and len(struct_name)==1:
        struct_name=iter(struct_name).next()
    if (type(struct_name)==str) and struct_name.startswith('Fibs:'):
        #print "we are dealing with special fibers"
        try:
            fibers = reader.get('fibers', code, name=struct_name[5:], color='fa')
        except Exception:
            n = float('nan')
            return n
    else:
        try:
            fibers=reader.get('fibers',code,waypoint=struct_name,color='fa',operation='or')
        except Exception:
            n=float('nan')
            return n
    if fibers is None:
        #print "Problem loading fibers for subject %s"%code
        n=float('nan')
        return n
    elif metric=='number':
        n=fibers.GetNumberOfLines()
    elif metric=='mean_length':
        desc=braviz.interaction.get_fiber_bundle_descriptors(fibers)
        n=float(desc[1])
    elif metric=='mean_fa':
        desc=braviz.interaction.aggregate_fiber_scalar(fibers, component=0, norm_factor=1/255)
        del fibers
        n=float(desc[1])
    else:
        print 'unknowm fiber metric %s'%metric
        return float('nan')
    return n

def cached_get_struct_metric_col(reader,codes,struct_name,metric,
                                 state_variables={},force_reload=False,laterality_dict={}):
    #global struct_metrics_col, temp_struct_metrics_col, processing, cancel_calculation_flag, struct_name, metric
    state_variables['struct_name']=struct_name
    state_variables['metric']=metric
    state_variables['working']=True
    state_variables['output']=None
    state_variables['number_calculated']=0
    state_variables['number_requested'] = len(codes)
    calc_function=get_struct_metric
    if random.random()<0.01:
        force_reload=True
    if hasattr(struct_name,'__iter__'):
        #we have multiple sequences
        calc_function=get_mult_struct_metric
        standard_list=list(struct_name)
        standard_list.sort()
        key='column_%s_%s' % (''.join(struct_name).replace(':', '_'), metric.replace(':', '_'))
    else:
        key = 'column_%s_%s' % (struct_name.replace(':', '_'), metric.replace(':', '_'))
    if len(key)>250:
        key=hashlib.sha1(key).hexdigest()
    cache_file_name = path_join(reader.getDataRoot(), 'pickles', '%s.pickle' % key)
    if force_reload is not True:
        try:
            with open(cache_file_name, 'rb') as cachef:
                struct_metrics_col_and_codes = cPickle.Unpickler(cachef).load()
        except IOError:
            pass
        else:
            cache_codes,struct_metrics_col,  = zip(*struct_metrics_col_and_codes)
            if list(cache_codes)==list(codes):
                state_variables['working'] = False
                state_variables['output'] = struct_metrics_col
                state_variables['number_calculated'] = 0
            return struct_metrics_col
    print "Calculating %s for structure %s" % (metric, struct_name)
    temp_struct_metrics_col = []
    for code in codes:
        cancel_calculation_flag=state_variables.get('cancel',False)
        if cancel_calculation_flag is True:
            print "cancel flag received"
            state_variables['working'] = False
            return
        struct_name2=solve_laterality(laterality_dict.get(code,'unknown'),struct_name)
        scalar = calc_function(reader,struct_name2, code, metric)
        temp_struct_metrics_col.append(scalar)
        state_variables['number_calculated'] = len(temp_struct_metrics_col)
    try:
        with open(cache_file_name, 'wb') as cachef:
            cPickle.Pickler(cachef, 2).dump(zip(codes,temp_struct_metrics_col))
    except IOError:
        print "cache write failed"
        print "file was %s" % cache_file_name
    state_variables['output']=temp_struct_metrics_col
    state_variables['working'] = False
    return temp_struct_metrics_col


laterality_lut={
    #dominant or non_dominant, right_handed or left_handed : resulting hemisphere
    ('d','r'):'l',
    ('d','l'):'r',
    ('n','r'):'r',
    ('n','l'):'l',
}
def get_right_or_left_hemisphere(hemisphere,laterality):
    if hemisphere in ('d', 'n'):
        if laterality[0].lower() not in ('r','l'):
            raise Exception('Unknown laterality')
        new_hemisphere = laterality_lut[(hemisphere, laterality[0])]
    elif hemisphere in ('r','l'):
        new_hemisphere=hemisphere
    else:
        raise Exception('Unknwon hemisphere')
    return new_hemisphere

def solve_laterality(laterality,names):
    new_names=[]
    for name in names:
        new_name=name
        if name.startswith('ctx-'):
            h=name[4]
            new_name=''.join((name[:4],get_right_or_left_hemisphere(h,laterality),name[5:]))
        elif name.startswith('wm-'):
            h=name[3]
            new_name = ''.join((name[:3], get_right_or_left_hemisphere(h, laterality), name[4:]))
        elif name[-2:] in ('_d','_n'):
            h=get_right_or_left_hemisphere(name[-1],laterality)
            new_name=name[:-1]+h
        new_names.append(new_name)

    return new_names
