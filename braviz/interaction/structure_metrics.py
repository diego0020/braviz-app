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


"""Functions for calculating or reading structure metrics"""
from __future__ import division
import random
import logging

import numpy as np

import braviz
import braviz.readAndFilter.tabular_data
import scipy.stats

from vtk.util import numpy_support

__author__ = 'Diego'


def get_mult_struct_metric(reader, struct_names, code, metric='volume'):
    """
    Aggregates a metric across multiple structures

    The supported metrics are:

        - *volume*: Total volume of the structures, read from freesurfer files
        - *area*: Sum of the surface areas of each structure
        - *nfibers*: Number of fibers that cross the structure, or number of fibers
          in the bundle if structure is ``Fibs:*``
        - *lfibers*: Mean length of fibers going through structure or in bundle
        - *fa_fibers*: Mean fa of fibers crossing the structure or in bundle
        - *fa_inside*: Mean fa inside the structures
        - *md_inside*: Mean md inside the structures

    if metric is nfiber,lfibers or fa_fibers :func:`get_fibers_metric` is used

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data
        struct_names (list) : List of structure names
        code : Subject id
        metric (str) : Metric to calculate, options are *volume*, *area* (surface area), *nfibers*, *lfibers*
            *md_inside* and *fa_inside*

    Returns:
        A float number with the requested metric
    """
    values = []
    result = None
    if metric in ('lfibers', 'fa_fibers', 'nfibers'):
        # we need to get all the fibers
        if metric == 'nfibers':
            result = get_fibers_metric(reader, struct_names, code, 'number')
        elif metric == 'lfibers':
            result = get_fibers_metric(
                reader, struct_names, code, 'mean_length')
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
            result = mean_inside(reader, code, struct_names, img2)
        else:
            img2 = "MD"
            result = mean_inside(reader, code, struct_names, img2)
            #result *= 1e12
    else:
        log = logging.getLogger(__name__)
        log.error("Unknown metric")
        raise Exception('Unknown metric')
    return result


def get_struct_metric(reader, struct_name, code, metric='volume'):
    """
    Calculates a metric for a specific structure

    The supported metrics are:

        - *volume*: Volume of the structure, read from freesurfer files
        - *area*: Surfrace area of the structure
        - *nfibers*: Number of fibers that cross the structure, or number of fibers in the bundle if structure is Fibs:*
        - *lfibers*: Mean length of fibers going through structure or in bundle
        - *fa_fibers*: Mean fa of fibers crossing the structure or in bundle
        - *fa_inside*: Mean fa inside the structure
        - *md_inside*: Mean md inside the structure

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data
        struct_name (str) : Name of an structure or of a named bundle (should start with *Fibs:*)
        cod : Subject id
        metric (str) : Look above for the options

    Returns:
        A float number with the requested metric
    """
    # print "calculating %s for %s (%s)"%(metric,struct_name,code)
    if metric == 'volume':
        try:
            return reader.get('model', code, name=struct_name, volume=1)
        except IOError:
            return float('nan')
    # volume don't require the structure to exist
    if not struct_name.startswith('Fib'):
        try:
            model = reader.get('model', code, name=struct_name)
        except Exception:
            log = logging.getLogger(__name__)
            log.warning("%s not found for subject %s" % (struct_name, code))
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
    elif metric in ("fa_inside", "md_inside"):
        if metric == "fa_inside":
            img2 = "FA"
            return mean_inside(reader, code, (struct_name,), img2)
        else:
            img2 = "MD"
            return mean_inside(reader, code, (struct_name,), img2)
    else:
        raise Exception("unknown metric %s" % metric)


