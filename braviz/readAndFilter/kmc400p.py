from __future__ import division

import base64
import os
import re
import platform  # for the autoReader
import cPickle
import hashlib
import types
import pickle
import logging

import nibabel as nib
import numpy as np
from numpy.linalg import inv
import vtk

from braviz.readAndFilter import nibNii2vtk, applyTransform, readFlirtMatrix, transformPolyData, transformGeneralData, \
    readFreeSurferTransform, cache_function, numpy2vtkMatrix, extract_poly_data_subset, numpy2vtk_img, nifti_rgb2vtk, \
    CacheContainer

from braviz.readAndFilter.surfer_input import surface2vtkPolyData, read_annot, read_morph_data, addScalars, get_free_surfer_lut, \
    surfLUT2VTK
from braviz.readAndFilter.read_tensor import cached_readTensorImage
from braviz.readAndFilter.readDartelTransform import dartel2GridTransform_cached
from braviz.readAndFilter.read_csv import read_free_surfer_csv_file
import braviz.readAndFilter.color_fibers
from braviz.readAndFilter import bundles_db
from hierarchical_fibers import read_logical_fibers

class kmc400Reader(object):
    """
A read and filter class designed to work with the file structure and data from the KMC pilot project which contains 40 subjects.
Data is organized into folders, and path and names for the different files can be derived from data type and id.
The path containing this structure must be set."""
    __cache_container = CacheContainer()

    def __init__(self, static_root,dynamic_route, max_cache=2000):
        "The path pointing to the __root of the file structure must be set here"
        self.__static_root = os.path.normcase(static_root)
        #Remove trailing slashes
        self.__static_root = self.__static_root.rstrip('/\\')
        self.__dynaimc_data_root = dynamic_route.rstrip("/\\")
        if self.__static_root[-1]==":":
            self.__static_root+="\\"
        if self.__dynaimc_data_root[-1]==":":
            self.__dynaimc_data_root+="\\"

        self.__functional_paradigms={'ATENCION', 'COORDINACION', 'MEMORIA', 'MIEDO', 'PRENSION'}
        self.__cache_container.max_cache = max_cache
        self.__fmri_LUT = None

    @cache_function(__cache_container)
    def get(self,data, subj_id=None, **kw):
        """All vtkStructures can use an additional 'space' argument to specify the space of the output coordinates.
        Available spaces for all data are: world, talairach and dartel. Some data may support additional values
        data should be one of:
        IDS: Return the ids of all subjects in the study as a list

        MRI: By default returns a nibnii object, use format='VTK' to get a vtkImageData object.
             Additionally use space='native' to ignore the nifti transform.

        FA:  Same options as MRI, but space also accepts 'diffusion', also accepts 'lut'

        MD:  Same options as MRI, but space also accepts 'diffusion'

        DTI: Same options as MRI, but space also accepts 'diffusion'

        APARC: Same options as MRI, but also accepts 'lut' to get the corresponding look up table

        WMPARC: Same options as MRI, but also accepts 'lut' to get the corresponding look up table

        FMRI: requires name=<Paradigm>

        BOLD: requires name=<Paradigm>, only nifti format is available

        MODEL:Use name=<model> to get the vtkPolyData. Use index='T' to get a list of the available models for a subject.
              Use color=True to get the standard color associated to the structure
              Use volume=True to get the volume of the structure
              Use label=True to get the label corresponding to the structure

        SURF: Use name=<surface> and hemi=<r|h> to get the vtkPolyData of a free surfer surface reconstruction,
              use scalars to add scalars to the data
              surface must be orig pial white smoothwm inflated sphere

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

        TENSORS: Get an unstructured grid containing tensors at the points where they are available
                 and scalars representing the orientation of the main eigenvector
                 Use space=world to get output in world coordinates [experimental]

        """
        #All cache moved to decorator @cache_function
        return self.__get(data, subj_id, **kw)

    #============================end of public API==========================================
    def __get(self, data, subj=None, **kw):
        "Internal: decode instruction and dispatch"
        data = data.upper()
        if subj is not None:
            subj = str(subj)
        if data == 'MRI':
            return self.__getImg(data, subj, **kw)
        elif data == "MD":
            return self.__getImg(data, subj, **kw)
        elif data == "DTI":
            return self.__getImg(data, subj, **kw)
        elif data == 'FA':
            if kw.get('lut'):
                if not hasattr(self, 'fa_LUT'):
                    self.fa_LUT = self.__create_fa_lut()
                return self.fa_LUT
            return self.__getImg(data, subj, **kw)
        elif data == 'IDS':
            return self.__getIds()
        elif data == 'MODEL':
            return self.__load_free_surfer_model(subj, **kw)
        elif data == 'SURF':
            return self.__loadFreeSurferSurf(subj, **kw)
        elif data == 'SURF_SCALAR':
            return self.__loadFreeSurferScalar(subj, **kw)
        elif data == 'FIBERS':
            return self.__readFibers(subj, **kw)
        elif data == 'TENSORS':
            return self.__readTensors(subj, **kw)
        elif data in {"APARC","WMPARC"}:
            if kw.get('lut'):
                if not hasattr(self, 'free_surfer_aparc_LUT'):
                    self.free_surfer_aparc_LUT = self.__create_surfer_lut()
                return self.free_surfer_aparc_LUT
            return self.__getImg(data, subj, **kw)
        elif data == "FMRI":
            if kw.get('lut'):
                if self.__fmri_LUT is None:
                    self.__fmri_LUT = self.__create_fmri_lut()
                return self.__fmri_LUT
            if kw.get("index"):
                return self.__functional_paradigms
            return self.__read_func(subj, **kw)
        elif data == 'BOLD':
            return self.__read_bold(subj, kw['name'])
        else:
            log = logging.getLogger(__name__)
            log.error("Data type not available")
            raise (Exception("Data type not available"))

    def __getImg(self, data, subj, **kw):
        "Auxiliary function to read nifti images"
        #path=self.__root+'/'+str(subj)+'/MRI'
        if data == 'MRI':
            path = os.path.join(self.__static_root, "nii",str(subj))
            filename = 'MPRAGEmodifiedSENSE.nii.gz'
        elif data == 'FA':
            path = os.path.join(self.__static_root, 'tractography',str(subj))
            if kw.get('space',"").startswith('diff'):
                filename = 'fa.nii.gz'
            else:
                filename = 'fa_mri.nii.gz'
        elif data == "MD":
            path = os.path.join(self.__static_root, 'tractography',str(subj))
            if kw.get('space',"").startswith('diff'):
                filename = 'md.nii.gz'
            else:
                filename = 'md_mri.nii.gz'
        elif data == "DTI":
            path = os.path.join(self.__static_root, 'tractography',str(subj))
            if kw.get('space','').startswith('diff'):
                filename = 'rgb_dti_masked.nii.gz'
            else:
                filename = 'rgb_dti_mri_masked.nii.gz'
        elif data == 'APARC':
            path = os.path.join(self.__static_root, "slicer_models",str(subj))
            if kw.get("wm"):
                filename = 'wmparc.nii.gz'
                print "Warning... deprecated, use WMPARC instead"
            else:
                filename = 'aparc+aseg.nii.gz'
        elif data == "WMPARC":
            path = os.path.join(self.__static_root, "slicer_models",str(subj))
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
                img_data=img.get_data()
                img_data *= 1e5
                vtkImg = numpy2vtk_img(img_data)
            elif data == "DTI":
                vtkImg = nifti_rgb2vtk(img)
            else:
                vtkImg = nibNii2vtk(img)
            if kw.get('space', '').lower() == 'native':
                return vtkImg

            interpolate = True
            if data in {'APARC': 'WMPARC'}:
                interpolate = False
                #print "turning off interpolate"

            img2 = applyTransform(vtkImg, transform=inv(img.get_affine()), interpolate=interpolate)
            space = kw.get('space', 'world')
            if space == "diff" and (data in {"FA","MD","DTI"}):
                return img2
            return self.__move_img_from_world(subj, img2, interpolate, space=space)
        space = kw.get('space', 'native')
        if space == "diff" and (data in {"FA","MD","DTI"}):
            return img
        elif space == "world":
            return img
        elif space == "diff":
            #read transform:
            path = os.path.join(self.getDataRoot(), "tractography",str(subj))
            #matrix = readFlirtMatrix('surf2diff.mat', 'FA.nii.gz', 'orig.nii.gz', path)
            matrix = readFlirtMatrix('diff2surf.mat', 'fa.nii.gz', 'orig.nii.gz', path)
            affine = img.get_affine()
            aff2 = matrix.dot(affine)
            img2=nib.Nifti1Image(img.get_data(),aff2)
            return img2
        log = logging.getLogger(__file__)
        log.warning("Returned nifti image is in native space")
        return img


    def __move_img_from_world(self, subj, img2, interpolate=False, space='world'):
        "moves an image from the world coordinate space to talairach or dartel spaces"
        space = space.lower()
        if space == 'world':
            return img2
        elif space in ('template', 'dartel'):
            dartel_warp = self.__get_spm_grid_transform(subj,"dartel","back")
            img3 = applyTransform(img2, dartel_warp, origin2=(90, -126, -72), dimension2=(121, 145, 121),
                                  spacing2=(-1.5, 1.5, 1.5), interpolate=interpolate)
            #origin, dimension and spacing come from template 
            return img3
        elif space[:2].lower() == 'ta':
            talairach_file = os.path.join(self.__static_root, "freeSurfer_Tracula", subj, "mri","transforms",'talairach.xfm')
            transform = readFreeSurferTransform(talairach_file)
            img3 = applyTransform(img2, inv(transform), (-100, -120, -110), (190, 230, 230), (1, 1, 1),
                                  interpolate=interpolate)
            return img3
        elif space[:4] in ('func', 'fmri'):
            #functional space
            paradigm = space[5:]
            #print paradigm
            paradigm =self.__get_paradigm_name(paradigm)
            transform = self.__read_func_transform(subj, paradigm, True)
            img3 = applyTransform(img2, transform, origin2=(78, -112, -50), dimension2=(79, 95, 68),
                                  spacing2=(-2, 2, 2),
                                  interpolate=interpolate)
            return img3
        elif space == "diff":
            path = os.path.join(self.getDataRoot(), "tractography", str(subj))
            # notice we are reading the inverse transform diff -> world
            trans = readFlirtMatrix('diff2surf.mat', 'FA.nii.gz', 'orig.nii.gz', path)
            img3 = applyTransform(img2, trans, interpolate=interpolate)
            return img3
        else:
            log = logging.getLogger(__name__)
            log.error('Unknown space %s' % space)
            raise Exception('Unknown space %s' % space)

    def __getIds(self):
        "Auxiliary function to get the available ids"
        contents = os.listdir(os.path.join(self.__static_root,"freeSurfer_Tracula"))
        numbers = re.compile('[0-9]+$')
        ids = [c for c in contents if numbers.match(c) is not None]
        ids.sort(key=int)
        return ids

    __spharm_models = {'Left-Amygdala': 'l_amygdala',
                       'Left-Caudate': 'l_caudate',
                       'Left-Hippocampus': 'l_hippocampus',
                       'Right-Amygdala': 'r_amygdala',
                       'Right-Caudate': 'r_caudate',
                       'Right-Hippocampus': 'r_hippocampus'}

    def __get_spm_grid_transform(self,subject,paradigm,direction,assume_bad_matrix=False):
        """
        Get the spm non linear registration transform grid associated to the paradigm
        Use paradigm=dartel to get the transform associated to the dartel normalization
        """
        assert direction in {"forw","back"}
        if paradigm=="dartel":
            y_file = os.path.join(self.getDataRoot(),"spm",subject,"T1", "y_dartel_%s.nii" % direction)
            cache_name=os.path.join(self.__dynaimc_data_root,".braviz_cache",
                                    "y_%s_%s_%s.vtk"%(paradigm,subject,direction))
        else:
            y_file = os.path.join(self.getDataRoot(),"spm", subject,paradigm, "y_seg_%s.nii.gz" % direction)
            cache_name=os.path.join(self.__dynaimc_data_root,".braviz_cache",
                                    "y_%s_%s_%s.vtk"%(paradigm,subject,direction))
        return dartel2GridTransform_cached(y_file,assume_bad_matrix,cache_file_name=cache_name)


    def __load_free_surfer_model(self, subject, **kw):
        """Auxiliary function to read freesurfer models stored as vtk files or the freeSurfer colortable"""
        #path=self.__root+'/'+str(subject)+'/SlicerImages/segmentation/3DModels'
        #path=self.__root+'/'+str(subject)+'/Models2'
        if subject is not None:
            path = os.path.join(self.__static_root, 'slicer_models',subject)
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
            for k, val in self.__spharm_models.iteritems():
                if os.path.isfile(os.path.join(spharm_path, "%sSPHARM.vtk" % val)):
                    models.append(k + '-SPHARM')
            return models
        name = kw.get('name')
        if name is not None:
            if kw.get('color'):
                if not hasattr(self, 'free_surfer_LUT'):
                    self.__parse_fs_color_file()
                colors = self.free_surfer_LUT
                if name.endswith('-SPHARM'):
                    return colors[name[:-7]]
                else:
                    return colors[name]
            elif kw.get('volume'):
                if name.endswith('-SPHARM'):
                    log.warning("Warning, spharm structure treated as non-spharm equivalent")
                    name = name[:-7]
                return self.__get_volume(subject, name)
            elif kw.get('label'):
                if name.endswith('-SPHARM'):
                    log.warning("Warning, spharm structure treated as non-spharm equivalent")
                    name = name[:-7]
                if not hasattr(self,"free_surfer_labels"):
                    self.__parse_fs_color_file()
                return self.free_surfer_labels.get(name)
            else:
                available = self.__load_free_surfer_model(subject, index='T')
                if not name in available:
                    log.warning( 'Model %s not available' % name)
                    raise Exception('Model %s not available' % name)
                if name.endswith('-SPHARM'):
                    spharm_name = self.__spharm_models[name[:-7]]
                    filename = os.path.join(spharm_path, spharm_name + 'SPHARM.vtk')
                    reader = vtk.vtkPolyDataReader()
                    reader.SetFileName(filename)
                    reader.Update()
                    output = reader.GetOutput()
                    output = self.__movePointsToSpace(output, 'spharm', subject, True)
                else:
                    filename = os.path.join(path, name + '.vtk')
                    reader = vtk.vtkPolyDataReader()
                    reader.SetFileName(filename)
                    reader.Update()
                    output = reader.GetOutput()
                if kw.get('space', 'native').lower() == 'native':
                    return output
                else:
                    return self.__movePointsToSpace(output, kw.get('space', 'world'), subject)
        else:
            log.error('Either "index" or "name" is required.')
            raise (Exception('Either "index" or "name" is required.'))

    def __get_volume(self, subject, model_name):
        data_root = self.getDataRoot()
        data_dir = os.path.join(data_root, 'freeSurfer_Tracula',subject, 'stats')
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

    def __parse_fs_color_file(self):
        "Creates an inernal representation of the freesurfer color LUT"
        cached = self.load_from_cache('free_surfer_color_lut_internal')
        cached2 = self.load_from_cache('free_surfer_labels_dict_internal')
        if (cached is not None) and (cached2 is not None):
            self.free_surfer_LUT = cached
            self.free_surfer_labels = cached2
            return
        color_file_name = os.path.join(self.__static_root,"freeSurfer_Tracula", 'FreeSurferColorLUT.txt')

        with open(color_file_name) as color_file:
            color_lines = color_file.readlines()
            color_file.close()
            color_lists = [l.split() for l in color_lines if l[0] not in ('#', '\n', ' ') ]
            color_tuples = ((l[1], tuple([float(c) / 256 for c in l[2:]])) for l in color_lists)
            color_dict = dict(color_tuples)
            self.save_into_cache('free_surfer_color_lut_internal', color_dict)
            labels_tuples = ((l[1],l[0]) for l in color_lists )
            labels_dict=dict(labels_tuples)
            self.save_into_cache('free_surfer_labels_dict_internal',labels_dict)

        self.free_surfer_LUT = color_dict
        self.free_surfer_labels = labels_dict

    def _cached_surface_read(self,subj,name):
        "cached function to read a freesurfer structure file"
        #check cache
        key = "surf_%s_%s"%(name,subj)
        poly = self.load_from_cache(key)
        #print 'reading from surfer file'
        if poly is None:
            path = os.path.join(self.__static_root, "freeSurfer_Tracula",str(subj), 'surf')
            filename = os.path.join(path,name)
            poly=surface2vtkPolyData(filename)
            self.save_into_cache(key,poly)
        return poly

    def __loadFreeSurferSurf(self, subj, **kw):
        """Auxiliary function to read the corresponding surface file for hemi and name.
        Scalars can be added to the output surface"""
        if 'name' in  kw and 'hemi' in kw:
            #Check required arguments
            name = kw['hemi'] + 'h.' + kw['name']
        else:
            log = logging.getLogger(__name__)
            log.error('Name=<surface> and hemi=<l|r> are required.')
            raise Exception('Name=<surface> and hemi=<l|r> are required.')
        if not 'scalars' in kw:

            output = self._cached_surface_read(subj,name)
            return self.__movePointsToSpace(output, kw.get('space', 'world'), subj)
        else:
            scalars = self.get('SURF_SCALAR', subj, hemi=name[0], scalars=kw['scalars'])
            #Take advantage of cache
            kw.pop('scalars')
            orig = self.get('SURF', subj, **kw)
            addScalars(orig, scalars)
            return orig

    def __loadFreeSurferScalar(self, subj, **kw):
        "Auxiliary function to read free surfer scalars"
        morph = {'area', 'curv', 'avg_curv', 'thickness', 'volume', 'sulc'}
        morph_path = os.path.join(self.__static_root, "freeSurfer_Tracula",str(subj), 'surf')
        labels_path = os.path.join(self.__static_root, "freeSurfer_Tracula",str(subj), 'label')
        log = logging.getLogger(__name__)
        try:
            hemisphere = kw['hemi']
            hs = hemisphere + 'h'
        except KeyError:
            log.error("hemi is required")
            raise (Exception("hemi is required"))
        if kw.get('index'):
            contents = os.listdir(morph_path)
            contents.extend(os.listdir(labels_path))
            pattern = re.compile(hs + r'.*\.annot$')
            annots = [m[3:-6] for m in contents if pattern.match(m) is not None]
            morfs = [m for m in morph if hs + '.' + m in contents]
            return morfs + annots
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

    def __cached_color_fibers(self, subj, color=None,scalars=None):
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
                if color.startswith('orient'):
                    #This one should always exist!!!!!
                    file_name = os.path.join(self.getDataRoot(), "tractography",subj, 'CaminoTracts.vtk')
                    if not os.path.isfile(file_name):
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
            fibers = self.__cached_color_fibers(subj, 'orient')
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

    def __cached_filter_fibers(self, subj, waypoint):
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
                ids = braviz.readAndFilter.filterPolylinesWithModel(fibers, model, do_remove=False)
            else:
                ids = set()
        else:
            try:
                fibers = self.get('fibers', subj, space='world',color=None,scalars=img_name)
            except Exception:
                log.error("%s image not found"%img_name)
                return set()
            if not hasattr(self,"free_surfer_labels"):
                self.__parse_fs_color_file()
            lbl = self.free_surfer_labels.get(waypoint)
            if lbl is None:
                raise Exception("Unknown structure")
            ids = braviz.readAndFilter.filter_polylines_by_scalar(fibers,int(lbl))

        self.save_into_cache(cache_key,ids)
        return ids

    def filter_fibers(self,subj,struct):
        subj = str(subj)
        return self.__cached_filter_fibers(subj,struct)

    def __readFibers_from_db(self,subj,db_id,**kw):
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
            poly = self.get("Fibers", subj, waypoint=checkpoints, operation=operation,**kw)
            return poly
        elif bundle_type == 10:
            tree_dict = pickle.loads(data)
            poly = read_logical_fibers(subj,tree_dict,self,**kw)
            return poly
        else:
            log.error("Unknown data type")
            raise Exception("Unknown fibers")

    def __readFibers(self, subj, **kw):
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
                lut = braviz.readAndFilter.color_fibers.get_md_lut()
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
            poly = self.__readFibers_from_db(subj,db_id,**kw)
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
            target_space = kw.get('space', 'world').lower()
            if target_space == result_space:
                return fibers
            if result_space != 'world':
                fibers = self.transformPointsToSpace(fibers, result_space, subj, inverse=True)
            if target_space != 'world':
                transformed_streams = self.__movePointsToSpace(fibers, kw['space'], subj, inverse=False)
                return transformed_streams
            return fibers
        if 'waypoint' not in kw:
            path = os.path.join(self.getDataRoot(),'tractography', str(subj))
            streams = self.__cached_color_fibers(subj, kw.get('color'),kw.get("scalars"))
            if kw.get('space', 'world').lower() in {'diff', 'native'}:
                return streams
            #move to world
            matrix = readFlirtMatrix('diff2surf.mat', 'fa.nii.gz', 'orig.nii.gz', path)
            streams_mri = transformPolyData(streams, matrix)
            if kw.get('space', 'world').lower() != 'world':
                transformed_streams = self.__movePointsToSpace(streams_mri, kw['space'], subj)
                return transformed_streams
            return streams_mri
        else:
            #dealing with waypoints

            if kw.get('space', 'world').lower() == 'world':
                #Do filtering in world coordinates
                models = kw.pop('waypoint')
                if isinstance(models, str) or isinstance(models, unicode):
                    models = (models,)
                if (kw.get('operation', 'and') == 'and') and len(models) == 0:
                    #return all fibers
                    fibers = self.get('fibers', subj, space='world', color=kw.get('color'),scalars=kw.get("scalars"))
                    return fibers

                valid_ids = None
                for nm, model_name in enumerate(models):
                    new_ids = self.__cached_filter_fibers(subj, model_name)
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
                target_space = kw['space']
                kw['space'] = 'world'
                filtered_fibers = self.get('fibers', subj, **kw)
                transformed_streams = self.__movePointsToSpace(filtered_fibers, target_space, subj)
                return transformed_streams

    def __readTensors(self, subj, **kw):
        "Internal function to read a tensor file"
        raise NotImplementedError
        path = os.path.join(self.__root, str(subj), 'camino')
        tensor_file = os.path.join(path, 'camino_dt.nii.gz')
        if kw.get('space') == 'world':
            tensor_file = os.path.join(path, 'camino2_dt.nii.gz')
        fa_file = os.path.join(path, 'FA_masked.nii.gz')
        #tensor_data=readTensorImage(tensor_file, fa_file)
        tensor_data = cached_readTensorImage(tensor_file, fa_file)
        #tensor_data=readTensorImage(tensor_file)
        if kw.get('space') == 'world':
            matrix = readFlirtMatrix('diff2surf.mat', 'FA.nii.gz', 'orig.nii.gz', path)
            tensors_mri = transformGeneralData(tensor_data, matrix)
            return tensors_mri
        return tensor_data

    def __movePointsToSpace(self, point_set, space, subj, inverse=False):
        """Transforms a set of points in 'world' space to the talairach or template spaces
        If inverse is True, the points will be moved from 'space' to world"""
        if space.lower()[:2] == 'wo':
            return point_set
        elif space.lower()[:2] == 'ta':
            talairach_file = os.path.join(self.__static_root, "freeSurfer_Tracula",str(subj), 'mri',"transforms",
                                          'talairach.xfm')
            transform = readFreeSurferTransform(talairach_file)
            if inverse:
                transform = inv(transform)
            return transformPolyData(point_set, transform)
        elif space.lower() in ('template', 'dartel'):
            if inverse:
                dartel_warp = self.__get_spm_grid_transform(subj,"dartel","back")
            else:
                dartel_warp = self.__get_spm_grid_transform(subj,"dartel","forw")
            return transformPolyData(point_set, dartel_warp)
        elif space[:4] in ('func', 'fmri'):
            #functional space
            paradigm = space[5:]
            trans = self.__read_func_transform(subj, paradigm, inverse)
            return transformPolyData(point_set, trans)
        elif space.lower() == 'spharm':
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

    def __create_surfer_lut(self):
        "returns a vtkLookUpTable based on the freeSurferColorLUT file"
        #Based on subject 119
        color_dict = self.load_from_cache('aparc_color_tuples_dictionary')
        if color_dict is not None and len(color_dict)<180:
            color_dict = None
        #color_dict = None
        if color_dict is None:
            ref = self.get("ids")[0]
            aparc_img = self.get('APARC', ref)
            aparc_data = aparc_img.get_data()
            aparc_values = set(np.unique(aparc_data.flat))
            wmparc_img = self.get("WMPARC",ref)
            wmparc_data = wmparc_img.get_data()
            wmparc_values = np.unique(wmparc_data.flat)
            aparc_values.update(wmparc_values)
            color_file_name = os.path.join(self.getDataRoot(),"freeSurfer_Tracula", 'FreeSurferColorLUT.txt')
            try:
                color_file = open(color_file_name)
            except IOError as e:
                log = logging.getLogger(__name__)
                log.error(e)
                raise
            color_lines = color_file.readlines()
            color_file.close()
            color_lists = (l.split() for l in color_lines if l[0] not in ['#', '\n', ' '] )
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

    def __create_fa_lut(self):
        fa_lut = vtk.vtkLookupTable()
        fa_lut.SetRampToLinear()
        fa_lut.SetTableRange(0.0, 1.0)
        fa_lut.SetHueRange(0.0, 0.0)
        fa_lut.SetSaturationRange(1.0, 1.0)
        fa_lut.SetValueRange(0.0, 1.0)
        fa_lut.Build()
        return fa_lut

    def __create_fmri_lut(self):
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

    def __get_paradigm_name(self,paradigm_name):
        if paradigm_name.endswith("SENSE"):
            return paradigm_name
        paradigm_name = paradigm_name.upper()
        assert paradigm_name in self.FUNCTIONAL_PARADIGMS

        if paradigm_name=="MIEDO":
            paradigm_name="MIEDOSofTone"
        paradigm_name +="SENSE"
        return paradigm_name

    def __read_func_transform(self, subject, paradigm_name, inverse=False):
        "reads the transform from world to functional space"
        paradigm_name = self.__get_paradigm_name(paradigm_name)
        path = os.path.join(self.getDataRoot(), 'spm',subject )
        if inverse is False:
            T1_func = os.path.join(path, paradigm_name, 'T1.nii')
            T1_world = os.path.join(path, 'T1', 'T1.nii')
            dartel_trans = self.__get_spm_grid_transform(subject,paradigm_name,"forw", True)
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
            dartel_trans = self.__get_spm_grid_transform(subject,paradigm_name,"back", True)
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

    def __read_func(self, subject, **kw):
        "Internal function to read functional images, deals with the SPM transforms"
        log = logging.getLogger(__name__)
        try:
            name = kw['name']
        except KeyError:
            log.error('Paradigm name is required')
            raise Exception('Paradigm name is required')
        space = kw.get('space', 'world')
        name = name.upper()
        space = space.lower()
        if name not in self.FUNCTIONAL_PARADIGMS:
            log.warning(" functional paradigm %s not available" % name)
            return None
        name = self.__get_paradigm_name(name)
        path = os.path.join(self.getDataRoot(), "spm",subject,name,"FirstLevel")
        contrast = kw.get("contrast",1)
        contrast_n = "%.4d"%contrast
        z_map = os.path.join(path, 'spmT_%s.hdr')%contrast_n
        log.info("Loading map %s"%z_map)
        nii_z_map = nib.load(z_map)
        if kw.get('format', 'nifti').lower() == 'nifti':
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
        fmri_trans = self.__read_func_transform(subject, name)
        log.info("attempting to move to world")
        world_z_map = applyTransform(vtk_z_map, fmri_trans, origin2, dimension2, spacing2)

        return self.__move_img_from_world(subject, world_z_map, True, kw.get('space', 'world'))

    def __read_bold(self, subj, paradigm):
        paradigm = self.__get_paradigm_name(paradigm)
        route = os.path.join(self.getDataRoot(), 'spm',subj, paradigm, 'smoothed.nii.gz')
        img_4d = nib.load(route)
        return img_4d


    def getDataRoot(self):
        """Returns the data_root of this reader"""
        return self.__static_root

    def getDynDataRoot(self):
        """Returns the dynamic data_root of this reader"""
        return self.__dynaimc_data_root

    def transformPointsToSpace(self, point_set, space, subj, inverse=False):
        """Access to the internal coordinate transform function. Moves from world to space. 
        If inverse is true moves from space to world"""
        subj = str(subj)
        return self.__movePointsToSpace(point_set, space, subj, inverse)

    def __process_key(self, key):
        data_root_length = len(self.getDataRoot())
        key = "%s" % key
        if len(key) + data_root_length > 250:
            key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
        else:
            ilegal = ['_','<', '>', ':', '"', '/', "\\", '|', '?', '*']
            for i,il in enumerate(ilegal):
                key = key.replace(il, '%d_'%i)
        return key


    def save_into_cache(self, key, data):
        """
        Saves some data into a cache, can deal with vtkData and python objects which can be pickled

        key should be printable by %s, and it can be used to later retrive the data using load_from_cache
        you should not use the same key for python objects and vtk objects
        returnt true if success, and false if failure
        WARNING: Long keys are hashed using sha1: Low risk of collisions, no checking is done
        """
        key = self.__process_key(key)
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
        key = self.__process_key(key)
        cache_dir = os.path.join(self.__dynaimc_data_root, '.braviz_cache')
        cache_file = os.path.join(cache_dir, "%s.pickle" % key)
        log = logging.getLogger(__name__)
        try:
            with open(cache_file, 'rb') as cache_descriptor:
                try:
                    ans = cPickle.load(cache_descriptor)
                except cPickle.UnpicklingError:
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

    def clear_cache(self,last_word=False):
        if last_word is True:
            cache_dir = os.path.join(self.__dynaimc_data_root, '.braviz_cache')
            os.rmdir(cache_dir)
            os.mkdir(cache_dir)

