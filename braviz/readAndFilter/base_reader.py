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


from __future__ import division, print_function

import base64
import os
import hashlib
import logging

import tempfile

from braviz.readAndFilter.cache import cache_function, CacheContainer

_auto_temp_dir = os.path.join(tempfile.gettempdir(), "braviz_temp")


class BaseReader(object):

    """
Provide access to projects' non-tabular data

Project readers provide a common interface to each projects underlying data. All project readers should be inherited
from this class. Most data access is carried out through the :meth:`get` method. Underneath this method locates the
appropriate data files and transformations, and returns the requested data in the requested coordinates system.

An instance of this class will always return empty lists when indexes are requested and raise exceptions when
data is requested. To get a more useful class you should create your own subclass.
"""
    _memory_cache_container = CacheContainer()

    def __init__(self, max_cache=100, **kwargs):
        """
        The base reader handles a memory cache for speeding repeated access for the same data.

        Args:
            max_cache (int) : The maximum amount of memory in MB that can be used for cache
            **kwargs : Ignored, maybe used by derived classes

        Note that subclasses may have more arguments in their constructors.
        """

        self._memory_cache_container.max_cache = max_cache
        self.__static_root = _auto_temp_dir
        return

    @cache_function(_memory_cache_container)
    def get(self, data, subj_id=None, space='world', **kwargs):
        """Provides access to geometric data in an specified coordinate system.

        Args:
            data (str): Case insensitive, the type of data requested. Currently the possible values are

                ===========  =====================================================
                Ids          ids of all subjects in the study as a list

                             Returns a list of ids
                -----------  -----------------------------------------------------
                IMAGE        structural image of the given subject
                             requires ``name=<modality>``. The available modalities
                             depend of the project, but some common values are
                             MRI, FA, and MD.

                             Use ``index=True`` to get a list of available modalities.

                             All of these are single channel images.
                             Other modalities
                             may be available under DTI and Label.

                             Returns a nibabel image object,
                             use ``format="VTK"`` to
                             receive a vtkImageData instead.
                -----------  -----------------------------------------------------
                DTI          RGB DTI image

                             returns a nibabel image object, use ``format="VTK"`` to
                             receive a vtkImageData instead.
                -----------  -----------------------------------------------------
                Label        Read Label Map images

                             requires ``name=<map>``. Some common maps are

                             APARC: FreeSurfer Aparc (Auto Parcelation) image
                             WMPARC: FreeSurfer WMParc (White Matter Parcelation) image

                             use ``index=True`` to get a list of available maps

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

                             ``SPM = True`` will return a :class:`~braviz.readAndFilter.read_spm.SpmFileReader`
                              with the data contained in the *spm.mat* file.
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

                             ``ids=True`` will return the ids of the polylines, based in the whole tractography, that
                             cross the specified waypoints.

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
            **kwargs: Arguments specific to each data type

        """
        subj_id = self._decode_subject(subj_id)
        return self._get(data, subj_id, space, **kwargs)

    def _decode_subject(self, subj):
        """
        Transforms the subject into the standard format, should be called at the start of all public methods
        """
        return subj

    def move_img_to_world(self, img, source_space, subj, interpolate=False):
        """
        Resamples an image into the world coordinate system

        Args:
            img (vtkImageData): source image
            source_space (str): source image coordinate system
            subj: Subject to whom the image belongs
            interpolate (bool): If False nearest neighbours interpolation is applied, useful for label maps
        Returns:
            Resliced image in world coordinate system
        """
        raise NotImplementedError

    def move_img_from_world(self, img, target_space, subj, interpolate=False):
        """
        Resamples an image from the world coordinates into some other coordinate system

        Args:
            img (vtkImageData): source image
            target_space (str): destination coordinate system
            subj: Subject to whom the image belongs
            interpolate (bool): If False nearest neighbours interpolation is applied, useful for label maps
        Returns:
            Resliced image in *target_space* coordinates
        """
        raise NotImplementedError

    def transform_points_to_space(self, point_set, space, subj, inverse=False):
        """
        Transforms a set of points into another coordinate system

        By defaults moves from world coordinates to another system, but these behaviour is reversed if the
        *inverse* parameter is True. At the moment, to move from an arbitrary coordinate system to another it is
        necessary to use the world coordinates as stopover

        Args:
            point_set (vtkPolyData,vtkPoints,vtkDataSet): source points
            space (str): origin or destination coordinate system, depending on *inverse*
            subj: Subject to whom the points belong
            inverse (bool): If false points are moved from world to *space*, else the points are moved from
            *space* to world.
        Returns:
            Transformed points
        """
        raise NotImplementedError

    def clear_mem_cache(self):
        """
        Clears the contents of the memory cache
        """
        log = logging.getLogger(__name__)
        log.info("Clearing cache")
        self._memory_cache_container.clear()

    def save_into_cache(self, key, data):
        """
        Saves some data into a cache, uses vtkDataWriter or :mod:`cPickle` for python objects.

        Data is stored using a *key*. This value is required to retrieve the data or to overwrite it.
        To retrieve data use :func:`load_from_cache`.

        Args:
            key(str): Unique value used to reference the data into the cache,
                if data with the same key exists it will be overwritten
            data: Data object to store
        Returns:
            True if the value was successfully saved, False if there was a problem
        """
        return False

    def load_from_cache(self, key):
        """
        Loads data stored into cache with :func:`save_into_cache`

        Args:
            key(str): Key used to store the object

        Returns:
            If successful returns the object as it was previously stored.

            In case of failure returns `None`
        """
        return None

    def clear_cache_dir(self, last_word=False):
        """
        Clears all the contents of the disk cache

        Args:
            last_word (bool) : If True goes on to clear the cache, otherwise does nothing
        """
        import shutil
        if last_word is True:
            cache_dir = os.path.join(self.get_dyn_data_root(), '.braviz_cache')
            try:
                shutil.rmtree(cache_dir)
            except OSError:
                pass
            os.mkdir(cache_dir)
        else:
            print("If you are sure you want to delete the cache dir, call this function with a True argument")

    def get_data_root(self):
        """Returns the root directory from which this instance reads data

        This directory should be readable by the current user
        """
        return self.__static_root

    def get_dyn_data_root(self):
        """Returns the root directory into which this instance stores cache and data

        This directory should be writable by the current user
        """
        return self.__static_root

    @staticmethod
    def get_auto_data_root():
        """
        Returns the root directory that would be used by an auto_reader to read data
        """
        return _auto_temp_dir

    @staticmethod
    def get_auto_dyn_data_root():
        """
        Returns the root directory that would be used by an auto_reader to store data
        """
        return _auto_temp_dir

    @staticmethod
    def clear_dynamic_data_dir(dir_name):
        """
        Clears data written by braviz from a directory

        Args:
            dir_name (str) : Path to the root location where data was written, this is,
                the value returned by :meth:`get_dyn_data_root` in the reader that stored the data.
        """
        try:
            os.walk(os.path.join(dir_name, "logs"))
            os.walk(os.path.join(dir_name, ".braviz_cache"))
            os.walk(os.path.join(dir_name, "braviz_data", "scenarios"))
            for sub_dir in ("logs", ".braviz_cache", "braviz_data"):
                top = os.path.join(dir_name, sub_dir)
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
        Creates the basic directory structure used for braviz starting at the specified path.

        Args:
            dir_name(str): The path where the structure will be created.
                If None, the value returned by :meth:`get_auto_dyn_data_root` will be used
        """
        from braviz.readAndFilter import check_db
        if dir_name is None:
            dir_name = BaseReader.get_auto_dyn_data_root()
        os.makedirs(os.path.join(dir_name, "logs"))
        os.makedirs(os.path.join(dir_name, ".braviz_cache"))
        os.makedirs(os.path.join(dir_name, "braviz_data", "scenarios"))
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
            ilegal = ['_', '<', '>', ':', '"', '/', "\\", '|', '?', '*']
            for i, il in enumerate(ilegal):
                key = key.replace(il, '%d_' % i)
        return key

    def __raise_error(self):
        """
        Raises an IOError
        """
        raise IOError("Data not available in BaseReader")

    def _get(self, data, subj=None, space='world', **kw):
        """Internal: decode instruction and dispatch"""
        data = data.upper()
        if data == 'IMAGE':
            if kw.get("index"):
                return []
            self.__raise_error()
        elif data == "DTI":
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
        elif data == "LABEL":
            if kw.get("index"):
                return []
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