def get_fibers_metric(reader, struct_name, code, metric='number', ):
    """
    Calculates metrics for groups of fibers

    struct_name can be the name of a freesurfer model, in which case the bundle will be the fibers that cross it,
    if struct_name is a list of structures, the fibers crossing any of those structures will be used
    finally struct_name can be a named fiber, which will be used as a bundle

    metrics are number, mean_length and mean_fa, see :func:`get_struct_metric`

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data
        struct_name (str) : Name of an structure or of a named bundle (should start with *Fibs:*)
        cod : Subject id
        metric (str) : Options are *number*, *mean_length*, and *mean_fa*

    Returns:
        A float number with the requested metric
    """
    # print "calculating for subject %s"%code
    if hasattr(struct_name, "__iter__") and len(struct_name) == 1:
        struct_name = iter(struct_name).next()
    if (type(struct_name) == str) and struct_name.startswith('Fibs:'):
        # print "we are dealing with special fibers"
        try:
            fibers = reader.get(
                'fibers', code, name=struct_name[5:], color='fa')
        except Exception:
            n = float('nan')
            return n
    else:
        try:
            fibers = reader.get(
                'fibers', code, waypoint=struct_name, color='fa', operation='or')
        except Exception:
            n = float('nan')
            return n
    if fibers is None:
        # print "Problem loading fibers for subject %s"%code
        n = float('nan')
        return n
    elif metric == 'number':
        n = fibers.GetNumberOfLines()
    elif metric == 'mean_length':
        desc = braviz.interaction.get_fiber_bundle_descriptors(fibers)
        n = float(desc[1])
    elif metric == 'mean_fa':
        desc = braviz.interaction.aggregate_fiber_scalar(
            fibers, norm_factor=1 / 255)
        del fibers
        n = float(desc[1])
    else:
        log = logging.getLogger(__name__)
        log.error('unknowm fiber metric %s' % metric)
        return float('nan')
    return n


def cached_get_struct_metric_col(reader, codes, struct_name, metric,
                                 state_variables=None, force_reload=False, laterality_dict=None):
    """
    calculates a structure metrics for all subjects in a list of codes

    It has a disk cache which is used to try to save results, and reload them instead of calculating again
    if force_reload is True, a cached result will be ignored, and the column will be calculated again

    A laterality_dict may be used for solving dominant and non dominant structures specifications

    It has a dictionary of state_variables which can be used to monitor or cancel the calculation
    from a different thread
    The states variables are:

        - 'struct_name': the requested structure name
        - 'metric' ; the requested metric
        - 'working' : Set to true at start of function, and to false just before returning
        - 'output' : A partial list of results will be stored here, this is the same object that will be returned
        - 'number_calculated' : number of metrics calculated
        - 'number_requested' : number of metrics requested (length of codes list)
        - 'cancel' : Set this to True, to cancel the operation and return before the next iteration

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data and access cache
        codes (list) : List of subject ids
        struct_name (str) : Name of an structure or of a named bundle (should start with *Fibs:*)
        metric (str) : See :func:`get_struct_metric` for options
        state_variables (dict) : Used for sharing state with other threads, read above
        force_reload (bool) : If ``True`` cache is ignored
        laterality_dict (dict) : Dictionary with laterality of subjects. Values should be
            'l' for left handed subjects and 'r' otherwise. See :func:`braviz.readAndFilter.tabular_data.get_laterality`

    Returns:
        A list of floats of the same length as *codes* with the respective metrics for each subject
    """
    if state_variables is None:
        state_variables = dict()

    if laterality_dict is None:
        laterality_dict = dict()

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
        # we have multiple sequences
        calc_function = get_mult_struct_metric
        standard_list = list(struct_name)
        standard_list.sort()
        key = 'column_%s_%s' % (
            ''.join(sorted(struct_name)).replace(':', '_'), metric.replace(':', '_'))
    else:
        key = 'column_%s_%s' % (
            struct_name.replace(':', '_'), metric.replace(':', '_'))
    key += ';'.join(codes)
    if force_reload is not True:
        cached = reader.load_from_cache(key)
        if cached is not None:
            cache_codes, struct_metrics_col, = zip(*cached)
            if np.sum(np.isnan(struct_metrics_col)) / len(cache_codes) > 0.5:
                log = logging.getLogger(__name__)
                log.warning("Cache looks wrong, recalculating")
            elif list(cache_codes) == list(codes):
                state_variables['output'] = struct_metrics_col
                state_variables['working'] = False
                state_variables['number_calculated'] = 0
            return struct_metrics_col
    log = logging.getLogger(__name__)
    log.info("Calculating %s for structure %s" % (metric, struct_name))
    temp_struct_metrics_col = []
    for code in codes:
        cancel_calculation_flag = state_variables.get('cancel', False)
        if cancel_calculation_flag is True:
            log.info("cancel flag received")
            state_variables['working'] = False
            return
        struct_name2 = solve_laterality(
            laterality_dict.get(code, 'unknown'), struct_name)
        scalar = calc_function(reader, struct_name2, code, metric)
        temp_struct_metrics_col.append(scalar)
        state_variables['number_calculated'] = len(temp_struct_metrics_col)
    reader.save_into_cache(key, zip(codes, temp_struct_metrics_col))
    state_variables['output'] = temp_struct_metrics_col
    state_variables['working'] = False
    return temp_struct_metrics_col


