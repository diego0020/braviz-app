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
    def get(self,data, subj_id=None, space='world', **kw):
        """
        Provides access to geometric data in an specified coordinate system.

        All vtkStructures can use an additional 'space' argument to specify the space of the output coordinates.
        Available spaces for all data are: world, talairach and dartel. Some data may support additional values
        data should be one of:

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
                -----------  -----------------------------------------------------
                WMparc       FreeSurfer WMParc (White Matter Parcelation) image

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.
                -----------  -----------------------------------------------------
                fMRI         SPM t-score map

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.
                -----------  -----------------------------------------------------
                BOLD         SPM, pre-processed bold series

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.
                -----------  -----------------------------------------------------
                Model        Reconstruction of FreeSurfer segmented structure
                -----------  -----------------------------------------------------
                Surf         FreeSurfer brain cortex surface reconstruction
                -----------  -----------------------------------------------------
                Surf_Scalar  Scalars for a FreeSurfer surfaces
                -----------  -----------------------------------------------------
                Fibers       Tractography
                -----------  -----------------------------------------------------
                Tracula      Tracula probabilistic tractography
                ===========  =====================================================

        MRI: By default returns a nibnii object, use format='VTK' to get a vtkImageData object.
             Additionally use space='native' to ignore the nifti transform.

        FA:  Same options as MRI, but space also accepts 'diffusion', also accepts 'lut'

        MD:  Same options as MRI, but space also accepts 'diffusion'

        DTI: Same options as MRI, but space also accepts 'diffusion'

        APARC: Same options as MRI, but also accepts 'lut' to get the corresponding look up table

        WMPARC: Same options as MRI, but also accepts 'lut' to get the corresponding look up table

        FMRI: requires name=<Paradigm>, may also receive contrast to indicate a specific contrast (the defautl is 1)
              Use contrasts_dict = True togethet with paradigms to get the names of the contrasts
              Use SPM = True to get a representation of the corresponding spm file

        BOLD: requires name=<Paradigm>, only nifti format is available

        MODEL:Use name=<model> to get the vtkPolyData. Use index=True to get a list of the available models for a subject.
              Use color=True to get the standard color associated to the structure
              Use volume=True to get the volume of the structure
              Use label=True to get the label corresponding to the structure

        SURF: Use name=<surface> and hemi=<r|h> to get the vtkPolyData of a free surfer surface reconstruction,
              use scalars to add scalars to the data
              surface must be orig pial white smoothwm inflated sphere
              us normals = 0 to avoid calculating normals

        SURF_SCALAR: Use scalar=<name> and hemi=<l|r> to get scalar data associated to a SURF.
                     Use index=True to get a list of available scalars,
                     Use lut=True to get the associated lookUpTable for Annotations and a standard LUT for morphology

        FIBERS: The default space is world, use space='diff' to get fibers in diffusion space.
                Use waypoint=<model-name> to restrict to fibers passing through a given MODEL as indicated above.
                waypoint may also be a list of models. In this case you will by default get tracts that pass through all
                the models if the list. This can be changed by setting operation='or', to get tracts which pass through
                any of the models.
                Can accept color=<orient|fa|curv|y|rand> to get different color scalars
                Otherwise can acecpt scalars=<fa_p|fa_l|md_p|md_l|length>
                In this case you may use lut=T to get the corresponding LUT
                'Name' can be provided instead of waypoint to get custom tracts, to get a list of currently available
                named tracts call index=True
                Use db_id = 'id' to read a fiber stored in the braviz data base

        TRACULA: The default space is world, use space='diff' to get fibers in diffusion space.
                 Requires name = <track-name>. Use Index = True to get a list of available bundles.
                 The default returns contours at 0.20 of the maximum aposteriori probability.
                 Use contour = <percentage> to get different contours
                 Use map = True to get the probability map as an image.
                 Use color=True to get the default color for the structure

        TENSORS: Get an unstructured grid containing tensors at the points where they are available
                 and scalars representing the orientation of the main eigenvector
                 Use space=world to get output in world coordinates [experimental]

        """
        subj_id = self.decode_subject(subj_id)
        return self._get(data, subj_id,space, **kw)

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