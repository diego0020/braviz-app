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

import os
import re
from braviz.readAndFilter.config_file import get_host_config
import logging

import nibabel as nib

from numpy.linalg import inv


from braviz.readAndFilter.cache import memo_ten
from braviz.readAndFilter.images import numpy2vtk_img, nifti_rgb2vtk, nibNii2vtk

from braviz.readAndFilter.kmc_abstract import KmcAbstractReader
from braviz.readAndFilter.transforms import applyTransform, readFreeSurferTransform, readFlirtMatrix
from braviz.visualization.create_lut import get_colorbrewer_lut



class PlutonReader(KmcAbstractReader):
    def __init__(self, static_path, dynamic_path, max_cache=2000):
        super(PlutonReader, self).__init__(static_path, dynamic_path, max_cache)
        self._available_images = frozenset(("FA", "MRI"))
        self._functional_paradigms = frozenset()
        self._named_bundles = frozenset()
    def _getIds(self):
        """Auxiliary function to get the available ids"""
        contents = os.listdir(self.get_data_root())
        numbers = re.compile('[0-9]+$')
        ids = [c for c in contents if numbers.match(c) is not None]
        ids.sort(key=int)
        return ids

    def _decode_subject(self, subj):
        subj = str(subj)
        return subj

    def _get_img(self, image_name, subj, space,  **kw):
        """Auxiliary function to read nifti images"""
        # path=self.getDataRoot()+'/'+subj+'/MRI'
        path = os.path.join(self.get_data_root(), subj, "camino")
        filename="fa_.nii.gz"
        wholeName = os.path.join(path, filename)
        try:
            img = nib.load(wholeName)
        except IOError as e:
            log = logging.getLogger(__name__)
            log.error(e.message)
            log.error("File %s not found" % wholeName)
            raise (Exception('File not found'))

        if kw.get('format', '').upper() == 'VTK':
            vtkImg = nibNii2vtk(img)
            if space == 'native':
                return vtkImg

            interpolate = True
            if image_name in {'APARC', "WMPARC"}:
                interpolate = False
                # print "turning off interpolate"

            img2 = applyTransform(
                vtkImg, transform=inv(img.get_affine()), interpolate=interpolate)

            if space == "diff" and (image_name in {"FA", "MD", "DTI"}):
                return img2
            return self._move_img_from_world(subj, img2, interpolate, space=space)

        if space == "diff" and (image_name in {"FA", "MD", "DTI"}):
            return img
        elif space == "subject":
            return img
        elif space == "diff":
            # read transform:
            return img
        log = logging.getLogger(__file__)
        log.error("Returned nifti image is in native space")
        raise NotImplementedError

    def _move_img_from_world(self, subj, img2, interpolate=False, space='subject'):
        """moves an image from the subject coordinate space to talairach or dartel spaces"""
        return img2
        if space == 'subject':
            return img2
        elif space in ('template', 'dartel'):

            dartel_warp = self._get_spm_grid_transform(subj, "dartel", "back")
            img3 = applyTransform(img2, dartel_warp, origin2=(90, -126, -72), dimension2=(121, 145, 121),
                                  spacing2=(-1.5, 1.5, 1.5), interpolate=interpolate)
            # origin, dimension and spacing come from template
            return img3
        elif space[:2].lower() == 'ta':
            talairach_file = self._get_talairach_transform_name(subj)
            transform = readFreeSurferTransform(talairach_file)
            img3 = applyTransform(img2, inv(transform), (-100, -120, -110), (190, 230, 230), (1, 1, 1),
                                  interpolate=interpolate)
            return img3
        elif space[:4] in ('func', 'fmri'):
            # functional space
            paradigm = space[5:]
            # print paradigm
            paradigm = self._get_paradigm_name(paradigm)
            transform = self._read_func_transform(subj, paradigm, True)
            img3 = applyTransform(img2, transform, origin2=(78, -112, -50), dimension2=(79, 95, 68),
                                  spacing2=(-2, 2, 2),
                                  interpolate=interpolate)
            return img3
        elif space == "diff":
            path = self._get_base_fibs_dir_name(subj)
            # notice we are reading the inverse transform diff -> world
            trans = readFlirtMatrix(
                'diff2surf.mat', 'FA.nii.gz', 'orig.nii.gz', path)
            img3 = applyTransform(img2, trans, interpolate=interpolate)
            return img3
        else:
            log = logging.getLogger(__name__)
            log.error('Unknown space %s' % space)
            raise Exception('Unknown space %s' % space)

    def _move_img_to_subject(self, subj, img2, interpolate=False, space='subject'):
        """moves an image from the subject coordinate space to talairach or dartel spaces"""
        return img2
        if space == 'subject':
            return img2
        elif space in ('template', 'dartel'):

            dartel_warp = self._get_spm_grid_transform("dartel", "forw")
            img3 = applyTransform(img2, dartel_warp, origin2=(90, -126, -72), dimension2=(121, 145, 121),
                                  spacing2=(-1.5, 1.5, 1.5), interpolate=interpolate)
            # origin, dimension and spacing come from template
            return img3
        elif space[:2].lower() == 'ta':
            talairach_file = self._get_talairach_transform_name(subj)
            transform = readFreeSurferTransform(talairach_file)
            img3 = applyTransform(img2, inv(transform), (-100, -120, -110), (190, 230, 230), (1, 1, 1),
                                  interpolate=interpolate)
            return img3
        elif space[:4] in ('func', 'fmri'):
            # functional space
            paradigm = space[5:]
            paradigm = self._get_paradigm_name(paradigm)
            transform = self._read_func_transform(subj, paradigm, True)
            img3 = applyTransform(img2, transform, origin2=(78, -112, -50), dimension2=(79, 95, 68),
                                  spacing2=(-2, 2, 2),
                                  interpolate=interpolate)
            return img3
        elif space == "diff":
            path = self._get_base_fibs_dir_name(subj)
            # notice we are reading the inverse transform diff -> world
            trans = readFlirtMatrix(
                'diff2surf.mat', 'FA.nii.gz', 'orig.nii.gz', path)
            img3 = applyTransform(img2, trans, interpolate=interpolate)
            return img3
        else:
            log = logging.getLogger(__name__)
            log.error('Unknown space %s' % space)
            raise Exception('Unknown space %s' % space)

    #==========Free Surfer================
    def _get_free_surfer_models_dir_name(self, subject):
            return os.path.join(self.get_data_root(), 'models', subject)

    def _get_talairach_transform_name(self, subject):
        """xfm extension"""
        return os.path.join(self.get_data_root(), "freesurfer", subject, "mri", "transforms", 'talairach.xfm')

    def _get_free_surfer_stats_dir_name(self, subject):
        return os.path.join(self.get_data_root(), 'freesurfer', subject, 'stats')

    def _get_freesurfer_lut_name(self):
        return os.path.join(self.get_data_root(), "freesurfer", 'FreeSurferColorLUT.txt')

    def _get_free_surfer_morph_path(self, subj):
        return os.path.join(self.get_data_root(), "freesurfer", str(subj), 'surf')

    def _get_free_surfer_labels_path(self, subj):
        return os.path.join(self.get_data_root(), "freesurfer", str(subj), 'label')

    def _get_freesurfer_surf_name(self, subj, name):
        return os.path.join(self.get_data_root(), "freesurfer", str(subj), "surf", name)

    def _get_tracula_map_name(self, subj):
        data_dir = os.path.join(
            self.get_data_root(), "freesurfer", "%s" % subj, "dpath")
        tracks_file = "merged_avg33_mni_bbr.mgz"
        tracks_full_file = os.path.join(data_dir, tracks_file)
        return tracks_full_file

    #=============Camino==================

    def _get_base_fibs_name(self, subj):
        # return os.path.join(self.get_data_root(), "tractography",subj,
        # 'CaminoTracts.vtk')
        return os.path.join(self.get_data_root(), subj, "camino", 'camino_tracks.vtk')

    def _get_base_fibs_dir_name(self, subj):
        """
        Must contain 'diff2surf.mat', 'fa.nii.gz', 'orig.nii.gz'
        """
        # return os.path.join(self.get_data_root(), "tractography",subj)
        return os.path.join(self.get_data_root(), subj, "camino")

    def _get_fa_img_name(self):
        return "fa_.nii.gz"

    def _get_orig_img_name(self):
        return "orig.nii.gz"

    def _get_md_lut(self):
        lut = get_colorbrewer_lut(491e-6, 924e-6, "YlGnBu", 9, invert=True)
        return lut
    #==========SPM================
    def _get_paradigm_name(self, paradigm_name):
        return paradigm_name.upper()



    @staticmethod
    @memo_ten
    def get_auto_data_root():
        project_name = os.path.basename(__file__).split('.')[0]
        log = logging.getLogger(__name__)
        try:
            config = get_host_config(project_name)
        except KeyError as e:
            log.exception(e)
            raise
        data_root = config["data root"]
        if not os.path.isabs(data_root):
            data_root = os.path.join(os.path.dirname(__file__),"../applications",data_root)
        return data_root

    @staticmethod
    @memo_ten
    def get_auto_dyn_data_root():
        project_name = os.path.basename(__file__).split('.')[0]
        log = logging.getLogger(__name__)
        try:
            config = get_host_config(project_name)
        except KeyError as e:
            log.exception(e)
            raise
        data_root = config["dynamic data root"]
        if not os.path.isabs(data_root):
            data_root = os.path.join(os.path.dirname(__file__),"../applications",data_root)
        return data_root

    @staticmethod
    def get_auto_reader(**kw_args):
        """Initialized a kmc400Reader based on the computer name"""
        project_name = os.path.basename(__file__).split('.')[0]
        log = logging.getLogger(__name__)
        try:
            config = get_host_config(project_name)
        except KeyError as e:
            log.error(e.message)
            log.exception(e)
            raise
        static_data_root = config["data root"]
        if not os.path.isabs(static_data_root):
            static_data_root = os.path.join(os.path.dirname(__file__),"../applications",static_data_root)
        dyn_data_root = config["dynamic data root"]
        if not os.path.isabs(dyn_data_root):
            dyn_data_root = os.path.join(os.path.dirname(__file__),"../applications",dyn_data_root)
        if kw_args.get('max_cache', 0) > 0:
            max_cache = kw_args.pop('max_cache')
            log.info("Max cache set to %.2f MB" % max_cache)
        else:
            max_cache = config["memory (mb)"]
        return PlutonReader(static_data_root, dyn_data_root, max_cache=max_cache)
