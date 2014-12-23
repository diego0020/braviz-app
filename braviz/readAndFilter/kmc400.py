from __future__ import division


import os
import re
import platform  # for the autoReader

import logging

import nibabel as nib
import numpy as np
from numpy.linalg import inv


from braviz.readAndFilter import nibNii2vtk, applyTransform, readFlirtMatrix,readFreeSurferTransform,  numpy2vtk_img,\
    nifti_rgb2vtk, memo_ten

from braviz.readAndFilter.kmc_abstract import KmcAbstractReader

from braviz.readAndFilter.readDartelTransform import dartel2GridTransform_cached

class kmc400Reader(KmcAbstractReader):
    """
A read and filter class designed to work with the file structure and data from the KMC pilot project which contains 40 subjects.
Data is organized into folders, and path and names for the different files can be derived from data type and id.
The path containing this structure must be set."""

    def __init__(self, static_root,dynamic_route, max_cache=2000):
        "The path pointing to the __root of the file structure must be set here"
        KmcAbstractReader.__init__(self,static_root,dynamic_route,max_cache)

        self._functional_paradigms=frozenset(('ATENCION', 'COORDINACION', 'MEMORIA', 'MIEDO', 'PRENSION'))


    def _getIds(self):
        "Auxiliary function to get the available ids"
        contents = os.listdir(os.path.join(self.getDataRoot(),"freeSurfer_Tracula"))
        numbers = re.compile('[0-9]+$')
        ids = [c for c in contents if numbers.match(c) is not None]
        ids.sort(key=int)
        return ids

    def decode_subject(self,subj):
        return str(subj)

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
            paradigm =self._get_paradigm_name(paradigm)
            transform = self._read_func_transform(subj, paradigm, True)
            img3 = applyTransform(img2, transform, origin2=(78, -112, -50), dimension2=(79, 95, 68),
                                  spacing2=(-2, 2, 2),
                                  interpolate=interpolate)
            return img3
        elif space == "diff":
            #TODO: Check, looks wrong
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
        ref = self.get("mri",subj,space="world",format="vtk")
        origin = ref.GetOrigin()
        spacing = ref.GetSpacing()
        dims = ref.GetDimensions()
        if space in ('template', 'dartel'):
            dartel_warp = self._get_spm_grid_transform(subj,"dartel","forw")
            img3 = applyTransform(img2, dartel_warp, origin2=origin, dimension2=dims,
                                  spacing2=spacing, interpolate=interpolate)
            #origin, dimension and spacing come from template
            return img3
        elif space[:2].lower() == 'ta':
            talairach_file = self._get_talairach_transform_name(subj)
            transform = readFreeSurferTransform(talairach_file)
            img3 = applyTransform(img2, transform, origin, dims, spacing,
                                  interpolate=interpolate)
            return img3
        elif space[:4] in ('func', 'fmri'):
            #functional space
            paradigm = space[5:]
            #print paradigm
            paradigm =self._get_paradigm_name(paradigm)
            transform = self._read_func_transform(subj, paradigm, False)
            img3 = applyTransform(img2, transform, origin2=origin, dimension2=dims,
                                  spacing2=spacing,
                                  interpolate=interpolate)
            return img3
        elif space == "diff":
            path = self._get_base_fibs_dir_name(subj)
            # notice we are reading the inverse transform diff -> world
            trans = readFlirtMatrix('diff2surf.mat', 'FA.nii.gz', 'orig.nii.gz', path)
            img3 = applyTransform(img2, trans, interpolate=interpolate,origin2=origin,spacing2=spacing,dimension2=dims)
            return img3
        else:
            log = logging.getLogger(__name__)
            log.error('Unknown space %s' % space)
            raise Exception('Unknown space %s' % space)

    def _getImg(self, data, subj, **kw):
        "Auxiliary function to read nifti images"
        #path=self.__root+'/'+str(subj)+'/MRI'
        if data == 'MRI':
            path = os.path.join(self.getDataRoot(), "nii",str(subj))
            filename = 'MPRAGEmodifiedSENSE.nii.gz'
        elif data == 'FA':
            path = os.path.join(self.getDataRoot(), 'tractography',str(subj))
            if kw.get('space',"").startswith('diff'):
                filename = 'fa.nii.gz'
            else:
                filename = 'fa_mri.nii.gz'
        elif data == "MD":
            path = os.path.join(self.getDataRoot(), 'tractography',str(subj))
            if kw.get('space',"").startswith('diff'):
                filename = 'md.nii.gz'
            else:
                filename = 'md_mri.nii.gz'
        elif data == "DTI":
            path = os.path.join(self.getDataRoot(), 'tractography',str(subj))
            if kw.get('space','').startswith('diff'):
                filename = 'rgb_dti.nii.gz'
                #filename = 'rgb_dti_masked.nii.gz'
            else:
                filename = 'rgb_dti_mri.nii.gz'
                #filename = 'rgb_dti_mri_masked.nii.gz'
        elif data == 'APARC':
            path = os.path.join(self.getDataRoot(), "slicer_models",str(subj))
            if kw.get("wm"):
                filename = 'wmparc.nii.gz'
                print "Warning... deprecated, use WMPARC instead"
            else:
                filename = 'aparc+aseg.nii.gz'
        elif data == "WMPARC":
            path = os.path.join(self.getDataRoot(), "slicer_models",str(subj))
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
            log.exception(e)
            log.error("File %s not found" % wholeName)
            raise (Exception('File not found'))

        if kw.get('format', '').upper() == 'VTK':
            if data == "MD":
                img_data=img.get_data()
                img_data *= 1e5
                #remove lower than 0
                img_data[img_data<0]=0
                #remove bigger than 1000
                img_data[img_data>1000]=1000
                vtkImg = numpy2vtk_img(img_data)
            elif data == "DTI":
                vtkImg = nifti_rgb2vtk(img)
            else:
                vtkImg = nibNii2vtk(img)
            if kw.get('space', '').lower() == 'native':
                return vtkImg

            interpolate = True
            if data in {'APARC', 'WMPARC'}:
                interpolate = False
                #print "turning off interpolate"

            img2 = applyTransform(vtkImg, transform=inv(img.get_affine()), interpolate=interpolate)
            space = kw.get('space', 'world')
            if space == "diff" and (data in {"FA","MD","DTI"}):
                return img2
            return self._move_img_from_world(subj, img2, interpolate, space=space)
        space = kw.get('space', 'world')
        space = space.lower()
        if space == "diff" and (data in {"FA","MD","DTI"}):
            return img
        elif space == "world":
            return img
        elif space == "diff":
            #read transform:
            path = self._get_base_fibs_dir_name(subj)
            #matrix = readFlirtMatrix('surf2diff.mat', 'orig.nii.gz', 'FA.nii.gz', path)
            matrix = readFlirtMatrix('diff2surf.mat', 'fa.nii.gz', 'orig.nii.gz', path)
            matrix = np.linalg.inv(matrix)
            affine = img.get_affine()
            aff2 = matrix.dot(affine)
            img2=nib.Nifti1Image(img.get_data(),aff2)
            return img2
        elif space[:2] == "ta":
            talairach_file = self._get_talairach_transform_name(subj)
            #TODO needs more testing
            transform = readFreeSurferTransform(talairach_file)
            affine = img.get_affine()
            aff2 = transform.dot(affine)
            img2=nib.Nifti1Image(img.get_data(),aff2)
            return img2
        raise NotImplementedError("Returned nifti image is in world space")


    #==========Free Surfer================
    def _get_free_surfer_models_dir_name(self,subject):
        return os.path.join(self.getDataRoot(), 'slicer_models',subject)

    def _get_talairach_transform_name(self,subject):
        """xfm extension"""
        return os.path.join(self.getDataRoot(), "freeSurfer_Tracula", subject, "mri","transforms",'talairach.xfm')

    def _get_free_surfer_stats_dir_name(self,subject):
        return os.path.join(self.getDataRoot(), 'freeSurfer_Tracula',subject, 'stats')

    def _get_freesurfer_lut_name(self):
        return os.path.join(self.getDataRoot(),"freeSurfer_Tracula", 'FreeSurferColorLUT.txt')

    def _get_free_surfer_morph_path(self,subj):
        return os.path.join(self.getDataRoot(), "freeSurfer_Tracula",str(subj), 'surf')

    def _get_free_surfer_labels_path(self,subj):
        return os.path.join(self.getDataRoot(), "freeSurfer_Tracula",str(subj), 'label')

    def _get_freesurfer_surf_name(self,subj,name):
        return os.path.join(self.getDataRoot(),"freeSurfer_Tracula",str(subj),"surf",name )

    def _get_tracula_map_name(self,subj):
        data_dir = os.path.join(self.getDataRoot(),"freeSurfer_Tracula","%s"%subj,"dpath")
        tracks_file = "merged_avg33_mni_bbr.mgz"
        tracks_full_file = os.path.join(data_dir,tracks_file)
        return tracks_full_file

    #=============Camino==================
    def _get_base_fibs_name(self,subj):
        return os.path.join(self.getDataRoot(), "tractography",subj, 'CaminoTracts.vtk')

    def _get_base_fibs_dir_name(self,subj):
        """
        Must contain 'diff2surf.mat', 'fa.nii.gz', 'orig.nii.gz'
        """
        return os.path.join(self.getDataRoot(), "tractography",subj)

    def _get_fa_img_name(self):
        return "fa.nii.gz"

    def _get_orig_img_name(self):
        return "orig.nii.gz"
    #==========SPM================
    def _get_paradigm_name(self,paradigm_name):
        if paradigm_name.endswith("SENSE"):
            return paradigm_name
        paradigm_name = paradigm_name.upper()
        assert paradigm_name in self._functional_paradigms

        if paradigm_name=="MIEDO":
            paradigm_name="MIEDOSofTone"
        paradigm_name +="SENSE"
        return paradigm_name

    def _get_paradigm_dir(self,subject,name,spm=False):
        "If spm is True return the direcory containing spm.mat, else return its parent"
        if not spm:
            return os.path.join(self.getDataRoot(),"spm", subject,name)
        else:
            return os.path.join(self.getDataRoot(), "spm",subject,name,"FirstLevel")

    def _get_spm_grid_transform(self,subject,paradigm,direction,assume_bad_matrix=False):
        """
        Get the spm non linear registration transform grid associated to the paradigm
        Use paradigm=dartel to get the transform associated to the dartel normalization
        """
        assert direction in {"forw","back"}
        cache_key = "y_%s_%s_%s.vtk"%(paradigm,subject,direction)
        if paradigm=="dartel":
            y_file = os.path.join(self.getDataRoot(),"spm",subject,"T1", "y_dartel_%s.nii" % direction)


        else:
            y_file = os.path.join(self.getDataRoot(),"spm", subject,paradigm, "y_seg_%s.nii.gz" % direction)

        return dartel2GridTransform_cached(y_file,cache_key,self,assume_bad_matrix)

    def _read_func_transform(self,subject,paradigm_name,inverse=False):
        paradigm_name = self._get_paradigm_name(paradigm_name)
        path = os.path.join(self.getDataRoot(), 'spm',subject )
        T1_func = os.path.join(path, paradigm_name, 'T1.nii')
        T1_world = os.path.join(path, 'T1', 'T1.nii')
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
        node_id = platform.node()
        node = known_nodes.get(node_id)
        if node is not None:
            return node[1]
        log = logging.getLogger(__name__)
        log.error("Unknown node")
        raise Exception("Unkown node")

    @staticmethod
    def autoReader(**kw_args):
        """Initialized a kmc400Reader based on the computer name"""
        node_id = platform.node()
        node = known_nodes.get(node_id)
        log = logging.getLogger(__name__)
        if node is not None:
            static_data_root = node[0]
            dyn_data_root = node[1]

            if kw_args.get('max_cache', 0) > 0:
                max_cache = kw_args.pop('max_cache')

                log.info("Max cache set to %.2f MB" % max_cache)
            else:
                max_cache = node[2]
            return kmc400Reader(static_data_root,dyn_data_root, max_cache=max_cache)
        else:
            print "Unknown node %s, please enter route to data" % node_id
            path = raw_input('KMC_root: ')
            return kmc400Reader(path, **kw_args)
            # add other strategies to find the project __root
    
    
