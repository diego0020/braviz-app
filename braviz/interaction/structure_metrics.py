"""Functions for calculating or reading structure metrics"""
from __future__ import division
import random

import numpy as np

import braviz
import braviz.readAndFilter.tabular_data

__author__ = 'Diego'


def get_mult_struct_metric(reader, struct_names, code, metric='volume'):
    """Aggregates a metric across multiple structures

    If metric is area or volume the values for the different structures are added,
    if metric is nfiber,lfibers or fa_fibers get_fibers_metric is used"""
    values = []
    if metric in ('lfibers', 'fa_fibers', 'nfibers'):
        #we need to get all the fibers
        if metric == 'nfibers':
            result = get_fibers_metric(reader, struct_names, code, 'number')
        elif metric == 'lfibers':
            result = get_fibers_metric(reader, struct_names, code, 'mean_length')
        elif metric == 'fa_fibers':
            result = get_fibers_metric(reader, struct_names, code, 'mean_fa')
    elif metric in ('area', 'volume'):
        for struct in struct_names:
            value = get_struct_metric(reader, struct, code, metric)
            if np.isfinite(value):
                values.append(value)
        if len(values) > 0:
            result = np.sum(values)
        else:
            result = float('nan')
    elif metric in ("fa_inside", "md_inside"):
        if metric == "fa_inside":
            img2 = "FA"
            result = mean_inside(code, struct_names, img2)
        else:
            img2 = "MD"
            result = mean_inside(code, struct_names, img2)
            result *= 1e12
    else:
        raise Exception('Unknown metric')
    return result


def get_struct_metric(reader, struct_name, code, metric='volume'):
    """Calculates a metric for a specific structure

    The supported metrics are:
    volume: Volume of the structure, read from freesurfer files
    area: Surfrace area of the structure
    nfibers: Number of fibers that cross the structure, or number of fibers in the bundle if structure is Fibs:*
    lfibers: Mean length of fibers going through structure or in bundle
    fa_fibers: Mean fa of fibers crossing the structure or in bundle
    """
    #print "calculating %s for %s (%s)"%(metric,struct_name,code)

    if metric == 'volume':
        try:
            return reader.get('model', code, name=struct_name, volume=1)
        except IOError:
            return float('nan')
    #volume don't require the structure to exist
    if not struct_name.startswith('Fib'):
        try:
            model = reader.get('model', code, name=struct_name)
        except Exception:
            print "%s not found for subject %s" % (struct_name, code)
            return float('nan')
    if metric == 'area':
        area, volume = braviz.interaction.compute_volume_and_area(model)
        return area
    elif metric == 'nfibers':
        return get_fibers_metric(reader, struct_name, code, 'number')
    elif metric == 'lfibers':
        return get_fibers_metric(reader, struct_name, code, 'mean_length')
    elif metric == 'fa_fibers':
        return get_fibers_metric(reader, struct_name, code, 'mean_fa')
    else:
        raise Exception("unknown metric %s" % metric)


def get_fibers_metric(reader, struct_name, code, metric='number', ):
    """Calculates metrics for groups of fibers

    struct_name can be the name of a freesurfer model, in which case the bundle will be the fibers that cross it,
    if struct_name is a list of structures, the fibers crossing any of those structures will be used
    finally struct_name can be a named fiber, which will be used as a bundle

    metrics are number, mean_length and mean_fa
    """
    #print "calculating for subject %s"%code
    n = 0
    if hasattr(struct_name, "__iter__") and len(struct_name) == 1:
        struct_name = iter(struct_name).next()
    if (type(struct_name) == str) and struct_name.startswith('Fibs:'):
        #print "we are dealing with special fibers"
        try:
            fibers = reader.get('fibers', code, name=struct_name[5:], color='fa')
        except Exception:
            n = float('nan')
            return n
    else:
        try:
            fibers = reader.get('fibers', code, waypoint=struct_name, color='fa', operation='or')
        except Exception:
            n = float('nan')
            return n
    if fibers is None:
        #print "Problem loading fibers for subject %s"%code
        n = float('nan')
        return n
    elif metric == 'number':
        n = fibers.GetNumberOfLines()
    elif metric == 'mean_length':
        desc = braviz.interaction.get_fiber_bundle_descriptors(fibers)
        n = float(desc[1])
    elif metric == 'mean_fa':
        desc = braviz.interaction.aggregate_fiber_scalar(fibers, component=0, norm_factor=1 / 255)
        del fibers
        n = float(desc[1])
    else:
        print 'unknowm fiber metric %s' % metric
        return float('nan')
    return n