laterality_lut = {
    # dominant or non_dominant, right_handed or left_handed : resulting
    # hemisphere
    ('d', 'r'): 'l',
    ('d', 'l'): 'r',
    ('n', 'r'): 'r',
    ('n', 'l'): 'l',
}


def get_right_or_left_hemisphere(hemisphere, laterality):
    """
    Translates 'd' (dominant) and 'n' (non-dominant) into 'r' (right) or 'l' (left) using laterality,

    laterality should be r (right handed) or l (left handed)
    hemisphere can also be 'r' or 'l'; in this case the same letters will be returned

    Args:
        hemisphere (str) : Should be 'd' for dominant, 'n' for non-dominant, 'r' for right or 'l' for left
        laterality (str) : Should be 'l' for left handed subjects or 'r' otherwise

    Returns:
        'r' or 'l'
    """
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
    """
    translates dominant and nondominant freesurfer names into right and left names,

    laterality should be  'l' (left handed) or 'r'
    names is a list of names to translate
    currently ``wm-[d|n|r|l]h-*`` , ``ctx-[d|n|r|l]h-*`` and fiber bundles ending in ``_[d|n|r|l]`` are supported

    Args:
        laterality (str) : Laterality of subject, 'l' for left handed, 'r' otherwise
        names (list) : List of structure names, possibly with 'd' and 'n' sides, to translate to 'l' and 'r' sides.
            Only cortical structures and named fibers are supported, read above.
    """
    new_names = []
    if isinstance(names,basestring):
        names2 = (names,)
    else:
        names2 = names
    for name in names2:
        new_name = name
        if name.startswith('ctx-'):
            h = name[4]
            new_name = ''.join(
                (name[:4], get_right_or_left_hemisphere(h, laterality), name[5:]))
        elif name.startswith('wm-'):
            h = name[3]
            new_name = ''.join(
                (name[:3], get_right_or_left_hemisphere(h, laterality), name[4:]))
        elif name[-2:] in ('_d', '_n', '_r', '_l'):
            h = get_right_or_left_hemisphere(name[-1], laterality)
            new_name = name[:-1] + h
        new_names.append(new_name)
    if isinstance(names,basestring):
        return new_names[0]
    else:
        return new_names


def mean_inside(reader, subject, structures, img2, paradigm=None, contrast=1):
    """
    Calculate the mean value of img2 values inside of the structures listed

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data
        subject : Subject id
        structures (list) : List of structure names
        img2 (str) : Modality in which to calculate mean, must be FA, MD, MRI or fMRI
        paradigm (str) : In case img2 is fMRI, the paradigm to use
        contrast (int) : In case img2 is fMRI, the contrast to use

    Returns:
        The mean value of the image voxels that lay inside any of the listed structures
    """
    if len(structures) == 0:
        return float("nan")
    if isinstance(structures, basestring):
        structures = (structures,)
    # find label
    # print "label:",label
    # find voxels in structure
    try:
        aparc_img = reader.get("LABEL", subject, name="APARC", space="subject", format="nii")
    except Exception:
        return float("nan")
    locations = [_get_locations(reader, subject, name) for name in structures]
    shape = aparc_img.shape
    shape2 = shape + (1,)
    locations = [l.reshape(shape2) for l in locations]
    locations2 = np.concatenate(locations, 3)
    locations3 = np.any(locations2, 3)
    indexes = np.where(locations3)
    n_voxels = len(indexes[0])
    # print indexes
    # find mm coordinates of voxels in aparc
    img_coords = np.vstack(indexes)
    ones = np.ones(len(indexes[0]))
    img_coords = np.vstack((img_coords, ones))
    t = aparc_img.get_affine()
    mm_coords = img_coords.T.dot(t.T)
    # print mm_coords

    # find voxel coordinates in fa
    if paradigm is None:
        target_img = reader.get("IMAGE",subject, name=img2 , space="subject", format="nii")
    else:
        target_img = reader.get(
            "FMRI", subject, space="subject", format="nii", name=paradigm, contrast=contrast)
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


