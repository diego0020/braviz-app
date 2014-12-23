from __future__ import division

import os
import re
import platform  # for the autoReader
import logging

import nibabel as nib

from numpy.linalg import inv


from braviz.readAndFilter import nibNii2vtk, applyTransform, readFlirtMatrix, \
    readFreeSurferTransform,  numpy2vtk_img, nifti_rgb2vtk,memo_ten

from braviz.readAndFilter.readDartelTransform import  dartel2GridTransform_cached
from braviz.readAndFilter.kmc_abstract import KmcAbstractReader


class kmc40Reader(KmcAbstractReader):
    """
A read and filter class designed to work with the file structure and data from the KMC pilot project which contains 40 subjects.
Data is organized into folders, and path and names for the different files can be derived from data type and id.
The path containing this structure must be set."""
    def __init__(self, path, max_cache=2000):
        "The path pointing to the __root of the file structure must be set here"
        KmcAbstractReader.__init__(self,path,path,max_cache)
        self._functional_paradigms = frozenset(("PRECISION", "POWERGRIP"))

    def _getIds(self):
        "Auxiliary function to get the available ids"
        contents = os.listdir(self.getDataRoot())
        numbers = re.compile('[0-9]+$')
        ids = [c for c in contents if numbers.match(c) is not None]
        ids.sort(key=int)
        return ids

    def decode_subject(self,subj):
        subj = str(subj)
        if len(subj) < 3:
            subj = "0" * (3 - len(subj)) + subj
        return subj

    def _getImg(self, data, subj, **kw):
        "Auxiliary function to read nifti images"
        #path=self.getDataRoot()+'/'+subj+'/MRI'
        if data == 'MRI':
            path = os.path.join(self.getDataRoot(), subj, 'MRI')
            filename = '%s-MRI-full.nii.gz' % subj
        elif data == 'FA':
            path = os.path.join(self.getDataRoot(), subj, 'camino')
            if kw.get('space', "").startswith('diff'):
                filename = 'FA_masked.nii.gz'
            else:
                filename = 'FA_mri_masked.nii.gz'
        elif data == "MD":
            path = os.path.join(self.getDataRoot(), subj, 'camino')
            if kw.get('space', "").startswith('diff'):
                filename = 'MD_masked.nii.gz'
            else:
                filename = 'MD_mri_masked.nii.gz'
        elif data == "DTI":
            path = os.path.join(self.getDataRoot(), subj, 'camino')
            if kw.get('space', '').startswith('diff'):
                filename = 'rgb_dti_masked.nii.gz'
            else:
                filename = 'rgb_dti_mri_masked.nii.gz'
        elif data == 'APARC':
            path = os.path.join(self.getDataRoot(), subj, 'Models')
            if kw.get("wm"):
                log = logging.getLogger(__name__)
                log.warning("deprecated, use WMPARC instead")
                path = os.path.join(self.getDataRoot(), subj, 'Models3')
                filename = 'wmparc.nii.gz'
            else:
                filename = 'aparc+aseg.nii.gz'
        elif data == "WMPARC":
            path = os.path.join(self.getDataRoot(), subj, 'Models3')
            filename = 'wmparc.nii.gz'
        else:
            log = logging.getLogger(__name__)
            log.error('Unknown image type %s' % data)
            raise Exception('Unknown image type %s' % data)
        wholeName = os.path.join(path, filename)
        try:
            img = nib.load(wholeName)
        except IOError as e:
            log = logging.getLogger(__name__)
            log.error(e.message)
            log.error("File %s not found" % wholeName)
            raise (Exception('File not found'))

        if kw.get('format', '').upper() == 'VTK':
            if data == "MD":
                img_data = img.get_data()
                img_data *= 1e12
                vtkImg = numpy2vtk_img(img_data)
            elif data == "DTI":
                vtkImg = nifti_rgb2vtk(img)
            else:
                vtkImg = nibNii2vtk(img)
            if kw.get('space', '').lower() == 'native':
                return vtkImg

            interpolate = True
            if data in {'APARC', "WMPARC"}:
                interpolate = False
                #print "turning off interpolate"

            img2 = applyTransform(vtkImg, transform=inv(img.get_affine()), interpolate=interpolate)
            space = kw.get('space', 'world')
            space = space.lower()
            if space == "diff" and (data in {"FA", "MD", "DTI"}):
                return img2
            return self._move_img_from_world(subj, img2, interpolate, space=space)
        space = kw.get('space', 'world')
        space = space.lower()
        if space == "diff" and (data in {"FA", "MD", "DTI"}):
            return img
        elif space == "world":
            return img
        elif space == "diff":
            #read transform:
            path = os.path.join(self.getDataRoot(), subj, 'camino')
            #matrix = readFlirtMatrix('surf2diff.mat', 'FA.nii.gz', 'orig.nii.gz', path)
            matrix = readFlirtMatrix('diff2surf.mat', 'FA.nii.gz', 'orig.nii.gz', path)
            affine = img.get_affine()
            aff2 = matrix.dot(affine)
            img2 = nib.Nifti1Image(img.get_data(), aff2)
            return img2
        log = logging.getLogger(__file__)
        log.error("Returned nifti image is in native space")
        raise NotImplementedError

    def _move_img_from_world(self, subj, img2, interpolate=False, space='world'):
        "moves an image from the world coordinate space to talairach or dartel spaces"
        space = space.lower()
        if space == 'world':
            return img2
        elif space in ('template', 'dartel'):

            dartel_warp = self._get_spm_grid_transform(subj,"dartel","back")
            img3 = applyTransform(img2, dartel_warp, origin2=(90, -126, -72), dimension2=(121, 145, 121),
                                  spacing2=(-1.5, 1.5, 1.5), interpolate=interpolate)
            #origin, dimension and spacing come from template
            return img3
        elif space[:2].lower() == 'ta':
            talairach_file = self._get_talairach_transform_name(subj)
            transform = readFreeSurferTransform(talairach_file)
            img3 = applyTransform(img2, inv(transform), (-100, -120, -110), (190, 230, 230), (1, 1, 1),
                                  interpolate=interpolate)
            return img3
        elif space[:4] in ('func', 'fmri'):
            #functional space
            paradigm = space[5:]
            #print paradigm
            paradigm = self._get_paradigm_name(paradigm)
            transform = self._read_func_transform(subj, paradigm, True)
            img3 = applyTransform(img2, transform, origin2=(78, -112, -50), dimension2=(79, 95, 68),
                                  spacing2=(-2, 2, 2),
                                  interpolate=interpolate)
            return img3
        elif space == "diff":
            path = self._get_base_fibs_dir_name(subj)
            # notice we are reading the inverse transform diff -> world
            trans = readFlirtMatrix('diff2surf.mat', 'FA.nii.gz', 'orig.nii.gz', path)
            img3 = applyTransform(img2, trans, interpolate=interpolate)
            return img3
        else:
            log = logging.getLogger(__name__)
            log.error('Unknown space %s' % space)
            raise Exception('Unknown space %s' % space)

    def _move_img_to_world(self, subj, img2, interpolate=False, space='world'):
        "moves an image from the world coordinate space to talairach or dartel spaces"
        space = space.lower()
        if space == 'world':
            return img2
        elif space in ('template', 'dartel'):

            dartel_warp = self._get_spm_grid_transform("dartel","forw")
            img3 = applyTransform(img2, dartel_warp, origin2=(90, -126, -72), dimension2=(121, 145, 121),
                                  spacing2=(-1.5, 1.5, 1.5), interpolate=interpolate)
            #origin, dimension and spacing come from template
            return img3
        elif space[:2].lower() == 'ta':
            talairach_file = self._get_talairach_transform_name(subj)
            transform = readFreeSurferTransform(talairach_file)
            img3 = applyTransform(img2, inv(transform), (-100, -120, -110), (190, 230, 230), (1, 1, 1),
                                  interpolate=interpolate)
            return img3
        elif space[:4] in ('func', 'fmri'):
            #functional space
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
            trans = readFlirtMatrix('diff2surf.mat', 'FA.nii.gz', 'orig.nii.gz', path)
            img3 = applyTransform(img2, trans, interpolate=interpolate)
            return img3
        else:
            log = logging.getLogger(__name__)
            log.error('Unknown space %s' % space)
            raise Exception('Unknown space %s' % space)

    #==========Free Surfer================
    def _get_free_surfer_models_dir_name(self,subject):
        return os.path.join(self.getDataRoot(), subject, 'Models3')

    def _get_talairach_transform_name(self,subject):
        """xfm extension"""
        return os.path.join(self.getDataRoot(), subject, 'Surf', 'talairach.xfm')

    def _get_free_surfer_stats_dir_name(self,subject):
        return os.path.join(self.getDataRoot(), subject, 'Models', 'stats')

    def _get_freesurfer_lut_name(self):
        return os.path.join(self.getDataRoot(), 'FreeSurferColorLUT.txt')

    def _get_free_surfer_morph_path(self,subj):
        return os.path.join(self.getDataRoot(), str(subj), 'Surf')

    def _get_free_surfer_labels_path(self,subj):
        return os.path.join(self.getDataRoot(), str(subj), 'Surf')

    def _get_freesurfer_surf_name(self,subj,name):
        return os.path.join(self.getDataRoot(),str(subj),"Surf",name )

    def _get_tracula_map_name(self,subj):
        raise IOError("Tracula data not available")

    #=============Camino==================
    def _get_base_fibs_name(self,subj):
        return os.path.join(self.getDataRoot(), subj, 'camino', 'streams.vtk')

    def _get_base_fibs_dir_name(self,subj):
        """
        Must contain 'diff2surf.mat', 'fa.nii.gz', 'orig.nii.gz'
        """
        return os.path.join(self.getDataRoot(), subj, 'camino')

    def _get_fa_img_name(self):
        return "FA.nii.gz"

    def _get_orig_img_name(self):
        return "orig.nii.gz"

    #==========SPM================
    def _get_paradigm_name(self,paradigm_name):
        return paradigm_name

    def _get_paradigm_dir(self,subject,name,spm=False):
        "If spm is True return the direcory containing spm.mat, else return its parent"
        if not spm:
            return os.path.join(self.getDataRoot(), subject, 'spm', name)
        else:
            return os.path.join(self.getDataRoot(), subject, 'spm', name)

    def _get_spm_grid_transform(self,subject,paradigm,direction,assume_bad_matrix=False):
        """
        Get the spm non linear registration transform grid associated to the paradigm
        Use paradigm=dartel to get the transform associated to the dartel normalization
        """
        assert direction in {"forw","back"}
        cache_key = "y_%s_%s_%s.vtk"%(paradigm,subject,direction)
        if paradigm=="dartel":
            y_file = os.path.join(self.getDataRoot(), 'Dartel', "y_%s-%s.nii.gz" % (subject,direction))
        else:
            y_file = os.path.join(self.getDataRoot(), subject, 'spm',paradigm,'y_seg_%s.nii.gz' % direction)
        return dartel2GridTransform_cached(y_file,cache_key,self,assume_bad_matrix)

    def _read_func_transform(self,subject,paradigm_name,inverse=False):
        paradigm_name = self._get_paradigm_name(paradigm_name)
        path = os.path.join(self.getDataRoot(),subject,"spm" )
        T1_func = os.path.join(path, paradigm_name, 'T1.nii.gz')
        T1_world = os.path.join(path, 'T1', 'T1.nii.gz')
        return self._read_func_transform_internal(subject,paradigm_name,inverse,path,T1_func,T1_world)


    @staticmethod
    @memo_ten
    def get_auto_data_root():
        node_id = platform.node()
        node = known_nodes.get(node_id)
        if node is not None:
            return node[0]
        log = logging.getLogger(__name__)
        log.error("Unknown node")
        raise Exception("Unkown node")

    @staticmethod
    @memo_ten
    def get_auto_dyn_data_root():
        return kmc40Reader.get_auto_data_root()

    @staticmethod
    def autoReader(**kw_args):
        """Initialized a kmc40Reader based on the computer name"""
        node_id = platform.node()
        node = known_nodes.get(node_id)
        log = logging.getLogger(__name__)
        if node is not None:
            data_root = node[0]
            if kw_args.get('max_cache', 0) > 0:
                max_cache = kw_args.pop('max_cache')

                log.info("Max cache set to %.2f MB" % max_cache)
            else:
                max_cache = node[1]
            return kmc40Reader(data_root, max_cache=max_cache)
        else:
            print "Unknown node %s, please enter route to data" % node_id
            path = raw_input('KMC_root: ')
            return kmc40Reader(path, **kw_args)
            # add other strategies to find the project __root