known_nodes = {  #
    # Name          :  ( static data root, dyn data root , cache size in MB)
    'gambita.uniandes.edu.co': ('/media/DATAPART5/kmc400','/media/DATAPART5/kmc400_braviz', 4000),
    #'dieg8': (r'E:\kmc400',"E:/kmc400_braviz", 4000),
    'dieg8': (r'C:\Users\Diego\Documents\kmc400',r"C:\Users\Diego\Documents/kmc400_braviz", 4000),
    'archi5': ('/mnt/win/Users/Diego/Documents/kmc400',"/mnt/win/Users/Diego/Documents/kmc400_braviz", 4000),
    'ATHPC1304' : (r"Z:",r"F:\ProyectoCanguro\kmc400_braviz",14000),
    'IIND-EML754066' : (r"Z:",r"C:\Users\da.angulo39\Documents\kmc400_braviz",2000),
    #'da-angulo': ("Z:\\","D:\\kmc400-braviz" ,4000),
    'da-angulo': ("X:\\","D:\\kmc400-braviz" ,4000),
    #'da-angulo': ("F:\\kmc400","F:\kmc400_braviz" ,4000), # from external drive
    #'da-angulo': ("F:\\kmc400","D:\\kmc400-braviz" ,4000), # from external drive
    #'da-angulo': (r"N:\run\media\imagine\backups\kmc400","D:\\kmc400-braviz" ,4000), # from external drive
    'ISIS-EML725001': ('G:/kmc400', 'G:/kmc400-braviz',8000),
    'Echer': ('H:/kmc400', 'H:/kmc400-braviz',8000),
    'colivri1-homeip-net' : ('/home/canguro/kmc400-braviz','/media/external2/canguro_win/kmc_400_braviz',50000),
    'imagine-PC' : ("Z:\\","E:\\kmc_400_braviz",50000)

}

