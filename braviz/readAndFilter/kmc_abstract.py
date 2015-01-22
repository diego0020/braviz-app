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


from __future__ import division

import os
import re
import cPickle
import types
import pickle
import logging

import nibabel as nib
import numpy as np
from numpy.linalg import inv
import vtk

from braviz.readAndFilter import config_file
from braviz.readAndFilter.filter_fibers import extract_poly_data_subset
from braviz.readAndFilter.cache import memo_ten
from braviz.readAndFilter.images import numpy2vtk_img, nibNii2vtk

from braviz.readAndFilter.surfer_input import surface2vtkPolyData, read_annot, read_morph_data, addScalars,\
    get_free_surfer_lut,   surfLUT2VTK
from braviz.readAndFilter.read_csv import read_free_surfer_csv_file
import braviz.readAndFilter.color_fibers


from braviz.readAndFilter.read_spm import get_contrasts_dict,SpmFileReader

from braviz.readAndFilter.base_reader import BaseReader
from braviz.readAndFilter.transforms import applyTransform, numpy2vtkMatrix, transformPolyData, readFreeSurferTransform, readFlirtMatrix


class KmcAbstractReader(BaseReader):
    """
A read and filter class designed to work with kmc projects. Implements common functionality in kmc40 and kmc400."""


    def __init__(self, static_root,dynamic_route, max_cache=2000,**kwargs):
        "The path pointing to the __root of the file structure must be set here"
        self.__static_root = os.path.normcase(static_root)
        #Remove trailing slashes
        self.__static_root = self.__static_root.rstrip('/\\')
        self.__dynaimc_data_root = dynamic_route.rstrip("/\\")
        if self.__static_root[-1]==":":
            self.__static_root+="\\"
        if self.__dynaimc_data_root[-1]==":":
            self.__dynaimc_data_root+="\\"

        BaseReader.__init__(self,max_cache)
        self._fmri_LUT = None
        self._fa_lut = None
        self._free_surfer_aparc_lut = None
        self._free_surfer_lut = None
        self._free_surfer_labels = None

        self._functional_paradigms=frozenset()


    def transform_points_to_space(self, point_set, space, subj, inverse=False):
        """Access to the internal coordinate transform function. Moves from world to space.
        If inverse is true moves from space to world"""
        subj = self._decode_subject(subj)
        space = space.lower()
        return self._movePointsToSpace(point_set, space, subj, inverse)

    def move_img_to_world(self,img,source_space,subj,interpolate=False):
        """
        Resample image to the world coordinate system
        :param img: image
        :param source_space: source coordinates
        :param subj: subject
        :param interpolate: apply interpolation or do nearest neighbours
        :return: resliced image
        """
        subj = self._decode_subject(subj)
        source_space = source_space.lower()
        img2 = self._move_img_to_world(subj,img,interpolate,source_space)
        return img2

    def move_img_from_world(self,img,target_space,subj,interpolate=False):
        """
        Resample image to the world coordinate system
        :param img: image
        :param target_space: target coordinates
        :param subj: subject
        :param interpolate: apply interpolation or do nearest neighbours
        :return: resliced image
        """
        subj = self._decode_subject(subj)
        target_space = target_space.lower()
        img2 = self._move_img_from_world(subj,img,interpolate,target_space)
        return img2

    def save_into_cache(self, key, data):
        """
        Saves some data into a cache, can deal with vtkData and python objects which can be pickled

        key should be printable by %s, and it can be used to later retrive the data using load_from_cache
        you should not use the same key for python objects and vtk objects
        returnt true if success, and false if failure
        WARNING: Long keys are hashed using sha1: Low risk of collisions, no checking is done
        """
        key = self._process_key(key)
        cache_dir = os.path.join(self.__dynaimc_data_root, '.braviz_cache')
        if not os.path.isdir(cache_dir):
            os.mkdir(cache_dir)
        if isinstance(data, vtk.vtkObject):
            cache_file = os.path.join(cache_dir, "%s.vtk" % key)
            writer = vtk.vtkGenericDataObjectWriter()
            writer.SetInputData(data)
            writer.SetFileName(cache_file)
            writer.SetFileTypeToBinary()
            res = writer.Write()
            if res == 1:
                return True
            else:
                return False
        else:
            # Python object, try to pickle
            cache_file = os.path.join(cache_dir, "%s.pickle" % key)
            try:
                with open(cache_file, 'wb') as cache_descriptor:
                    try:
                        cPickle.dump(data, cache_descriptor, -1)
                    except cPickle.PicklingError:
                        return False
            except OSError:
                log = logging.getLogger(__name__)
                log.error("couldn't open file %s" % cache_file)
                return False
            return True

    def load_from_cache(self, key):
        """
        Loads data stored into cache with the function save_into_cache

        Data can be a vtkobject or a python structure, if both were stored with the same key, python object will be returned
        returns None if object not found
        """
        key = self._process_key(key)
        cache_dir = os.path.join(self.__dynaimc_data_root, '.braviz_cache')
        cache_file = os.path.join(cache_dir, "%s.pickle" % key)
        log = logging.getLogger(__name__)
        try:
            with open(cache_file, 'rb') as cache_descriptor:
                try:
                    ans = cPickle.load(cache_descriptor)
                except (cPickle.UnpicklingError,EOFError):
                    log.error("File %s is corrupted " % cache_file)
                    return None
                else:
                    return ans
        except IOError:
            pass

        cache_file = os.path.join(cache_dir, "%s.vtk" % key)
        if not os.path.isfile(cache_file):
            return None
        reader = vtk.vtkGenericDataObjectReader()
        reader.SetFileName(cache_file)
        if reader.ReadOutputType() < 0:
            return None
        reader.Update()
        return reader.GetOutput()

    def get_data_root(self):
        """Returns the data_root of this reader"""
        return self.__static_root

    def get_dyn_data_root(self):
        """Returns the dynamic data_root of this reader"""
        return self.__dynaimc_data_root