known_nodes = {  #
                 # Name          :  ( data root                   , cache size in MB)
                 'gambita.uniandes.edu.co': ('/media/DATAPART5/KAB-db', 4000),
                 'Unidelosandes': ('K:\\JohanaForero\\KAB-db', 1200),
                 'dieg8': (r'C:\Users\Diego\Documents\kmc40-db\KAB-db', 4000),
                 'TiberioHernande': (r'E:\KAB-db', 1100),
                 'localhost.localdomain': ('/home/diego/braviz/subjects', 1000),
                 'ISIS-EML725001': (r'C:\KAB-db', 8000),
                 'archi5': (r"/mnt/win/Users/Diego/Documents/kmc40-db/KAB-db", 4000),
                 'dellingr.vrac.iastate.edu': (r"/Volumes/diegoa/KAB-db", 14000),
                 'MacAirCyril-S.local': ("/Users/CS/Desktop/diego_data", 7000),
                 'ATHPC1304': (r"F:\ProyectoCanguro\KAB-db", 14000),
                 'IIND-EML754066': (r"C:\Users\da.angulo39\Documents\KAB-db", 2000),
                 'da-angulo': (r"D:\KAB-db", 4000),
                 'Echer': ('H:/KAB-db',8000),
                 'imagine-PC' : ("E:\\KAB-db",50000)
}

