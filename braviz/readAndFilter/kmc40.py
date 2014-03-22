from __future__ import division

import base64
import os
import re
import platform  # for the autoReader
import cPickle
import hashlib
import types

import nibabel as nib
import numpy as np
from numpy.linalg import inv
import vtk

from braviz.readAndFilter import nibNii2vtk, applyTransform, readFlirtMatrix, transformPolyData, transformGeneralData, \
    readFreeSurferTransform, cache_function, numpy2vtkMatrix, extract_poly_data_subset, numpy2vtk_img, nifti_rgb2vtk
from braviz.readAndFilter.surfer_input import surface2vtkPolyData, read_annot, read_morph_data, addScalars, getMorphLUT, \
    surfLUT2VTK
from braviz.readAndFilter.read_tensor import cached_readTensorImage
from braviz.readAndFilter.readDartelTransform import dartel2GridTransform_cached as dartel2GridTransform
from braviz.readAndFilter.read_csv import read_free_surfer_csv_file
import braviz.readAndFilter.color_fibers


class kmc40Reader:
    """
A read and filter class designed to work with the file structure and data from the KMC pilot project which contains 40 subjects.
Data is organized into folders, and path and names for the different files can be derived from data type and id.
The path containing this structure must be set."""

    def __init__(self, path, max_cache=500):
        "The path pointing to the __root of the file structure must be set here"
        global max_cache_size
        self.__root = os.path.normcase(path)
        #Remove trailing slashes
        self.__root = self.__root.rstrip('/\\')

        @cache_function(max_cache)
        def get(data, subj_id=None, **kw):
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
            
            FMRI: requires name=<Paradigm>

            BOLD: requires name=<Paradigm>, only nifti format is available
    
            MODEL:Use name=<model> to get the vtkPolyData. Use index='T' to get a list of the available models for a subject.
                  Use color=True to get the standard color associated to the structure
                  Use volume=True to get the volume of the structure
    
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
                    'Name' can be provided instead of waypoint to get custom tracts, to get a list of currently available
                    named tracts call index=True
            TENSORS: Get an unstructured grid containing tensors at the points where they are available
                     and scalars representing the orientation of the main eigenvector
                     Use space=world to get output in world coordinates [experimental]

            TABLE: Read variables from the csv file
            """
            #All cache moved to decorator @cache_function
            return self.__get(data, subj_id, **kw)

        self.get = get

    #============================end of public API==========================================
    def __get(self, data, subj=None, **kw):
        "Internal: decode instruction and dispatch"
        data = data.upper()
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
        elif data == 'APARC':
            if kw.get('lut'):
                if not hasattr(self, 'free_surfer_aparc_LUT'):
                    self.free_surfer_aparc_LUT = self.__create_surfer_lut()
                return self.free_surfer_aparc_LUT
            return self.__getImg(data, subj, **kw)
        elif data == "FMRI":
            if kw.get('lut'):
                if not hasattr(self, 'fmri_LUT'):
                    self.fmri_LUT = self.__create_fmri_lut()
                return self.fmri_LUT
            return self.__read_func(subj, **kw)
        elif data == 'BOLD':
            return self.__read_bold(subj, kw['name'])
        else:
            print "Data type not available"
            raise (Exception("Data type not available"))

    def __getImg(self, data, subj, **kw):
        "Auxiliary function to read nifti images"
        #path=self.__root+'/'+str(subj)+'/MRI'
        if data == 'MRI':
            path = os.path.join(self.__root, str(subj), 'MRI')
            filename = '%s-MRI-full.nii.gz' % str(subj)
        elif data == 'FA':
            path = os.path.join(self.__root, str(subj), 'camino')
            if kw.get('space').startswith('diff'):
                filename = 'FA_masked.nii.gz'
            else:
                filename = 'FA_mri_masked.nii.gz'
        elif data == "MD":
            path = os.path.join(self.__root, str(subj), 'camino')
            if kw.get('space').startswith('diff'):
                filename = 'MD_masked.nii.gz'
            else:
                filename = 'MD_mri_masked.nii.gz'
        elif data == "DTI":
            path = os.path.join(self.__root, str(subj), 'camino')
            if kw.get('space','').startswith('diff'):
                filename = 'rgb_dti_masked.nii.gz'
            else:
                filename = 'rgb_dti_mri_masked.nii.gz'
        elif data == 'APARC':
            path = os.path.join(self.__root, str(subj), 'Models')
            filename = 'aparc+aseg.nii.gz'
        else:
            raise Exception('Unknown image type %s' % data)
        wholeName = os.path.join(path, filename)
        try:
            img = nib.load(wholeName)
        except IOError as e:
            print e
            print "File %s not found" % wholeName
            raise (Exception('File not found'))

        if kw.get('format', '').upper() == 'VTK':
            if data == "MD":
                img_data=img.get_data()
                img_data *= 1e12
                vtkImg = numpy2vtk_img(img_data)
            elif data == "DTI":
                vtkImg = nifti_rgb2vtk(img)
            else:
                vtkImg = nibNii2vtk(img)
            if kw.get('space', '').lower() == 'native':
                return vtkImg

            interpolate = True
            if data == 'APARC':
                interpolate = False
                #print "turning off interpolate"

            img2 = applyTransform(vtkImg, transform=inv(img.get_affine()), interpolate=interpolate)
            return self.__move_img_from_world(subj, img2, interpolate, kw.get('space', 'world'))
        return img

    def __move_img_from_world(self, subj, img2, interpolate=False, space='world'):
        "moves an image from the world coordinate space to talairach or dartel spaces"
        space = space.lower()
        if space == 'world':
            return img2
        elif space in ('template', 'dartel'):
            dartel_yfile = os.path.join(self.__root, 'Dartel', "y_%s-back.nii.gz" % subj)
            dartel_warp = dartel2GridTransform(dartel_yfile)
            img3 = applyTransform(img2, dartel_warp, origin2=(90, -126, -72), dimension2=(121, 145, 121),
                                  spacing2=(-1.5, 1.5, 1.5), interpolate=interpolate)
            #origin, dimension and spacing come from template 
            return img3
        elif space[:2].lower() == 'ta':
            talairach_file = os.path.join(self.__root, str(subj), 'Surf', 'talairach.xfm')
            transform = readFreeSurferTransform(talairach_file)
            img3 = applyTransform(img2, inv(transform), (-100, -120, -110), (190, 230, 230), (1, 1, 1),
                                  interpolate=interpolate)
            return img3
        elif space[:4] in ('func', 'fmri'):
            #functional space
            paradigm = space[5:]
            #print paradigm
            transform = self.__read_func_transform(subj, paradigm, True)
            img3 = applyTransform(img2, transform, origin2=(78, -112, -50), dimension2=(79, 95, 68),
                                  spacing2=(-2, 2, 2),
                                  interpolate=interpolate)
            return img3
        else:
            raise Exception('Unknown space %s' % space)

    def __getIds(self):
        "Auxiliary function to get the available ids"
        contents = os.listdir(self.__root)
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

    def __load_free_surfer_model(self, subject, **kw):
        """Auxiliary function to read freesurfer models stored as vtk files or the freeSurfer colortable"""
        #path=self.__root+'/'+str(subject)+'/SlicerImages/segmentation/3DModels'
        #path=self.__root+'/'+str(subject)+'/Models2'
        path = os.path.join(self.__root, str(subject), 'Models3')
        spharm_path = os.path.join(self.__root, str(subject), 'spharm')
        if kw.get('index', False):
            contents = os.listdir(path)
            pattern = re.compile(r'.*\.vtk$')
            models = [m[0:-4] for m in contents if pattern.match(m) is not None]
            #look for spharm_models
            for k, val in self.__spharm_models.iteritems():
                if os.path.isfile(os.path.join(spharm_path, "%sSPHARM.vtk" % val)):
                    models.append(k + '-SPHARM')
            return models
        if kw.has_key('name'):
            name = kw['name']
            if kw.get('color'):
                if hasattr(self, 'free_surfer_LUT'):
                    colors = self.free_surfer_LUT
                else:
                    colors = self.__createColorDictionary()
                    self.free_surfer_LUT = colors
                if name.endswith('-SPHARM'):
                    return colors[name[:-7]]
                else:
                    return colors[name]
            elif kw.get('volume'):
                if name.endswith('-SPHARM'):
                    name = name[:-7]
                return self.__get_volume(subject, name)
            else:
                available = self.__load_free_surfer_model(subject, index='T')
                if not name in available:
                    print 'Model %s not available' % name
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
            print 'Either "index" or "name" is required.'
            raise (Exception('Either "index" or "name" is required.'))

    def __get_volume(self, subject, model_name):
        data_root = self.getDataRoot()
        data_dir = os.path.join(data_root, subject, 'Models', 'stats')
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

    def __createColorDictionary(self):
        "Creates an inernal representation of the freesurfer color LUT"
        cached = self.load_from_cache('free_surfer_color_lut_internal')
        if cached is not None:
            return cached
        color_file_name = os.path.join(self.__root, 'FreeSurferColorLUT.txt')

        with open(color_file_name) as color_file:
            color_lines = color_file.readlines()
            color_file.close()
            color_lists = (l.split() for l in color_lines if l[0] not in ['#', '\n', ' '] )
            color_tuples = ((l[1], tuple([float(c) / 256 for c in l[2:]])) for l in color_lists)
            color_dict = dict(color_tuples)
            self.save_into_cache('free_surfer_color_lut_internal', color_dict)
            return color_dict


    def __loadFreeSurferSurf(self, subj, **kw):
        """Auxiliary function to read the corresponding surface file for hemi and name.
        Scalars can be added to the output surface"""
        if kw.has_key('name') and kw.has_key('hemi'):
            #Check required arguments
            name = kw['hemi'] + 'h.' + kw['name']
        else:
            print 'Name=<surface> and hemi=<l|r> are required.'
            raise Exception('Name=<surface> and hemi=<l|r> are required.')
        if not kw.has_key('scalars'):
            path = os.path.join(self.__root, str(subj), 'Surf')
            filename = path + '/' + name
            output = surface2vtkPolyData(filename)
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
        path = os.path.join(self.__root, str(subj), 'Surf')
        try:
            hemisphere = kw['hemi']
            hs = hemisphere + 'h'
        except KeyError:
            print "hemi is required"
            raise (Exception("hemi is required"))
        if kw.get('index'):
            contents = os.listdir(path)
            pattern = re.compile(hs + r'.*\.annot$')
            annots = [m[3:-6] for m in contents if pattern.match(m) is not None]
            morfs = [m for m in morph if hs + '.' + m in contents]
            return morfs + annots
        try:
            scalar_name = kw['scalars']
        except KeyError:
            raise (Exception('scalars is required'))
        path = os.path.join(self.__root, str(subj), 'Surf')
        if scalar_name in morph:
            if kw.get('lut'):
                return getMorphLUT(scalar_name)
            scalar_filename = path + '/' + hemisphere + 'h.' + scalar_name
            scalar_array = read_morph_data(scalar_filename)
            return scalar_array
        else:
            #It should be an annotation
            annot_filename = path + '/' + hemisphere + 'h.' + scalar_name + '.annot'
            labels, ctab, names = read_annot(annot_filename)
            if kw.get('lut'):
                return surfLUT2VTK(ctab, names)
            return labels

    def __cached_color_fibers(self, subj, color):
        """function that reads colored fibers from cache,
        if not available creates the structure and attempts to save the cache"""
        color = color.lower()
        cache_name = os.path.join(self.getDataRoot(), subj, 'camino', 'streams_%s.vtk' % color)
        if color == 'orient':
            #This one should always exist!!!!!
            cache_name = os.path.join(self.getDataRoot(), subj, 'camino', 'streams.vtk')
            if not os.path.isfile(cache_name):
                raise Exception("Fibers file not found")

        cached = os.path.isfile(cache_name)
        if cached:
            fib_reader = vtk.vtkPolyDataReader()
            fib_reader.SetFileName(cache_name)
            if fib_reader.IsFilePolyData() < 1:
                raise Exception("fibers polydata file not found")
            try:
                fib_reader.Update()
            except Exception:
                print "problems reading %s" % cache_name
                raise
            else:
                out = fib_reader.GetOutput()
                fib_reader.CloseVTKFile()
                return out
        else:
            fibers = self.__cached_color_fibers(subj, 'orient')
            if color == 'orient':
                return fibers
            elif color == 'y':
                color_fun = braviz.readAndFilter.color_fibers.color_by_z
                braviz.readAndFilter.color_fibers.color_fibers_pts(fibers, color_fun)
            elif color == 'fa':
                color_fun = braviz.readAndFilter.color_fibers.color_by_fa
                fa_img = self.get('fa', subj, format='vtk')
                fun_args = (fa_img,)
                braviz.readAndFilter.color_fibers.color_fibers_pts(fibers, color_fun, *fun_args)
            elif color == 'rand':
                color_fun = braviz.readAndFilter.color_fibers.random_line
                braviz.readAndFilter.color_fibers.color_fibers_lines(fibers, color_fun)
            elif color == 'curv':
                color_fun = braviz.readAndFilter.color_fibers.line_curvature
                braviz.readAndFilter.color_fibers.color_fibers_lines(fibers, color_fun)
            else:
                raise Exception('Unknown coloring scheme %s' % color)

            #Cache write
            fib_writer = vtk.vtkPolyDataWriter()
            fib_writer.SetFileName(cache_name)
            fib_writer.SetInputData(fibers)
            fib_writer.SetFileTypeToBinary()
            try:
                fib_writer.Update()
                if fib_writer.GetErrorCode() != 0:
                    print 'cache write failed'
            except Exception:
                print 'cache write failed'
            return fibers

    def __cached_filter_fibers(self, subj, waypoint):
        "Only one waypoint, returns a set"
        #print "filtering for model "+waypoint
        pickles_dir = os.path.join(self.getDataRoot(), 'pickles')
        pickle_name = 'fibers_%s_%s.pickle' % (subj, waypoint)
        try:
            with open(os.path.join(pickles_dir, pickle_name), 'rb') as cache_file:
                ids = cPickle.Unpickler(cache_file).load()
                cache_file.close()
                #print "read from cache"
                return ids
        except IOError:
            print "cache not found"
        fibers = self.get('fibers', subj, space='world')
        model = self.get('model', subj, name=waypoint, space='world')
        if model:
            ids = braviz.readAndFilter.filterPolylinesWithModel(fibers, model, do_remove=False)
        else:
            ids = set()

        try:
            with open(os.path.join(pickles_dir, pickle_name), 'wb') as cache_file:
                cPickle.Pickler(cache_file, 2).dump(ids)
                cache_file.close()
        except IOError:
            print "cache write failed: %s" % cache_file
        return ids

    def __readFibers(self, subj, **kw):
        """Auxiliary function for reading fibers, uses all the cache available.
        First reades the correct color file,
        afterwards the lists for the corresponding waypoints from which an intersection is calculated,
        the list is then used to remove unwanted polylines,
        and finally the fibers are translated to the wanted space
        """
        if kw.has_key('progress'):
            print "The progress argument is deprecated"
            kw['progress'].set(5)
        if kw.get('index', False):
            import braviz.readAndFilter.named_tracts

            named_tract_funcs = dir(braviz.readAndFilter.named_tracts)
            functions = filter(lambda x: isinstance(getattr(braviz.readAndFilter.named_tracts, x),
                                                    types.FunctionType), named_tract_funcs)
            return filter(lambda x: not x.startswith('_'), functions)

        if kw.has_key('name'):
            #named tracts, special case
            import braviz.readAndFilter.named_tracts

            try:
                named_tract_func = getattr(braviz.readAndFilter.named_tracts, kw['name'])
            except AttributeError:
                raise Exception("unknown tract name %s" % kw['name'])
            fibers, result_space = named_tract_func(self, subj, color=kw.get('color', 'orient'))
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
        if not kw.has_key('waypoint'):
            path = os.path.join(self.__root, str(subj), 'camino')
            streams = self.__cached_color_fibers(subj, kw.get('color', 'orient'))
            if kw.get('space', 'world').lower() in {'diff', 'native'}:
                return streams
            #move to world
            matrix = readFlirtMatrix('diff2surf.mat', 'FA.nii.gz', 'orig.nii.gz', path)
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
                    fibers = self.get('fibers', subj, space='world', color=kw.get('color', 'orient'))
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
                    if kw.has_key('progress'):
                        kw['progress'].set(nm / len(models) * 100)
                if valid_ids is None:
                    valid_ids = set()

                #Take advantage of buffer
                fibers = self.get('fibers', subj, space='world', color=kw.get('color', 'orient'))
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
            talairach_file = os.path.join(self.__root, str(subj), 'Surf', 'talairach.xfm')
            transform = readFreeSurferTransform(talairach_file)
            if inverse:
                transform = inv(transform)
            return transformPolyData(point_set, transform)
        elif space.lower() in ('template', 'dartel'):
            dartel_yfile = os.path.join(self.__root, 'Dartel', "y_%s-forw.nii.gz" % subj)
            if inverse:
                dartel_yfile = os.path.join(self.__root, 'Dartel', "y_%s-back.nii.gz" % subj)
            dartel_warp = dartel2GridTransform(dartel_yfile)
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
            print 'Unknown Space %s' % space
            raise Exception('Unknown Space %s' % space)

    def __create_surfer_lut(self):
        "returns a vtkLookUpTable based on the freeSurferColorLUT file"
        #Based on subject 143
        color_dict = self.load_from_cache('aparc_color_tuples_dictionary')
        if color_dict is None:
            aparc_img = self.get('APARC', '143')
            aparc_data = aparc_img.get_data()
            aparc_values = set()
            for v in aparc_data.flat:
                aparc_values.add(v)
            color_file_name = os.path.join(self.getDataRoot(), 'FreeSurferColorLUT.txt')
            try:
                color_file = open(color_file_name)
            except IOError as e:
                print e
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
        for i in color_dict:
            out_lut.SetAnnotation(i, color_dict[i][1])
        for i in color_dict:  # HACKY.... maybe there is a bug?
            idx = out_lut.GetAnnotatedValueIndex(i)
            out_lut.SetTableValue(idx, color_dict[i][0])
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

    def __read_func_transform(self, subject, paradigm, inverse=False):
        "reads the transform from world to functional space"
        name = paradigm.upper()
        path = os.path.join(self.getDataRoot(), subject, 'spm')
        if inverse is False:
            dartel_warp = os.path.join(path, name, 'y_seg_forw.nii.gz')
            T1_func = os.path.join(path, name, 'T1.nii.gz')
            T1_world = os.path.join(path, 'T1', 'T1.nii.gz')
            dartel_trans = dartel2GridTransform(dartel_warp, True)
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
            dartel_warp = os.path.join(path, name, 'y_seg_back.nii.gz')
            T1_func = os.path.join(path, name, 'T1.nii.gz')
            T1_world = os.path.join(path, 'T1', 'T1.nii.gz')
            dartel_trans = dartel2GridTransform(dartel_warp, True)
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
        try:
            name = kw['name']
        except KeyError:
            raise Exception('Paradigm name is required')
        space = kw.get('space', 'world')
        name = name.upper()
        space = space.lower()
        if name not in ('PRECISION', 'POWERGRIP'):
            print " functional paradigm %s not available" % name
            return None
        path = os.path.join(self.getDataRoot(), subject, 'spm')
        z_map = os.path.join(path, name, 'spmT_0001.hdr')
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
        world_z_map = applyTransform(vtk_z_map, fmri_trans, origin2, dimension2, spacing2)

        return self.__move_img_from_world(subject, world_z_map, True, kw.get('space', 'world'))

    def __read_bold(self, subj, paradigm):
        paradigm = paradigm.upper()
        route = os.path.join(self.getDataRoot(), subj, 'spm', paradigm, 'smoothed.nii.gz')
        img_4d = nib.load(route)
        return img_4d


    def getDataRoot(self):
        """Returns the data_root of this reader"""
        return self.__root

    def transformPointsToSpace(self, point_set, space, subj, inverse=False):
        """Access to the internal coordinate transform function. Moves from world to space. 
        If inverse is true moves from space to world"""
        return self.__movePointsToSpace(point_set, space, subj, inverse)

    def __process_key(self, key):
        data_root_length = len(self.getDataRoot())
        key = "%s" % key
        if len(key) + data_root_length > 250:
            key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
        else:
            ilegal = ['<', '>', ':', '"', '/', "\\", '|', '?', '*']
            for il in ilegal:
                key = key.replace('il', '_')
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
        cache_dir = os.path.join(self.getDataRoot(), '.braviz_cache')
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
                print "couldn't open file %s" % cache_file
                return False
            return True

    def load_from_cache(self, key):
        """
        Loads data stored into cache with the function save_into_cache

        Data can be a vtkobject or a python structure, if both were stored with the same key, python object will be returned
        returns None if object not found
        """
        key = self.__process_key(key)
        cache_dir = os.path.join(self.getDataRoot(), '.braviz_cache')
        cache_file = os.path.join(cache_dir, "%s.pickle" % key)
        try:
            with open(cache_file, 'rb') as cache_descriptor:
                try:
                    ans = cPickle.load(cache_descriptor)
                except cPickle.UnpicklingError:
                    print "File %s is corrupted " % cache_file
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


#===============================================================================================
def autoReader(**kw_args):
    """Initialized a kmc40Reader based on the computer name"""

    known_nodes = {  #
                     # Name          :  ( data root                   , cache size in MB)
                     #'IIND-EML753022': ('C:\\Users\\da.angulo39\\Documents\\Kanguro',1400), (No longer exists :( )
                     'gambita.uniandes.edu.co': ('/media/DATAPART5/KAB-db', 4000),
                     'Unidelosandes': ('K:\\JohanaForero\\KAB-db', 1200),
                     'dieg8': (r'C:\Users\Diego\Documents\kmc40-db\KAB-db', 4000),
                     'TiberioHernande': (r'E:\KAB-db', 1100),
                     'localhost.localdomain': ('/home/diego/braviz/subjects', 1000),
                     'ISIS-EML725001': (r'C:\KAB-db', 1200),
    }
    node_id = platform.node()

    if known_nodes.has_key(node_id):
        data_root = known_nodes[node_id][0]
        if kw_args.get('max_cache', 0) > 0:
            max_cache = kw_args.pop('max_cache')
            print "Max cache set to %.2f MB" % max_cache
        else:
            max_cache = known_nodes[node_id][1]
        return kmc40Reader(data_root, max_cache=max_cache, **kw_args)
    else:
        print "Unknown node %s, please enter route to data" % node_id
        path = raw_input('KMC_root: ')
        return kmc40Reader(path, **kw_args)
        # add other strategies to find the project __root
    
    