#============================end of public API==========================================

#============================virtual methods============================================

    @staticmethod
    @memo_ten
    def get_auto_data_root():
        raise NotImplementedError

    @staticmethod
    @memo_ten
    def get_auto_dyn_data_root():
        raise NotImplementedError

    @staticmethod
    def get_auto_reader(**kw_args):
        raise NotImplementedError

    def _getIds(self):
        "Auxiliary function to get the available ids"
        raise NotImplementedError

    def _decode_subject(self,subj):
        raise NotImplementedError

    def _getImg(self, data, subj, space, **kw):
        "Auxiliary function to read nifti images"
        raise NotImplementedError

    def _move_img_from_world(self, subj, img2, interpolate=False, space='world'):
        "moves an image from the world coordinate space to talairach or dartel spaces"
        raise NotImplementedError

    def _move_img_to_world(self, subj, img2, interpolate=False, space='world'):
        "moves an image from the world coordinate space to talairach or dartel spaces"
        raise  NotImplementedError

    #==========Free Surfer================
    def _get_free_surfer_models_dir_name(self,subject):
        raise NotImplementedError

    def _get_talairach_transform_name(self,subject):
        """xfm extension"""
        raise  NotImplementedError

    def _get_free_surfer_stats_dir_name(self,subject):
        raise NotImplementedError

    def _get_freesurfer_lut_name(self):
        raise NotImplementedError

    def _get_free_surfer_morph_path(self,subj):
        raise NotImplementedError

    def _get_free_surfer_labels_path(self,subj):
        raise NotImplementedError

    def _get_freesurfer_surf_name(self,subj,name):
        raise NotImplementedError

    def _get_tracula_map_name(self,subj):
        raise NotImplementedError

    #=============Camino==================
    def _get_base_fibs_name(self,subj):
        raise NotImplementedError

    def _get_base_fibs_dir_name(self,subj):
        """
        Must contain 'diff2surf.mat', '<fa_img>', '<orig_img>'
        where fa_img and orig_img are defined by the following functions
        """
        raise NotImplementedError

    def _get_fa_img_name(self):
        raise NotImplementedError

    def _get_orig_img_name(self):
        raise NotImplementedError

    def _get_md_lut(self):
        raise NotImplementedError

    #==========SPM================
    def _get_paradigm_name(self,paradigm_name):
        raise NotImplementedError

    def _get_paradigm_dir(self,subject,name,spm=False):
        "If spm is True return the direcory containing spm.mat, else return its parent"
        raise NotImplementedError

    def _get_spm_grid_transform(self,subject,paradigm,direction,assume_bad_matrix=False):
        #TODO: Cache shouldn't be here
        """
        Get the spm non linear registration transform grid associated to the paradigm
        Use paradigm=dartel to get the transform associated to the dartel normalization
        """
        raise NotImplementedError

    def _read_func_transform(self,subject,paradigm_name,inverse=False):
        raise NotImplementedError
#==========================end of virtual methods=======================================