class AggregateInRoi(object):

    """
    A class for doing repeated aggregations of image values inside different rois

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data

    """

    def __init__(self, reader):
        self.reader = reader
        self.img_values = None
        self.mean = True
        self.img = None

    def load_image(self, subject, space, img_class, img_name, contrast=1, mean=True):
        """
        Loads an image into the class

        Args:
            subject : subject id
            space (str) : Coordinate system in which the roi is defined
            img_class (str) : Image class in which to calculate mean or mode.
            img_name (str) : Image name in the given img_class
            contrast (int) : In case img_class is fMRI, the contrast to use
            mean (bool) : If ``True`` :meth:`get_value` will return the mean inside the roi, otherwise it will
                return the *mode*.
        """
        reader = self.reader
        if img_class == "DTI":
            img_class = "IMAGE"
            img_name = "FA"
        if img_class != "FMRI":
            target_img = reader.get(
                img_class, subject, space=space, format="nii", name=img_name)
        else:
            target_img = reader.get(
                img_class, subject, space=space, format="nii", name=img_name, contrast=contrast)

        all_values = target_img.get_data()

        self.img_values = all_values
        self.img = target_img

        self.mean = mean

    def get_value(self, roi_ctr, roi_radius):
        """
        Get mean or mode from the image inside an spherical roi

        Args:
            roi_ctr (tuple) : Coordinates of the roi center
            roi_radius (float) : Sphere radius

        Returns:
            The mean or mode of the image inside the sphere, according to the data set using :meth:`load_image`
        """
        target_img = self.img
        shape = target_img.get_shape()
        affine = target_img.get_affine()

        # Calculate bounding box for sphere
        i_affine = np.linalg.inv(affine)
        ctr_h = np.ones((4, 1))
        ctr_h[0:3, 0] = roi_ctr
        ctr_img_h = np.dot(i_affine, ctr_h)
        ctr_img = ctr_img_h[0:3] / ctr_img_h[3]
        max_factor = np.max(np.abs(i_affine.diagonal())) * roi_radius
        bb_x0 = max(0, int(ctr_img[0] - max_factor))
        bb_x1 = int(np.ceil(ctr_img[0] + max_factor))

        bb_y0 = max(0, ctr_img[1] - max_factor)
        bb_y1 = int(np.ceil(ctr_img[1] + max_factor))

        bb_z0 = max(0, ctr_img[2] - max_factor)
        bb_z1 = int(np.ceil(ctr_img[2] + max_factor))
        # create numpy grid
        grid = np.mgrid[bb_x0:bb_x1, bb_y0:bb_y1, bb_z0:bb_z1]
        grid = np.rollaxis(grid, 0, 4)
        points = grid.reshape((-1, 3))
        points_h = np.hstack((points, np.ones((points.shape[0], 1))))
        points_world_h = np.dot(affine, points_h.T).T
        points_world = points_world_h[:, :3]
        divisor = np.repeat(points_world_h[:, 3:], 3, 1)
        points_world = points_world / divisor
        r_sq = roi_radius ** 2
        offsets = points_world - roi_ctr
        dist_sq = np.sum(offsets * offsets, 1)
        inside = (dist_sq <= r_sq)

        points_inside = points[inside, :]
        all_values = self.img_values
        values_inside = all_values[
            points_inside[:, 0], points_inside[:, 1], points_inside[:, 2]]
        if self.mean is True:
            ans = np.mean(values_inside)
        else:
            ans = scipy.stats.mode(values_inside)[0]
        return ans


def aggregate_in_roi(reader, subject, roi_ctr, roi_radius, roi_space, img2, paradigm=None, contrast=None, mean=True):
    """
    Aggregate values from an image inside a spherical roi

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data
        subject : subject id
        roi_ctr (tuple) : Coordinates of the roi center
        roi_radius (float) : Sphere radius
        roi_space (str) : Coordinate system in which the roi is defined
        img2 (str) : Modality in which to calculate mean or mode.
        paradigm (str) : In case img2 is fMRI, the paradigm to use
        contrast (int) : In case img2 is fMRI, the contrast to use
        mean (bool) : If will return the mean inside the roi, otherwise it will
            return the *mode*.

    Returns:
        Mean or mode of the image inside a sphere
    """
    if paradigm is None:
        target_img = reader.get("IMAGE", subject,name=img2, space=roi_space, format="nii")
    else:
        target_img = reader.get(
            "fmri", subject, space=roi_space, format="nii", name=paradigm, contrast=contrast)
    r_sq = roi_radius ** 2
    shape = target_img.get_shape()
    affine = target_img.get_affine()
    # create numpy grid
    grid = np.mgrid[0:shape[0], 0:shape[1], 0:shape[2]]
    grid = np.rollaxis(grid, 0, 4)
    points = grid.reshape((np.prod(shape), 3))
    points_h = np.hstack((points, np.ones((points.shape[0], 1))))
    points_world_h = np.dot(affine, points_h.T).T
    points_world = points_world_h[:, :3]
    divisor = np.repeat(points_world_h[:, 3:], 3, 1)
    points_world = points_world / divisor

    offsets = points_world - roi_ctr
    dist_sq = np.sum(offsets * offsets, 1)
    inside = (dist_sq <= r_sq)

    points_inside = points[inside, :]
    all_values = target_img.get_data()
    values_inside = all_values[
        points_inside[:, 0], points_inside[:, 1], points_inside[:, 2]]
    if mean is True:
        ans = np.mean(values_inside)
    else:
        ans = scipy.stats.mode(values_inside)[0]
    return ans


