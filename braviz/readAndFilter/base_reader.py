from __future__ import division

import base64
import os
import hashlib
import logging

import tempfile

from braviz.readAndFilter import cache_function, CacheContainer

_auto_temp_dir = os.path.join(tempfile.gettempdir(),"braviz_temp")

class BaseReader(object):
    """
Provide access to projects' non-tabular data

Project readers provide a common interface to each projects underlying data. All project readers should be inherited
from this class. Most data access is carried out through the :meth:`get` method. Underneath this method locates the
appropriate data files and transformations, and returns the requested data in the requested coordinates system.

An instance of this class will always return empty lists when indexes are requested and raise exceptions when
data is requested. To get a more useful class you should create your own subclass.
."""
    _memory_cache_container = CacheContainer()

    def __init__(self,max_cache=100):
        """Reader parameters, like root data directories, should be set here"""

        self._memory_cache_container.max_cache = max_cache
        self.__static_root = _auto_temp_dir
        return

    def clear_cache(self):
        log = logging.getLogger(__name__)
        log.info("Clearing cache")
        self._memory_cache_container.clear()

    @cache_function(_memory_cache_container)
    def get(self,data, subj_id=None, space='world', **kwargs):
        """
        Provides access to geometric data in an specified coordinate system.

        Args:
            data (str): Case insensitive, the type of data requested. Currently the possible values are

                ===========  =====================================================
                Ids          ids of all subjects in the study as a list

                             *returns* a list of ids
                -----------  -----------------------------------------------------
                MRI          structural image of the given subject

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.

                -----------  -----------------------------------------------------
                FA           fractional anisotropy image

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.
                -----------  -----------------------------------------------------
                MD           Mean diffusivity image

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.
                -----------  -----------------------------------------------------
                DTI          RGB DTI image

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.
                -----------  -----------------------------------------------------
                Aparc        FreeSurfer Aparc (Auto Parcelation) image

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.

                             use ``lut=True`` to get a vtkLookupTable
                -----------  -----------------------------------------------------
                WMparc       FreeSurfer WMParc (White Matter Parcelation) image

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.

                             use ``lut=True`` to get a vtkLookupTable
                -----------  -----------------------------------------------------
                fMRI         SPM t-score map

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.

                             Requires ``name=<paradigm>``

                             Optionally you may specify ``contrast=<int>``

                             ``contrasts_dict`` = True will return a dictionary with
                             the available for contrasts for the specified paradigm.

                             ``SPM = True`` will return a dictionary with the data contained
                             in the *spm.mat* file.
                -----------  -----------------------------------------------------
                BOLD         SPM, pre-processed bold series

                             Only available as a 4d nibabel object
                -----------  -----------------------------------------------------
                Model        Reconstruction of FreeSurfer segmented structure

                             ``index=True`` returns a list of available models

                             ``name=<model>`` returns a vtkPolyData, unless one of the
                             following options is also specified

                             ``color=True`` returns the standard FreeSurfer color
                             associated with the given model

                             ``volume=True`` returns the volume of the given structure
                             read from the FreeSurfer stats files

                             ``label=True`` returns the integer which identifies the
                             structure in the Aparc or WMparc image
                -----------  -----------------------------------------------------
                Surf         FreeSurfer brain cortex surface reconstruction

                             Requires ``name=<surface>`` and ``hemi=<r|l>`` where
                             surface is *orig, pial, white, smoothwm, inflated or sphere*

                             ``normals=False`` returns a polydata without normals

                             ``scalars=<name>`` add the given scalars to the polydata
                             (look Surf_Scalar)
                -----------  -----------------------------------------------------
                Surf_Scalar  Scalars for a FreeSurfer surfaces

                             ``index = True`` returns a list of available scalars

                             ``scalars=<name>`` and ``hemi=<'r'|'l'>`` will return a numpy array with the
                             scalar data.

                             ``lut=True`` will return a vtkLookupTable appropriate for the given scalars.
                -----------  -----------------------------------------------------
                Fibers       Tractography

                             Returns a polydata containing polylines. The following options are available

                             ``color=<'orient'|'rand'|None>`` By default fibers are colored according to the
                             direction. 'rand' will give a different color for each polyline so that they can be
                             distinguished. Use None when you intend to display the fibers using scalar data and
                             a lookup table

                             ``scalars=<'fa_p','fa_l','md_p','md_l','length','aparc','wmparc'>`` will attach the
                             given scalar data to the polydata. fa stands for Fractional Anisotropy and md for
                             mean diffusivity. _p stands for a value for each point, while _l will create a value for
                             each line equal to the mean across the line. aparc and wmpar will attach the integer label
                             of the nearest voxel in the corresponding image.

                             ``lut=True`` can be used together with ``scalars`` to get an appropriate lookup table

                             ``waypoint = <model>`` will filter the tractography to the lines that pass through the
                             given structure

                             ``waypoint = <model-list>`` will filter the tractography to the lines that pass through
                             all models in the list. If ``operation='or'`` is also specified the behaviour changes to
                             the lines that pass through at least one of the models in the list.

                             ``name=<tract-name>`` can be used to access tracts defined through python functions. To get
                             a list of such available tracts add ``index=True``

                             ``db-id=<id>`` returns a tract stored in the database with the given index
                -----------  -----------------------------------------------------
                Tracula      Tracula probabilistic tractography

                             ``index=True`` returns a list of available bundles

                             ``name=<bundle>`` returns the isosurface at 0.20 of the maximum aposteriori probability
                             for the given bundle. Use ``contour=<percentage>`` to change this value.

                             ``map=True`` returns the probability map as an image

                             ``color=True`` returns the standard FreeSurfer color associated with the bundle.
                ===========  =====================================================

            subj_id: The id of the subject whose data is requested. Use data='ids' to get a list of available subjects

            space (str): The coordinate systems in which the result is requested. Available spaces are

                ===============   ==================================
                world             Defined by the MRI image

                talairach         MRI image after applying an affine transformation to the Talairach coordinates

                dartel            Non-linear warp towards a template

                diff              Defined by the diffusion images

                fmri-<pdgm>       Defined by the SPM results

                native            Ignores all transformations, raw voxels data
                ===============   ==================================

                Notice that some data types are not available in every space, in this case an exception will be risen.


        """
        subj_id = self.decode_subject(subj_id)
        return self._get(data, subj_id,space, **kwargs)

    def get_filtered_polydata_ids(self,subj,struct):
        self.__raise_error()

    def decode_subject(self,subj):
        """
        Transforms the subject into the standard format
        """
        return int(subj)

    def move_img_to_world(self,img,source_space,subj,interpolate=False):
        """
        Resample image to the world coordinate system
        :param img: image
        :param source_space: source coordinates
        :param subj: subject
        :param interpolate: apply interpolation or do nearest neighbours
        :return: resliced image
        """
        subj = self.decode_subject(subj)
        self.__raise_error()

    def move_img_from_world(self,img,target_space,subj,interpolate=False):
        """
        Resample image to the world coordinate system
        :param img: image
        :param target_space: target coordinates
        :param subj: subject
        :param interpolate: apply interpolation or do nearest neighbours
        :return: resliced image
        """
        subj = self.decode_subject(subj)
        self.__raise_error()

    def transform_points_to_space(self, point_set, space, subj, inverse=False):
        """Access to the internal coordinate transform function. Moves from world to space.
        If inverse is true moves from space to world"""
        subj = self.decode_subject(subj)
        self.__raise_error()

    def save_into_cache(self, key, data):
        """
        Saves some data into a cache, can deal with vtkData and python objects which can be pickled

        key should be printable by %s, and it can be used to later retrive the data using load_from_cache
        you should not use the same key for python objects and vtk objects
        returnt true if success, and false if failure
        WARNING: Long keys are hashed using sha1: Low risk of collisions, no checking is done
        """
        return False

    def load_from_cache(self, key):
        """
        Loads data stored into cache with the function save_into_cache

        Data can be a vtkobject or a python structure, if both were stored with the same key, python object will be returned
        returns None if object not found
        """
        return None

    def clear_cache_dir(self,last_word=False):
        if last_word is True:
            cache_dir = os.path.join(self.get_dyn_data_root(), '.braviz_cache')
            try:
                os.rmdir(cache_dir)
            except OSError:
                pass
            os.mkdir(cache_dir)

    def get_data_root(self):
        """Returns the data_root of this reader, this directory needs to be readable"""
        return self.__static_root

    def get_dyn_data_root(self):
        """Returns the dynamic data_root of this reader, this directory should be writable"""
        return self.__static_root

    @staticmethod
    def get_auto_data_root():
        """
        Data directory used by auto_readers
        """
        return _auto_temp_dir

    @staticmethod
    def get_auto_dyn_data_root():
        """
        Dynamic data directory used by auto_readers
        """
        return _auto_temp_dir

    @staticmethod
    def _clear_dynamic_data_dir(dir_name):
        """
        Clears braviz dynamic content from dir_name
        """
        try:
            os.walk(os.path.join(dir_name,"logs"))
            os.walk(os.path.join(dir_name,".braviz_cache"))
            os.walk(os.path.join(dir_name,"braviz_data","scenarios"))
            for sub_dir in ("logs",".braviz_cache","braviz_data"):
                top = os.path.join(dir_name,sub_dir)
                for root, dirs, files in os.walk(top, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
        except OSError:
            pass

    @staticmethod
    def initialize_dynamic_data_dir(dir_name=None):
        """
        Initializes the dynamic data directory
        """
        from braviz.readAndFilter import check_db
        if dir_name is None:
            dir_name = BaseReader.get_auto_dyn_data_root()
        os.makedirs(os.path.join(dir_name,"logs"))
        os.makedirs(os.path.join(dir_name,".braviz_cache"))
        os.makedirs(os.path.join(dir_name,"braviz_data","scenarios"))
        check_db.verify_db_completeness()

    @staticmethod
    def get_auto_reader(**kw_args):
        """Initialized a based on known nodes file"""
        return BaseReader()

    #======================END OF PUBLIC API===============================

    def _process_key(self, key):
        """
        Creates a suitable key for a cache file
        """
        data_root_length = len(self.get_dyn_data_root())
        key = "%s" % key
        if len(key) + data_root_length > 250:
            key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
        else:
            ilegal = ['_','<', '>', ':', '"', '/', "\\", '|', '?', '*']
            for i,il in enumerate(ilegal):
                key = key.replace(il, '%d_'%i)
        return key

    def __raise_error(self):
        """
        Raises an IOError
        """
        raise IOError("Data not available in BaseReader")

    def _get(self, data, subj=None, space='world', **kw):
        "Internal: decode instruction and dispatch"
        data = data.upper()
        if data == 'MRI':
            self.__raise_error()
        elif data == "MD":
            self.__raise_error()
        elif data == "DTI":
            self.__raise_error()
        elif data == 'FA':
            self.__raise_error()
        elif data == 'IDS':
            return []
        elif data == 'MODEL':
            if kw.get("index"):
                return []
            self.__raise_error()
        elif data == 'SURF':
            self.__raise_error()
        elif data == 'SURF_SCALAR':
            if kw.get("index"):
                return []
            self.__raise_error()
        elif data == 'FIBERS':
            self.__raise_error()
        elif data == 'TENSORS':
            self.__raise_error()
        elif data in {"APARC","WMPARC"}:
            self.__raise_error()
        elif data == "FMRI":
            if kw.get("index"):
                return frozenset()
            self.__raise_error()
        elif data == 'BOLD':
            self.__raise_error()
        elif data == "TRACULA":
            if kw.get("index"):
                return []
            self.__raise_error()
        else:
            log = logging.getLogger(__name__)
            log.error("Data type not available")
            raise (Exception("Data type not available"))