#==============================common methods===========================================

    def _get(self, data, subj=None, space='world', **kw):
        "Internal: decode instruction and dispatch"
        data = data.upper()
        space = space.lower()
        if subj is not None:
            subj = str(subj)
        if data == 'MRI':
            return self._getImg(data, subj, space, **kw)
        elif data == "MD":
            return self._getImg(data, subj, space,  **kw)
        elif data == "DTI":
            return self._getImg(data, subj, space,  **kw)
        elif data == 'FA':
            if kw.get('lut'):
                if self._fa_lut is None:
                    self._fa_lut = self._create_fa_lut()
                return self._fa_lut
            return self._getImg(data, subj, space, **kw)
        elif data == 'IDS':
            return self._getIds()
        elif data == 'MODEL':
            return self._load_free_surfer_model(subj, space, **kw)
        elif data == 'SURF':
            return self._load_free_surfer_surf(subj, space, **kw)
        elif data == 'SURF_SCALAR':
            return self._load_free_surfer_scalar(subj, **kw)
        elif data == 'FIBERS':
            return self._readFibers(subj, space, **kw)
        elif data == 'TENSORS':
            return self._readTensors(subj, space, **kw)
        elif data in {"APARC","WMPARC"}:
            if kw.get('lut'):
                if self._free_surfer_aparc_lut is None:
                    self._free_surfer_aparc_lut = self._create_surfer_lut()
                return self._free_surfer_aparc_lut
            return self._getImg(data, subj, space, **kw)
        elif data == "FMRI":
            if kw.get('lut'):
                if self._fmri_LUT is None:
                    self._fmri_LUT = self._create_fmri_lut()
                return self._fmri_LUT
            if kw.get("index"):
                return self._functional_paradigms
            return self._read_func(subj, space, **kw)
        elif data == 'BOLD':
            if space[:4] not in {'func','fmri'}:
                log = logging.getLogger(__name__)
                log.warning("BOLD data is only available in the native fMRI space")
            return self._read_bold(subj, kw['name'])
        elif data == "TRACULA":
            return self._read_tracula(subj, space, **kw)
        else:
            log = logging.getLogger(__name__)
            log.error("Data type not available")
            raise (Exception("Data type not available"))


    _spharm_models = {'Left-Amygdala': 'l_amygdala',
                       'Left-Caudate': 'l_caudate',
                       'Left-Hippocampus': 'l_hippocampus',
                       'Right-Amygdala': 'r_amygdala',
                       'Right-Caudate': 'r_caudate',
                       'Right-Hippocampus': 'r_hippocampus'}

    def _load_free_surfer_model(self, subject, space, **kw):
        """Auxiliary function to read freesurfer models stored as vtk files or the freeSurfer colortable"""
        #path=self.__root+'/'+str(subject)+'/SlicerImages/segmentation/3DModels'
        #path=self.__root+'/'+str(subject)+'/Models2'
        if subject is not None:
            path = self._get_free_surfer_models_dir_name(subject)
        else:
            path = None
        #todo
        spharm_path = path
        log = logging.getLogger(__name__)
        if kw.get('index', False):
            contents = os.listdir(path)
            pattern = re.compile(r'.*\.vtk$')
            models = [m[0:-4] for m in contents if pattern.match(m) is not None]
            #look for spharm_models
            for k, val in self._spharm_models.iteritems():
                if os.path.isfile(os.path.join(spharm_path, "%sSPHARM.vtk" % val)):
                    models.append(k + '-SPHARM')
            return models
        name = kw.get('name')
        if name is not None:
            if kw.get('color'):
                if self._free_surfer_lut is None:
                    self._parse_fs_color_file()
                colors = self._free_surfer_lut
                if name.endswith('-SPHARM'):
                    return colors[name[:-7]]
                else:
                    return colors[name]
            elif kw.get('volume'):
                if name.endswith('-SPHARM'):
                    log.warning("Warning, spharm structure treated as non-spharm equivalent")
                    name = name[:-7]
                return self._get_volume(subject, name)
            elif kw.get('label'):
                if name.endswith('-SPHARM'):
                    log.warning("Warning, spharm structure treated as non-spharm equivalent")
                    name = name[:-7]
                if self._free_surfer_labels is None:
                    self._parse_fs_color_file()
                return self._free_surfer_labels.get(name)
            else:
                available = self._load_free_surfer_model(subject, space=None, index='T')
                if not name in available:
                    log.warning( 'Model %s not available' % name)
                    raise Exception('Model %s not available' % name)
                if name.endswith('-SPHARM'):
                    spharm_name = self._spharm_models[name[:-7]]
                    filename = os.path.join(spharm_path, spharm_name + 'SPHARM.vtk')
                    reader = vtk.vtkPolyDataReader()
                    reader.SetFileName(filename)
                    reader.Update()
                    output = reader.GetOutput()
                    output = self._movePointsToSpace(output, 'spharm', subject, True)
                else:
                    filename = os.path.join(path, name + '.vtk')
                    reader = vtk.vtkPolyDataReader()
                    reader.SetFileName(filename)
                    reader.Update()
                    output = reader.GetOutput()
                if space == 'native':
                    return output
                else:
                    return self._movePointsToSpace(output, space, subject)
        else:
            log.error('Either "index" or "name" is required.')
            raise (Exception('Either "index" or "name" is required.'))

    def _get_volume(self, subject, model_name):

        data_dir = self._get_free_surfer_stats_dir_name(subject)
        if model_name[:2] == 'wm':
            #we are dealing with white matter
            file_name = 'wmparc.stats'
            complete_file_name = os.path.join(data_dir, file_name)
            vol = read_free_surfer_csv_file(complete_file_name, model_name, 'StructName', 'Volume_mm3')
        elif model_name[:3] == 'ctx':
            #we are dealing with a cortex structure
            hemisphere = model_name[4]
            name = model_name[7:]
            file_name = '%sh.aparc.stats' % hemisphere
            complete_file_name = os.path.join(data_dir, file_name)
            vol = read_free_surfer_csv_file(complete_file_name, name, 'StructName', 'GrayVol')
        else:
            #we are dealing with a normal structure
            name = model_name
            file_name = 'aseg.stats'
            complete_file_name = os.path.join(data_dir, file_name)
            vol = read_free_surfer_csv_file(complete_file_name, name, 'StructName', 'Volume_mm3')
        if vol is None:
            vol = 'nan'
        return float(vol)

    def _parse_fs_color_file(self):
        "Creates an inernal representation of the freesurfer color LUT"
        cached = self.load_from_cache('free_surfer_color_lut_internal')
        cached2 = self.load_from_cache('free_surfer_labels_dict_internal')
        if (cached is not None) and (cached2 is not None):
            if len(cached) > 1266:
                self._free_surfer_lut = cached
                self._free_surfer_labels = cached2
                return
        color_file_name = self._get_freesurfer_lut_name()

        with open(color_file_name) as color_file:
            color_lines = color_file.readlines()
            color_file.close()
            color_lists = [l.split() for l in color_lines if l[0] not in ('#', '\n', ' ') ]
            color_tuples = ((l[1], tuple([float(c) / 256 for c in l[2:]])) for l in color_lists if len(l)>0)
            color_dict = dict(color_tuples)
            self.save_into_cache('free_surfer_color_lut_internal', color_dict)
            labels_tuples = ((l[1],l[0]) for l in color_lists if len(l)>0)
            labels_dict=dict(labels_tuples)
            self.save_into_cache('free_surfer_labels_dict_internal',labels_dict)

        self._free_surfer_lut = color_dict
        self._free_surfer_labels = labels_dict


    def _cached_surface_read(self,subj,name):
        "cached function to read a freesurfer surface file"
        #check cache
        key = "surf_%s_%s"%(name,subj)
        poly = self.load_from_cache(key)
        #print 'reading from surfer file'
        if poly is None:
            filename = self._get_freesurfer_surf_name(subj,name)
            poly=surface2vtkPolyData(filename)
            self.save_into_cache(key,poly)
        return poly

    def _load_free_surfer_surf(self, subj, space, **kw):
        """Auxiliary function to read the corresponding surface file for hemi and name.
        Scalars can be added to the output surface"""
        try:
            #Check required arguments
            name = kw['hemi'] + 'h.' + kw['name']
        except KeyError:
            log = logging.getLogger(__name__)
            log.error('Name=<surface> and hemi=<l|r> are required.')
            raise Exception('Name=<surface> and hemi=<l|r> are required.')
        if not 'scalars' in kw:

            output = self._cached_surface_read(subj,name)
            if kw.get("normals",True):
                normal_f = vtk.vtkPolyDataNormals()
                normal_f.AutoOrientNormalsOn()
                normal_f.SetInputData(output)
                normal_f.Update()
                normal_f.SplittingOff()
                output = normal_f.GetOutput()
            return self._movePointsToSpace(output, space, subj)
        else:
            scalars = self.get('SURF_SCALAR', subj, hemi=name[0], scalars=kw['scalars'])
            #Take advantage of cache
            kw.pop('scalars')
            normals = kw.get('normals',True)
            kw["normals"]=False
            orig = self.get('SURF', subj, space, **kw)
            addScalars(orig, scalars)
            if normals:
                normal_f = vtk.vtkPolyDataNormals()
                normal_f.AutoOrientNormalsOn()
                normal_f.SetInputData(orig)
                normal_f.Update()
                normal_f.SetFeatureAngle(60)
                orig = normal_f.GetOutput()
            return orig

    def _load_free_surfer_scalar(self, subj, **kw):
        "Auxiliary function to read free surfer scalars"
        morph = {'area', 'curv', 'avg_curv', 'thickness', 'volume', 'sulc'}
        morph_path = self._get_free_surfer_morph_path(subj)
        labels_path = self._get_free_surfer_labels_path(subj)
        log = logging.getLogger(__name__)
        if kw.get('index'):
            contents = os.listdir(morph_path)
            contents.extend(os.listdir(labels_path))
            pattern = re.compile(hs + r'.*\.annot$')
            annots = [m[3:-6] for m in contents if pattern.match(m) is not None]
            morfs = [m for m in morph if hs + '.' + m in contents]
            return morfs + annots
        try:
            hemisphere = kw['hemi']
            hs = hemisphere + 'h'
        except KeyError:
            log.error("hemi is required")
            raise (Exception("hemi is required"))
        try:
            scalar_name = kw['scalars']
        except KeyError:
            log.error(Exception('scalars is required'))
            raise (Exception('scalars is required'))
        if scalar_name in morph:
            if kw.get('lut'):
                return get_free_surfer_lut(scalar_name)
            scalar_filename = os.path.join(morph_path,hemisphere + 'h.' + scalar_name)
            scalar_array = read_morph_data(scalar_filename)
            return scalar_array
        else:
            #It should be an annotation
            annot_filename = os.path.join(labels_path , hemisphere + 'h.' + scalar_name + '.annot')
            labels, ctab, names = read_annot(annot_filename)
            if kw.get('lut'):
                return surfLUT2VTK(ctab, names)
            return labels

    def _cached_color_fibers(self, subj, color=None,scalars=None):
        """function that reads colored fibers from cache,
        if not available creates the structure and attempts to save the cache"""

        log = logging.getLogger(__name__)
        if (color is None) and (scalars is None):
            color = "orient"

        #WE ARE IN DIFF SPACE
        if color is not None:
            color = color.lower()
            if color.startswith('orient'):
                #This one should always exist!!!!!
                file_name = self._get_base_fibs_name(subj)
                if not os.path.isfile(file_name):
                    log.error("Fibers file not found: %s"%file_name)
                    raise Exception("Fibers file not found")
                pd_reader = vtk.vtkPolyDataReader()
                pd_reader.SetFileName(file_name)
                pd_reader.Update()
                fibs = pd_reader.GetOutput()
                pd_reader.CloseVTKFile()
                #!!! This is the base case
                return fibs
            cache_key = 'streams_%s_%s.vtk' % (subj,color)
        else:
            scalars = scalars.lower()
            cache_key = 'streams_%s_sc_%s.vtk' % (subj,scalars)

        cached = self.load_from_cache(cache_key)
        if cached is not None:
                return cached
        else:
            #WE ARE IN DIFF SPACE
            #base case
            fibers = self._cached_color_fibers(subj, 'orient')
            if color == 'orient':
                return fibers
            elif color == 'y':
                color_fun = braviz.readAndFilter.color_fibers.color_by_z
                braviz.readAndFilter.color_fibers.color_fibers_pts(fibers, color_fun)
            elif color == 'fa':
                color_fun = braviz.readAndFilter.color_fibers.color_by_fa
                fa_img = self.get('fa', subj, format='vtk',space="diff")
                fun_args = (fa_img,)
                braviz.readAndFilter.color_fibers.color_fibers_pts(fibers, color_fun, *fun_args)
            elif color == 'rand':
                color_fun = braviz.readAndFilter.color_fibers.random_line
                braviz.readAndFilter.color_fibers.color_fibers_lines(fibers, color_fun)
            elif color == 'curv':
                color_fun = braviz.readAndFilter.color_fibers.line_curvature
                braviz.readAndFilter.color_fibers.color_fibers_lines(fibers, color_fun)
            elif scalars == "fa_p":
                fa_img = self.get("FA",subj,space="diff")
                braviz.readAndFilter.color_fibers.scalars_from_image(fibers,fa_img)
            elif scalars == "fa_l":
                fa_img = self.get("FA",subj,space="diff")
                braviz.readAndFilter.color_fibers.scalars_lines_from_image(fibers,fa_img)
            elif scalars == "md_p":
                md_img = self.get("MD",subj,space="diff")
                braviz.readAndFilter.color_fibers.scalars_from_image(fibers,md_img)
            elif scalars == "md_l":
                md_img = self.get("MD",subj,space="diff")
                braviz.readAndFilter.color_fibers.scalars_lines_from_image(fibers,md_img)
            elif scalars == "length":
                braviz.readAndFilter.color_fibers.scalars_from_length(fibers)
            elif scalars == "aparc":
                aparc_img = self.get("APARC",subj,space="diff")
                braviz.readAndFilter.color_fibers.scalars_from_image_int(fibers,aparc_img)
            elif scalars == "wmparc":
                wmparc_img = self.get("WMPARC",subj,space="diff")
                braviz.readAndFilter.color_fibers.scalars_from_image_int(fibers,wmparc_img)
            else:
                log.error('Unknown coloring scheme %s' % color)
                raise Exception('Unknown coloring scheme %s' % color)

            #Cache write
            self.save_into_cache(cache_key,fibers)
            return fibers

    def _cached_filter_fibers(self, subj, waypoint):
        "Only one waypoint, returns a set"
        #print "filtering for model "+waypoint
        cache_key = 'fibers_%s_%s' % (subj, waypoint)
        log = logging.getLogger(__name__)
        ids = self.load_from_cache(cache_key)
        if ids is not None:
            return ids
        if waypoint[:3]=="wm-":
            img_name = "WMPARC"
        elif waypoint[-7:]=="-SPHARM":
            #have to do it in the old style
            img_name = None
        else:
            img_name = "APARC"
        if img_name is None:
            fibers = self.get('fibers', subj, space='world')
            model = self.get('model', subj, name=waypoint, space='world')
            if model:
                ids = braviz.readAndFilter.filterPolylinesWithModel(fibers, model)
            else:
                ids = set()
        else:
            try:
                fibers = self.get('fibers', subj, space='world',color=None,scalars=img_name)
            except Exception as e:
                log.exception(e)
                log.error("%s image not found"%img_name)
                return set()
            if self._free_surfer_labels is None:
                self._parse_fs_color_file()
            lbl = self._free_surfer_labels.get(waypoint)
            if lbl is None:
                raise Exception("Unknown structure")
            ids = braviz.readAndFilter.filter_polylines_by_scalar(fibers,int(lbl))

        self.save_into_cache(cache_key,ids)
        return ids

    def _readFibers_from_db(self,subj,db_id, space, **kw):
        from braviz.readAndFilter import bundles_db
        from hierarchical_fibers import read_logical_fibers
        log = logging.getLogger(__name__)
        try:
            _, bundle_type, data = bundles_db.get_bundle_details(db_id)
        except Exception:
            log.error("Fiber with id=%s nor found in database"%db_id)
            raise Exception("Fiber with id=%s nor found in database"%db_id)

        bundle_type = int(bundle_type)

        if bundle_type == 0:
            #named tract
            assert "name" not in kw
            poly = self.get("Fibers", subj, name=data, **kw)
            return poly
        elif (bundle_type == 1) or (bundle_type == 2):
            assert "waypoint" not in kw
            assert "operation" not in kw
            operation = "and" if bundle_type == 1 else "or"
            checkpoints = pickle.loads(data)
            poly = self.get("Fibers", subj, waypoint=checkpoints, operation=operation,space=space, **kw)
            return poly
        elif bundle_type == 10:
            tree_dict = pickle.loads(data)
            poly = read_logical_fibers(subj,tree_dict,self,**kw)
            return poly
        else:
            log.error("Unknown data type")
            raise Exception("Unknown fibers")

    def _readFibers(self, subj, space, **kw):
        """Auxiliary function for reading fibers, uses all the cache available.
        First reades the correct color file,
        afterwards the lists for the corresponding waypoints from which an intersection is calculated,
        the list is then used to remove unwanted polylines,
        and finally the fibers are translated to the wanted space
        """

        log = logging.getLogger(__name__)
        if 'progress' in kw:
            log.warning("The progress argument is deprecated")
            kw['progress'].set(5)

        if kw.get("lut",False):
            scalars = kw.get("scalars")
            scalars = scalars.lower()
            if scalars is None:
                log.error("This requires scalars")
                raise Exception("This requires scalars")
            import braviz.readAndFilter.color_fibers
            if scalars == "length":
                lut = braviz.readAndFilter.color_fibers.get_length_lut()
                return lut
            elif scalars[:2]=="fa":
                lut = braviz.readAndFilter.color_fibers.get_fa_lut()
                return lut
            elif scalars[:2]=="md":
                lut = self._get_md_lut()
                return lut
        #named tracts index
        if kw.get('index', False):
            import braviz.readAndFilter.named_tracts
            named_tract_funcs = dir(braviz.readAndFilter.named_tracts)
            functions = filter(lambda x: isinstance(getattr(braviz.readAndFilter.named_tracts, x),
                                                    types.FunctionType), named_tract_funcs)
            return filter(lambda x: not x.startswith('_'), functions)

        #deal with database tracts:
        if "db_id" in kw:
            db_id = kw.pop("db_id")
            poly = self._readFibers_from_db(subj,db_id,space=space,**kw)
            return poly

        if 'name' in kw:
            #named tracts, special case
            import braviz.readAndFilter.named_tracts

            try:
                named_tract_func = getattr(braviz.readAndFilter.named_tracts, kw['name'])
            except AttributeError:
                raise Exception("unknown tract name %s" % kw['name'])
            fibers, result_space = named_tract_func(self, subj, color=kw.get('color'),scalars=kw.get("scalars"))
            #this are in result_splace coordinates, check if we need to change them
            target_space = space
            if target_space == result_space:
                return fibers
            if result_space != 'world':
                fibers = self.transform_points_to_space(fibers, result_space, subj, inverse=True)
            if target_space != 'world':
                transformed_streams = self._movePointsToSpace(fibers, space, subj, inverse=False)
                return transformed_streams
            return fibers
        if 'waypoint' not in kw:
            path = self._get_base_fibs_dir_name(subj)
            streams = self._cached_color_fibers(subj, kw.get('color'),kw.get("scalars"))
            if space in {'diff', 'native'}:
                return streams
            #move to world
            matrix = readFlirtMatrix('diff2surf.mat', self._get_fa_img_name(), self._get_orig_img_name(), path)
            #matrix = readFlirtMatrix('diff2surf.mat', 'fa.nii.gz', '../orig.nii.gz', path)
            streams_mri = transformPolyData(streams, matrix)
            if space != 'world':
                transformed_streams = self._movePointsToSpace(streams_mri, space, subj)
                return transformed_streams
            return streams_mri
        else:
            #dealing with waypoints
            if kw.get('ids',False):
                models = kw['waypoint']
                if isinstance(models, basestring):
                    return self._cached_filter_fibers(subj,models)
                sub_ids = [self._cached_filter_fibers(subj,m) for m in models]
                if (kw.get('operation', 'and') == 'and'):
                    return set.intersection(*sub_ids)
                else:
                    return set.union(*sub_ids)

            if space == 'world':
                #Do filtering in world coordinates
                models = kw.pop('waypoint')
                if isinstance(models, basestring):
                    models = (models,)
                if (kw.get('operation', 'and') == 'and') and len(models) == 0:
                    #return all fibers
                    fibers = self.get('fibers', subj, space='world', color=kw.get('color'),scalars=kw.get("scalars"))
                    return fibers

                valid_ids = None
                for nm, model_name in enumerate(models):
                    new_ids = self._cached_filter_fibers(subj, model_name)
                    if valid_ids is None:
                        valid_ids = new_ids
                    else:
                        if kw.get('operation', 'and') == 'and':
                            valid_ids.intersection_update(new_ids)
                        else:
                            valid_ids.update(new_ids)
                    prog = kw.get('progress')
                    if prog is not None:
                        prog.set(nm / len(models) * 100)
                if valid_ids is None:
                    valid_ids = set()

                #Take advantage of buffer
                fibers = self.get('fibers', subj, space='world', color=kw.get('color'),scalars=kw.get("scalars"))
                fibers2 = extract_poly_data_subset(fibers, valid_ids)
                return fibers2
            else:
                #space is not world
                #Always filter in world coordinates
                target_space = space
                filtered_fibers = self.get('fibers', subj, 'world', **kw)
                transformed_streams = self._movePointsToSpace(filtered_fibers, target_space, subj)
                return transformed_streams

    def _read_tracula(self,subj, space, **kw):
        "Read tracula files"
        if kw.get("index",False):
            labels = ['CC-ForcepsMajor', 'CC-ForcepsMinor', 'LAntThalRadiation', 'LCingulumAngBundle', 'LCingulumCingGyrus', 'LCorticospinalTract', 'LInfLongFas', 'LSupLongFasParietal', 'LSupLongFasTemporal', 'LUncinateFas', 'RAntThalRadiation', 'RCingulumAngBundle', 'RCingulumCingGyrus', 'RCorticospinalTract', 'RInfLongFas', 'RSupLongFasParietal', 'RSupLongFasTemporal', 'RUncinateFas']
            return labels
        log= logging.getLogger(__name__)
        track_name = kw.get("name")
        if track_name is None:
            log.error("Name is required")
            raise ValueError
        self._parse_fs_color_file()
        if kw.get("color",False):
            col = self._free_surfer_lut[track_name]
            return col[:3]
        idx = int(self._free_surfer_labels[track_name])
        idx %= 100

        if kw.get("map",False):
            format = kw.get("format","nii")
            map = self._read_tracula_map(subj,idx,format=format)
            if space in {"diff","native"}:
                return map
            else:
                if format == "vtk":
                    w_img = self.move_img_to_world(map,"diff",subj,interpolate=True)
                    s_img = self.move_img_from_world(w_img,space,subj,interpolate=True)
                    return s_img
                else:
                    raise NotImplementedError

        map = self._read_tracula_map(subj,idx,format="vtk")
        smooth = vtk.vtkImageGaussianSmooth()
        smooth.SetDimensionality(3)
        smooth.SetStandardDeviation(1)
        smooth.SetInputData(map)
        smooth.Update()

        maxi_val=smooth.GetOutput().GetScalarRange()[1]
        thr = maxi_val*kw.get("contour",0.2)

        contours = vtk.vtkContourFilter()
        contours.SetInputConnection(smooth.GetOutputPort())
        contours.SetNumberOfContours(1)
        contours.SetValue(0,thr)
        contours.Update()
        cont = contours.GetOutput()

        if space in {"diff","native"}:
            return cont
        cont_w = self._movePointsToSpace(cont,"diff",subj,inverse=True)
        cont_s = self._movePointsToSpace(cont_w,space,subj,inverse=False)
        return cont_s

    def _read_tracula_map(self,subj,index,format="nii"):
        affine,img_data = self._get_full_tracula_map(subj)
        data2 = img_data[:,:,:,index]
        if format == "nii":
            return nib.Nifti1Image(data2,affine)
        elif format == "vtk":
            vtk_img = numpy2vtk_img(data2, array_data_type=np.float64)
            vtk_img2 = applyTransform(vtk_img,np.linalg.inv(affine))
            return vtk_img2

    @memo_ten
    def _get_full_tracula_map(self,subj):
        tracks_full_file = self._get_tracula_map_name(subj)
        tracks_img = nib.load(tracks_full_file)
        affine = tracks_img.get_affine()
        img_data = tracks_img.get_data()
        return affine,img_data

    def _readTensors(self, subj, **kw):
        "Internal function to read a tensor file"
        raise NotImplementedError

    def _movePointsToSpace(self, point_set, space, subj, inverse=False):
        """Transforms a set of points in 'world' space to the talairach or template spaces
        If inverse is True, the points will be moved from 'space' to world"""
        if space[:2] == 'wo':
            return point_set
        elif space[:2] == 'ta':
            talairach_file = self._get_talairach_transform_name(subj)
            transform = readFreeSurferTransform(talairach_file)
            if inverse:
                transform = inv(transform)
            return transformPolyData(point_set, transform)
        elif space[:4] == 'diff':
            path = self._get_base_fibs_dir_name(subj)
            #TODO: This looks wrong!!!!
            transform = readFlirtMatrix('surf2diff.mat', self._get_orig_img_name(),self._get_fa_img_name(), path)
            if inverse:
                transform = readFlirtMatrix('diff2surf.mat', self._get_fa_img_name(), self._get_orig_img_name(), path)

            return transformPolyData(point_set, transform)
        elif space in ('template', 'dartel'):
            if inverse:
                dartel_warp = self._get_spm_grid_transform(subj,"dartel","back")
            else:
                dartel_warp = self._get_spm_grid_transform(subj,"dartel","forw")
            return transformPolyData(point_set, dartel_warp)
        elif space[:4] in ('func', 'fmri'):
            #functional space
            paradigm = space[5:]
            trans = self._read_func_transform(subj, paradigm, inverse)
            return transformPolyData(point_set, trans)
        elif space == 'spharm':
            #This is very hacky.... but works well, not explanation available :S
            aparc_img = self.get('aparc', subj)
            m = aparc_img.get_affine()
            m2 = np.copy(m)
            m2[0, 3] = 0
            m2[1, 3] = 0
            m2[1, 2] = m[2, 1]
            m2[2, 1] = m[1, 2]

            m3 = np.dot(m2, inv(m))

            if inverse:
                m3 = inv(m3)
            return transformPolyData(point_set, m3)

        else:
            log = logging.getLogger(__name__)
            log.error('Unknown Space %s' % space)
            raise Exception('Unknown Space %s' % space)

    def _create_surfer_lut(self):
        "returns a vtkLookUpTable based on the freeSurferColorLUT file"
        color_dict = self.load_from_cache('aparc_color_tuples_dictionary')
        if color_dict is not None and len(color_dict)<180:
            #pass
            color_dict = None
        #color_dict = None
        if color_dict is None:
            conf = config_file.get_apps_config()
            ref = conf.get_default_subject()
            aparc_img = self.get('APARC', ref)
            aparc_data = aparc_img.get_data()
            aparc_values = set(np.unique(aparc_data.flat))
            wmparc_img = self.get("WMPARC",ref)
            wmparc_data = wmparc_img.get_data()
            wmparc_values = np.unique(wmparc_data.flat)
            aparc_values.update(wmparc_values)
            color_file_name = self._get_freesurfer_lut_name()
            try:
                color_file = open(color_file_name)
            except IOError as e:
                log = logging.getLogger(__name__)
                log.error(e)
                raise
            color_lines = color_file.readlines()
            color_file.close()
            color_lists = (l.split() for l in color_lines if l[0] not in ['#', '\n', ' ','\r'] )
            color_tuples = ((int(l[0]),
                             ( tuple([float(c) / 256 for c in l[2:2 + 3]] + [1.0])
                               , l[1]) )
                            for l in color_lists if int(l[0]) in aparc_values)  # (index,(color,annot) )
            color_dict = dict(color_tuples)
            self.save_into_cache('aparc_color_tuples_dictionary', color_dict)
        out_lut = vtk.vtkLookupTable()
        out_lut.SetNanColor(0.0, 1.0, 0.0, 1.0)
        out_lut.SetNumberOfTableValues(max(color_dict.iterkeys()) + 1)
        out_lut.IndexedLookupOn()
        for k,v in color_dict.iteritems():
            out_lut.SetAnnotation(k, v[1])
        for k,v in color_dict.iteritems():  # HACKY.... maybe there is a bug?
            idx = out_lut.GetAnnotatedValueIndex(k)
            out_lut.SetTableValue(idx, v[0])
        #self.save_into_cache('free_surfer_vtk_color_lut',out_lut)
        return out_lut

    def _create_fa_lut(self):
        fa_lut = vtk.vtkLookupTable()
        fa_lut.SetRampToLinear()
        fa_lut.SetTableRange(0.0, 1.0)
        fa_lut.SetHueRange(0.0, 0.0)
        fa_lut.SetSaturationRange(1.0, 1.0)
        fa_lut.SetValueRange(0.0, 1.0)
        fa_lut.Build()
        return fa_lut

    def _create_fmri_lut(self):
        fmri_color_int = vtk.vtkColorTransferFunction()
        fmri_color_int.ClampingOn()
        fmri_color_int.SetColorSpaceToRGB()
        fmri_color_int.SetRange(-7, 7)
        fmri_color_int.Build()
        #                           x   ,r   ,g   , b
        fmri_color_int.AddRGBPoint(-7.0, 0.0, 1.0, 1.0)
        fmri_color_int.AddRGBPoint(-3.0, 0.0, 0.0, 0.0)
        fmri_color_int.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
        fmri_color_int.AddRGBPoint(3.0, 0.0, 0.0, 0.0)
        fmri_color_int.AddRGBPoint(7.0, 1.0, 0.27, 0.0)

        return fmri_color_int


    def _read_func_transform_internal(self,subject, paradigm_name, inverse, path, T1_func, T1_world,  ):
        "reads the transform from world to functional space"
        if inverse is False:

            dartel_trans = self._get_spm_grid_transform(subject,paradigm_name,"forw", True)
            T1_func_img = nib.load(T1_func)
            T1_world_img = nib.load(T1_world)
            Tf = T1_func_img.get_affine()
            Tw = T1_world_img.get_affine()
            T_dif = np.dot(Tf, inv(Tw))
            aff_vtk = numpy2vtkMatrix(T_dif)

            vtkTrans = vtk.vtkMatrixToLinearTransform()
            vtkTrans.SetInput(aff_vtk)

            concatenated_trans = vtk.vtkGeneralTransform()
            concatenated_trans.Identity()
            concatenated_trans.Concatenate(vtkTrans)
            concatenated_trans.Concatenate(dartel_trans)
            return concatenated_trans
        else:
            T1_func = os.path.join(path, paradigm_name, 'T1.nii')
            T1_world = os.path.join(path, 'T1', 'T1.nii')
            dartel_trans = self._get_spm_grid_transform(subject,paradigm_name,"back", True)
            T1_func_img = nib.load(T1_func)
            T1_world_img = nib.load(T1_world)
            Tf = T1_func_img.get_affine()
            Tw = T1_world_img.get_affine()
            T_dif = np.dot(Tf, inv(Tw))
            aff_vtk = numpy2vtkMatrix(inv(T_dif))

            vtkTrans = vtk.vtkMatrixToLinearTransform()
            vtkTrans.SetInput(aff_vtk)

            concatenated_trans = vtk.vtkGeneralTransform()
            concatenated_trans.Identity()
            concatenated_trans.Concatenate(dartel_trans)
            concatenated_trans.Concatenate(vtkTrans)

            return concatenated_trans

    def _read_func(self, subject, space, **kw):
        "Internal function to read functional images, deals with the SPM transforms"
        log = logging.getLogger(__name__)
        try:
            name = kw['name']
        except KeyError:
            log.error('Paradigm name is required')
            raise Exception('Paradigm name is required')
        name = name.upper()
        if name not in self._functional_paradigms:
            log.warning(" functional paradigm %s not available" % name)
            return None
        name = self._get_paradigm_name(name)
        path = self._get_paradigm_dir(subject,name,spm=True)
        if "contrasts_dict" in kw:
            spm_file_path = os.path.join(path,"SPM.mat")
            return get_contrasts_dict(spm_file_path)
        if kw.get("spm"):
            spm_file = os.path.join(path,"SPM.mat")
            return SpmFileReader(spm_file)
        contrast = kw.get("contrast",1)
        contrast_n = "%.4d"%contrast
        z_map = os.path.join(path, 'spmT_%s.hdr')%contrast_n
        log.info("Loading map %s"%z_map)
        nii_z_map = nib.load(z_map)
        if kw.get('format', 'nifti').lower() in {'nifti','nii'}:
            return nii_z_map
        vtk_z_map = nibNii2vtk(nii_z_map)
        if space == 'native':
            return vtk_z_map
        vtk_z_map = applyTransform(vtk_z_map, inv(nii_z_map.get_affine()))
        if space[:4] == 'func':
            return vtk_z_map

        T1_world = self.get('mri', subject, format='vtk', space='world')
        origin2 = T1_world.GetOrigin()
        dimension2 = T1_world.GetDimensions()
        spacing2 = T1_world.GetSpacing()
        fmri_trans = self._read_func_transform(subject, name)
        log.info("attempting to move to world")
        world_z_map = applyTransform(vtk_z_map, fmri_trans, origin2, dimension2, spacing2)

        return self._move_img_from_world(subject, world_z_map, True, space)

    def _read_bold(self, subj, paradigm):
        paradigm = self._get_paradigm_name(paradigm)
        path = self._get_paradigm_dir(subj,paradigm)
        route = os.path.join(path,'smoothed.nii.gz')
        img_4d = nib.load(route)
        return img_4d

#=========================end of common methods===========================================