def _get_locations(reader, subject, struct_name):

    label = int(reader.get("Model", subject, name=struct_name, label=True))
    if struct_name.startswith("wm"):
        aparc_img = reader.get("LABEL", subject, name="WMPARC", space="subject", format="nii")
    else:
        aparc_img = reader.get("LABEL", subject, name="APARC", space="subject", format="nii")
    aparc_data = aparc_img.get_data()
    return aparc_data == label


def get_scalar_from_fiber_ploydata(poly_data, scalar):
    """
    Calculates the number of lines, mean length or mean color from a polydata bundle

    Args:
        poly_data (vtkPolyData) : Poly Data containing only lines
        scalar (str) : may be "number","mean_length", or "mean_color"

    Returns:
        The requested scalar
    """
    pd = poly_data
    if scalar == "number":
        return pd.GetNumberOfLines()
    elif scalar == "mean_length":
        lengths = braviz.interaction.compute_fiber_lengths(pd)
        n = np.mean(lengths)
        return n
    elif scalar == "mean_color":
        desc = braviz.interaction.aggregate_fiber_scalar(pd, norm_factor=1)
        n = float(desc[1])
        return n
    else:
        log = logging.getLogger(__name__)
        log.error("Unknown metric %s", scalar)
        raise Exception("Unknown metric %s", scalar)


def get_fiber_scalars_from_db(reader, subj_id, db_id, scalar):
    """
    Calculates the number of lines, mean length mean fa or mean md from a database fiber

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data
        subj_id : Subject id
        db_id : Bundle database id
        scalar (str) : may be "number","mean_length", or "mean_fa" or "mean_md"

    Returns:
        The requested scalar, or 'nan' if there was an error
    """
    try:
        if scalar in ("number", "mean_length"):
            pd = reader.get("FIBERS", subj_id, db_id=db_id)
            return get_scalar_from_fiber_ploydata(pd, scalar)
        elif scalar == "mean_fa":
            fiber = reader.get("FIBERS", subj_id,
                               db_id=db_id, color=None, scalars="fa_p")
            n = get_scalar_from_fiber_ploydata(fiber, "mean_color")
            return n
        elif scalar == "mean_md":
            fiber = reader.get("FIBERS", subj_id,
                               db_id=db_id, color=None, scalars="md_p")
            n = get_scalar_from_fiber_ploydata(fiber, "mean_color")
            return n
    except Exception as e:
        log = logging.getLogger(__name__)
        log.error("Couldn't calculate %s for subject %s" % (scalar, subj_id))
        log.exception(e)
        return float("nan")


def get_fiber_scalars_from_waypoints(reader, subj_id, waypoints, operation, scalar):
    """
    Calculates the number of lines, mean length mean fa or mean md from a fiber created using waypoints

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data
        subj_id : Subject id
        waypoints (list) : List of structure names
        operation (str) : "and" if it required for lines to pass through *all* waypoints, "or" if they can pass
            through *any* of them
        scalar (str) : may be "number","mean_length", or "mean_fa" or "mean_md"

    Returns:
        The requested scalar, or 'nan' if there was an error
    """
    try:
        lat = braviz.readAndFilter.tabular_data.get_laterality(subj_id)
        waypoints2 = solve_laterality(lat, waypoints)
        if scalar in ("number", "mean_length"):
            pd = reader.get(
                "FIBERS", subj_id, waypoint=waypoints2, operation=operation)
            return get_scalar_from_fiber_ploydata(pd, scalar)
        elif scalar == "mean_fa":
            fiber = reader.get("FIBERS", subj_id,
                               waypoint=waypoints2, operation=operation, color=None, scalars="fa_p")
            n = get_scalar_from_fiber_ploydata(fiber, "mean_color")
            return n
        elif scalar == "mean_md":
            fiber = reader.get("FIBERS", subj_id,
                               waypoint=waypoints2, operation=operation, color=None, scalars="md_p")
            n = get_scalar_from_fiber_ploydata(fiber, "mean_color")
            return n
    except Exception as e:
        log = logging.getLogger(__name__)
        log.error("Couldn't calculate %s for subject %s" % (scalar, subj_id))
        log.exception(e)
        return float("nan")