def cached_get_struct_metric_col(reader, codes, struct_name, metric,
                                 state_variables={}, force_reload=False, laterality_dict={}):
    """
    calculates a structure metrics for all subjects in a list of codes

    It has a disk cache which is used to try to save results, and if available read from disk instead of calculating again
    if force_reload is True, a cached result will be ignored, and the column will be calculated again
    A laterality_dict may be used for solving dominand and non dominant structures specifications
    It has a dictionary of state_variables which can be used to monitor or cancel the calculation from a different thread
    The states variables are:
    'struct_name': the requested structure name
    'metric' ; the requested metric
    'working' : Set to true at start of function, and to false just before returning
    'output' : A partial list of results will be stored here, this is the same object that will be returned
    'number_calculated' : number of metrics calculated
    'number_requested' : number of metrics requested (length of codes list)
    'cancel' : Set this to True, to cancel the operation and return before the next iteration
    """
    #global struct_metrics_col, temp_struct_metrics_col, processing, cancel_calculation_flag, struct_name, metric
    state_variables['struct_name'] = struct_name
    state_variables['metric'] = metric
    state_variables['working'] = True
    state_variables['output'] = None
    state_variables['number_calculated'] = 0
    state_variables['number_requested'] = len(codes)
    calc_function = get_struct_metric
    if random.random() < 0.01:
        force_reload = True
    if hasattr(struct_name, '__iter__'):
        #we have multiple sequences
        calc_function = get_mult_struct_metric
        standard_list = list(struct_name)
        standard_list.sort()
        key = 'column_%s_%s' % (''.join(struct_name).replace(':', '_'), metric.replace(':', '_'))
    else:
        key = 'column_%s_%s' % (struct_name.replace(':', '_'), metric.replace(':', '_'))
    key += ';'.join(sorted(codes))
    if force_reload is not True:
        cached = reader.load_from_cache(key)
        if cached is not None:
            cache_codes, struct_metrics_col, = zip(*cached)
            if np.sum(np.isnan(struct_metrics_col)) / len(cache_codes) > 0.5:
                print "Cache looks wrong, recalculating"
            elif list(cache_codes) == list(codes):
                state_variables['output'] = struct_metrics_col
                state_variables['working'] = False
                state_variables['number_calculated'] = 0
            return struct_metrics_col
    print "Calculating %s for structure %s" % (metric, struct_name)
    temp_struct_metrics_col = []
    for code in codes:
        cancel_calculation_flag = state_variables.get('cancel', False)
        if cancel_calculation_flag is True:
            print "cancel flag received"
            state_variables['working'] = False
            return
        struct_name2 = solve_laterality(laterality_dict.get(code, 'unknown'), struct_name)
        scalar = calc_function(reader, struct_name2, code, metric)
        temp_struct_metrics_col.append(scalar)
        state_variables['number_calculated'] = len(temp_struct_metrics_col)
    reader.save_into_cache(key, zip(codes, temp_struct_metrics_col))
    state_variables['output'] = temp_struct_metrics_col
    state_variables['working'] = False
    return temp_struct_metrics_col


laterality_lut = {
    #dominant or non_dominant, right_handed or left_handed : resulting hemisphere
    ('d', 'r'): 'l',
    ('d', 'l'): 'r',
    ('n', 'r'): 'r',
    ('n', 'l'): 'l',
}


def get_right_or_left_hemisphere(hemisphere, laterality):
    """
    Translates d (dominant) and n (nondominant) into r (right) or l (left) using laterality,
    laterality should be r (right handed) or l (left handed)
    hemisphere can also be r or l; which will be outputed again"""
    if hemisphere in ('d', 'n'):
        if laterality[0].lower() not in ('r', 'l'):
            raise Exception('Unknown laterality')
        new_hemisphere = laterality_lut[(hemisphere, laterality[0])]
    elif hemisphere in ('r', 'l'):
        new_hemisphere = hemisphere
    else:
        raise Exception('Unknwon hemisphere')
    return new_hemisphere


