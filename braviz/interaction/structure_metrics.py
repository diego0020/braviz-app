import braviz
import vtk
from os.path import join as path_join
import cPickle
__author__ = 'Diego'

def get_struct_metric(reader,struct_name,code,metric='volume'):
    print "calculating %s for %s"%(metric,struct_name)
    if not struct_name.startswith('Fib'):
        try:
            model=reader.get('model',code,name=struct_name)
        except Exception:
            print "%s not found for subject %s"%(struct_name,code)
            return float('nan')
    if metric=='volume':
        return reader.get('model',code,name=struct_name,volume=1)
    if metric=='area':
        area, volume = braviz.interaction.compute_volume_and_area(model)
        return area
    elif metric=='nfibers':
        return get_fibers_metric(struct_name,code,'number')
    elif metric=='lfibers':
        return get_fibers_metric(struct_name,code,'mean_length')
    elif metric=='fa_fibers':
        return get_fibers_metric(struct_name,code,'mean_fa')
    else:
        print "unknown metric %s"%metric
        return None

def get_fibers_metric(reader, struct_name,code,metric='number'):
    #print "calculating for subject %s"%code
    n=0
    if struct_name.startswith('Fibs:'):
        #print "we are dealing with special fibers"
        try:
            fibers = reader.get('fibers', code, name=struct_name[6:], color='fa')
        except Exception:
            n = float('nan')
            return n
    else:
        try:
            fibers=reader.get('fibers',code,waypoint=struct_name,color='fa')
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

def cached_get_struct_metric_col(reader,struct_name_temp,metric_temp,async=False,state_variables={}):
    #global struct_metrics_col, temp_struct_metrics_col, processing, cancel_calculation_flag, struct_name, metric
    state_variables['working']=True
    key = 'column_%s_%s' % (struct_name_temp.replace(':', '_'), metric_temp.replace(':', '_'))
    cache_file_name = path_join(reader.getDataRoot(), 'pickles', '%s.pickle' % key)
    try:
        with open(cache_file_name, 'rb') as cachef:
            struct_metrics_col = cPickle.Unpickler(cachef).load()
    except IOError:
        pass
    else:
        return struct_metrics_col
    print "Calculating %s for structure %s" % (metric_temp, struct_name_temp)
    temp_struct_metrics_col = []
    codes=reader.get('ids')
    for code in codes:
        cancel_calculation_flag=state_variables.get('cancel',False)
        if cancel_calculation_flag is True:
            print "cancel flag received"
            state_variables['working'] = False
            return
        scalar = get_struct_metric(struct_name_temp, code, metric_temp)
        temp_struct_metrics_col.append(scalar)
        state_variables['number_calculated'] = len(temp_struct_metrics_col)
    try:
        with open(cache_file_name, 'wb') as cachef:
            cPickle.Pickler(cachef, 2).dump(struct_metrics_col)
    except Exception:
        print "cache write failed"
        print "file was %s" % cache_file_name
        pass
    state_variables['working'] = False
    return temp_struct_metrics_col