known_nodes = {  #
    # Name          :  ( static data root, dyn data root , cache size in MB)
    'gambita.uniandes.edu.co': ('/media/DATAPART5/kmc400','/media/DATAPART5/kmc400_braviz', 4000),
    'dieg8': (r'C:\Users\Diego\Documents\kmc400',"C:\Users\Diego\Documents\kmc400_braviz", 4000),
    'ATHPC1304' : (r"Z:",r"E:\ProyectoCanguro\kmc400_braviz",14000),
}


def get_data_root():
    node_id = platform.node()
    node = known_nodes.get(node_id)
    if node is not None:
        return node[0]
    log = logging.getLogger(__name__)
    log.error("Unknown node")
    raise Exception("Unkown node")

def get_dyn_data_root():
    node_id = platform.node()
    node = known_nodes.get(node_id)
    if node is not None:
        return node[1]
    log = logging.getLogger(__name__)
    log.error("Unknown node")
    raise Exception("Unkown node")

#===============================================================================================
def autoReader(**kw_args):
    """Initialized a kmc40Reader based on the computer name"""
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
        return kmc400Reader(static_data_root,dyn_data_root, max_cache=max_cache, **kw_args)
    else:
        print "Unknown node %s, please enter route to data" % node_id
        path = raw_input('KMC_root: ')
        return kmc400Reader(path, **kw_args)
        # add other strategies to find the project __root
    
    