def solve_laterality(laterality, names):
    """translates dominant and nondominant freesurfer names into right and left names,
    laterality should be  (right handed) or l (left handed)
    names is a list of names to translate
    currently wm-[d|n|r|l]h-* , ctx-[d|n|r|l]h-* and fiber bundles ending in '_[d|n|r|l]' are supported"""
    #TODO: Support Left-Amygdala
    new_names = []
    if type(names) == str:
        names2 = (names,)
    else:
        names2 = names
    for name in names2:
        new_name = name
        if name.startswith('ctx-'):
            h = name[4]
            new_name = ''.join((name[:4], get_right_or_left_hemisphere(h, laterality), name[5:]))
        elif name.startswith('wm-'):
            h = name[3]
            new_name = ''.join((name[:3], get_right_or_left_hemisphere(h, laterality), name[4:]))
        elif name[-2:] in ('_d', '_n', '_r', '_l'):
            h = get_right_or_left_hemisphere(name[-1], laterality)
            new_name = name[:-1] + h
        new_names.append(new_name)
    if type(names) == str:
        return new_names[0]
    else:
        return new_names


def mean_inside(subject, structures, img2, paradigm=None):
    """
    Calculate the mean value of img2 modality inside of the structures listed
    img2 must be FA, MD, MRI or fMRI
    """
    if len(structures) == 0:
        return float("nan")
    reader = braviz.readAndFilter.kmc40AutoReader()
    #find label
    #print "label:",label
    #find voxels in structure
    aparc_img = reader.get("APARC", subject, space="world", format="nii")
    locations = [get_locations(reader, subject, name) for name in structures]
    shape = aparc_img.shape
    shape2 = shape + (1,)
    locations = [l.reshape(shape2) for l in locations]
    locations2 = np.concatenate(locations, 3)
    locations3 = np.any(locations2, 3)
    indexes = np.where(locations3)
    n_voxels = len(indexes[0])
    #print indexes
    #find mm coordinates of voxels in aparc
    img_coords = np.vstack(indexes)
    ones = np.ones(len(indexes[0]))
    img_coords = np.vstack((img_coords, ones))
    t = aparc_img.get_affine()
    mm_coords = img_coords.T.dot(t.T)
    #print mm_coords

    #find voxel coordinates in fa
    if paradigm is None:
        target_img = reader.get(img2, subject, space="world", format="nii")
    else:
        target_img = reader.get(img2, subject, space="world", format="nii", name=paradigm)
    t2 = target_img.get_affine()
    t2i = np.linalg.inv(t2)
    fa_coords = mm_coords.dot(t2i.T)
    fa_coords = np.round(fa_coords)
    fa_coords = fa_coords.astype(np.int32)

    splitted = np.hsplit(fa_coords, 4)
    fa_coords2 = splitted[0:3]
    fa_data = target_img.get_data()
    #sample and sum
    res = np.sum(fa_data[fa_coords2])
    res /= n_voxels
    return res


def get_locations(reader, subject, struct_name):
    label = int(reader.get("Model", subject, name=struct_name, label=True))
    if struct_name.startswith("wm"):
        aparc_img = reader.get("APARC", subject, space="world", format="nii", wm=True)
    else:
        aparc_img = reader.get("APARC", subject, space="world", format="nii")
    aparc_data = aparc_img.get_data()
    return aparc_data == label


def get_scalar_from_fiber_ploydata(poly_data, scalar):
    pd = poly_data
    if scalar == "number":
        return pd.GetNumberOfLines()
    elif scalar == "mean_length":
        desc = braviz.interaction.get_fiber_bundle_descriptors(pd)
        n = float(desc[1])
        return n
    elif scalar == "mean_color":
        desc = braviz.interaction.aggregate_fiber_scalar(pd, component=0, norm_factor=1 / 255)
        n = float(desc[1])
        return n
    else:
        raise Exception("Unknown metric %s", scalar)
        return float("nan")


def get_fiber_scalars_from_db(reader, subj_id, db_id, scalar):
    color = "orient"
    if scalar == "mean_fa":
        color = "FA"
        scalar = "mean_color"
    try:
        pd = reader.get("FIBERS", subj_id, color=color, db_id=db_id)
    except Exception:
        return float("nan")
    return get_scalar_from_fiber_ploydata(pd, scalar)


def get_fiber_scalars_from_waypoints(reader, subj_id, waypoints, operation, scalar):
    color = "orient"
    lat = braviz.readAndFilter.tabular_data.get_laterality(subj_id)
    waypoints2 = solve_laterality(lat, waypoints)
    if scalar == "mean_fa":
        color = "FA"
        scalar = "mean_color"
    try:
        pd = reader.get("FIBERS", subj_id, color=color, waypoint=waypoints2, operation=operation)
    except Exception:
        return float("nan")
    return get_scalar_from_fiber_ploydata(pd, scalar)