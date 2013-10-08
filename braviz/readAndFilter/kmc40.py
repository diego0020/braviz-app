from __future__ import division

import nibabel as nib
import numpy as np
from numpy.linalg import inv

from braviz.readAndFilter import nibNii2vtk, applyTransform, readFlirtMatrix, transformPolyData, transformGeneralData, readFreeSurferTransform, cache_function,numpy2vtkMatrix
from braviz.readAndFilter.surfer_input import surface2vtkPolyData,read_annot,read_morph_data,addScalars,getMorphLUT,surfLUT2VTK
from braviz.readAndFilter.read_tensor import cached_readTensorImage
from braviz.readAndFilter.readDartelTransform import dartel2GridTransform_cached as dartel2GridTransform
import braviz.readAndFilter.color_fibers

import os
import re
import vtk
import platform #for the autoReader
import cPickle

class kmc40Reader:
    """
A read and filter class designed to work with the file structure and data from the KMC pilot project which contains 40 subjects.
Data is organized into folders, and path and names for the different files can be derived from data type and id.
The path containing this structure must be set."""
    def __init__(self,path,max_cache=500):
        "The path pointing to the __root of the file structure must be set here"
        global max_cache_size
        self.__root=os.path.normcase(path)
        #Remove trailing slashes
        self.__root=self.__root.rstrip('/\\')
        @cache_function(max_cache)    
        def get(data,subj_id=None,**kw):
            """All vtkStructures can use an additional 'space' argument to specify the space of the output coordinates.
            Available spaces for all data are: world, talairach and dartel. Some data may support additional values
            data should be one of:
            IDS: Return the ids of all subjects in the study as a list
    
            MRI: By default returns a nibnii object, use format='VTK' to get a vtkImageData object. 
                 Additionally use space='native' to ignore the nifti transform.
    
            FA:  Same options as MRI, but space also accepts 'diffusion'
            
            APARC: Same options as MRI, but also accepts 'lut' to get the corresponding look up table
            
            FMRI: requires name=<Paradigm>

            BOLD: requires name=<Paradigm>, only nifti format is available
    
            MODEL:Use name=<model> to get the vtkPolyData. Use index='T' to get a list of the available models for a subject.
                  Use color='t' to get the standard color associated to the structure 
    
            SURF: Use name=<surface> and hemi=<r|h> to get the vtkPolyData of a free surfer surface reconstruction, 
                  use scalars to add scalars to the data
                  surface must be orig pial white smoothwm inflated sphere
    
            SURF_SCALAR: Use scalar=<name> and hemi=<l|r> to get scalar data associated to a SURF.
                         Use index='T' to get a list of available scalars, 
                         Use lut='T' to get the associated lookUpTable for Annotations and a standard LUT for morphology
    
            FIBERS: The default space is world, use space='diff' to get fibers in diffusion space. 
                    Use waypoint=<model-name> to restrict to fibers passing through a given MODEL as indicated above
                    Can accept color=<orient|fa|curv|y|rand> to get different color scalars
    
            TENSORS: Get an unstructured grid containing tensors at the points where they are available
                     and scalars representing the orientation of the main eigenvector
                     Use space=world to get output in world coordinates [experimental]

            TABLE: Read variables from the csv file
            """
            #All cache moved to decorator @cache_function
            return self.__get(data,subj_id,**kw)
        self.get=get
    #============================end of public API==========================================
    def __get(self,data,subj=None,**kw):
        "Internal: decode instruction and dispatch"
        data=data.upper()
        if data=='MRI':
            return self.__getImg(data,subj,**kw)
        elif data=='FA':
            return self.__getImg(data,subj,**kw)
        elif data=='IDS':
            return self.__getIds()
        elif data=='MODEL':
            return self.__loadFreeSurferModel(subj, **kw)
        elif data=='SURF':
            return self.__loadFreeSurferSurf(subj,**kw)
        elif data=='SURF_SCALAR':
            return self.__loadFreeSurferScalar(subj,**kw)
        elif data=='FIBERS':
            return self.__readFibers(subj,**kw)
        elif data=='TENSORS':
            return self.__readTensors(subj,**kw)
        elif data=='APARC':
            if kw.has_key('lut'):
                if not hasattr(self,'free_surfer_aparc_LUT'):
                    self.free_surfer_aparc_LUT=self.__create_surfer_lut()
                return self.free_surfer_aparc_LUT
            return self.__getImg(data,subj,**kw)
        elif data=="FMRI":
            return self.__read_func(subj, **kw)
        elif data=='BOLD':
            return self.__read_bold(subj,kw['name'])
        else:
            print "Data type not available"
            raise(Exception("Data type not available"))
    def __getImg(self,data,subj,**kw):
            "Auxiliary function to read nifti images"
            #path=self.__root+'/'+str(subj)+'/MRI'
            if data=='MRI':
                path=os.path.join(self.__root,str(subj),'MRI')
                filename='%s-MRI-full.nii.gz'%str(subj)
            elif data=='FA':
                path=os.path.join(self.__root,str(subj),'camino')
                if kw.get('space')=='diff':
                    filename='FA_masked.nii.gz'
                else:
                    filename='FA_mri_masked.nii.gz'
            elif data=='APARC':
                path=os.path.join(self.__root,str(subj),'Models')
                filename='aparc+aseg.nii.gz'
            else:
                raise Exception('Unknown image type %s'%data)
            #wholeName=path+'/'+filename
            wholeName=os.path.join(path,filename)
            #print wholeName
            try:
                img=nib.load(wholeName)
            except IOError as e:
                print e
                print "File %s not found"%wholeName
                raise(Exception('File not found'))
            
            if kw.has_key('format') and kw.get('format').upper()=='VTK':
                vtkImg=nibNii2vtk(img)
                if  kw.has_key('space') and kw.get('space').lower()=='native':   
                    return vtkImg
                
                interpolate=True
                if data=='APARC':
                    interpolate=False
                    #print "turning off interpolate" 
                
                img2=applyTransform(vtkImg, inv(img.get_affine()),interpolate=interpolate)
                return self.__move_img_from_world(subj, img2, interpolate, kw.get('space','world'))
            return img
    def __move_img_from_world(self,subj,img2,interpolate=False,space='world'):     
        "moves an image from the world coordinate space to talairach or dartel spaces"
        space=space.lower()
        if space=='world':
            return img2
        elif space in ('template','dartel'):
            dartel_yfile=os.path.join(self.__root,'Dartel',"y_%s-back.nii.gz"%subj)
            dartel_warp=dartel2GridTransform(dartel_yfile)
            img3=applyTransform(img2, dartel_warp, origin2=(90,-126,-72), dimension2=(121,145,121), spacing2=(-1.5,1.5,1.5),interpolate=interpolate)
            #origin, dimension and spacing come from template 
            return img3
        elif space[:2].lower()=='ta':
            talairach_file=os.path.join(self.__root,str(subj),'Surf','talairach.xfm')
            transform=readFreeSurferTransform(talairach_file)
            img3=applyTransform(img2, inv(transform),(-100,-120,-110),(190,230,230),(1,1,1),interpolate=interpolate)
            return img3
        elif space[:4]in ('func','fmri'):
            #functional space
            paradigm=space[5:]
            #print paradigm
            transform = self.__read_func_transform(subj,paradigm,True)
            img3 = applyTransform(img2, transform, origin2=(78,-112,-50), dimension2=(79,95,68), spacing2=(-2,2,2),
                                  interpolate=interpolate)
            return img3
        else:
            raise Exception('Unknown space %s'%space)
        
    def __getIds(self):
        "Auxiliary function to get the available ids"
        contents=os.listdir(self.__root)
        numbers=re.compile('[0-9]+$')
        ids=[c for c in contents if numbers.match(c)!=None]
        ids.sort(key=int)
        return ids
    def __loadFreeSurferModel(self,subject,**kw):
        "Auxiliary function to read freesurfer models stored as vtk files or the freeSurfer colortable"
        #path=self.__root+'/'+str(subject)+'/SlicerImages/segmentation/3DModels'
        #path=self.__root+'/'+str(subject)+'/Models2'
        path=os.path.join(self.__root,str(subject),'Models')
        if kw.has_key('index'):
            contents=os.listdir(path)
            pattern=re.compile(r'.*\.vtk$')
            models=[m[0:-4] for m in contents if pattern.match(m)!=None]
            return models
        if kw.has_key('name'):
            name=kw['name']
            if kw.has_key('color'):
                if hasattr(self,'free_surfer_LUT'):
                    colors=self.free_surfer_LUT
                else:
                    colors=self.__createColorDictionary()
                    self.free_surfer_LUT=colors
                return colors[name]
            else:
                available=self.__loadFreeSurferModel(subject,index='T')                
                if not name in available:
                    print 'Model %s not available'%name
                    return None
                filename=path+'/'+name+'.vtk'
                reader=vtk.vtkPolyDataReader()
                reader.SetFileName(filename)
                reader.Update()
                output=reader.GetOutput()
                if not kw.has_key('space') or kw['space'].lower()=='native':
                    return output
                else:
                    return self.__movePointsToSpace(output, kw['space'], subject)
        else:
            print 'Either "index" or "name" is required.'
            raise(Exception('Either "index" or "name" is required.'))
        return None
    def __createColorDictionary(self):
        "Creates an inernal representation of the freesurfer color LUT"
        color_file_name=os.path.join(self.__root,'FreeSurferColorLUT.txt')
        try:
            color_file=open(color_file_name)
        except IOError as e:
            print e
            raise
        color_lines=color_file.readlines()
        color_file.close()
        color_lists=[l.split() for l in color_lines if l[0] not in ['#','\n',' '] ]
        color_tuples=[(l[1],tuple([float(c)/256 for c in l[2:]])) for l in color_lists]
        color_dict=dict(color_tuples)
        return color_dict
    def __loadFreeSurferSurf(self,subj,**kw):
        """Auxiliary function to read the corresponding surface file for hemi and name.
        Scalars can be added to the output surface"""
        if kw.has_key('name') and kw.has_key('hemi'):
            #Check required arguments
            name=kw['hemi']+'h.'+kw['name']
        else:
            print 'Name=<surface> and hemi=<l|r> are required.'
            raise Exception('Name=<surface> and hemi=<l|r> are required.')
        if kw.has_key('scalars'):
            scalars=self.get('SURF_SCALAR',subj,hemi=name[0],scalars=kw['scalars'])
            #Take advantage of cache
            kw.pop('scalars')
            orig=self.get('SURF', subj, **kw)
            addScalars(orig, scalars)
            return orig
        path=os.path.join(self.__root,str(subj),'Surf')
        filename=path+'/'+name
        output=surface2vtkPolyData(filename)
        if not kw.has_key('space'):
            return output
        else:
            return self.__movePointsToSpace(output, kw['space'], subj)
    def __loadFreeSurferScalar(self,subj,**kw):
        "Auxiliary function to read free surfer scalars"
        morph=set(('area','curv','avg_curv','thickness','volume','sulc'))
        path=os.path.join(self.__root,str(subj),'Surf')
        contents=os.listdir(path)
        if kw.has_key('hemi'):
            hemisphere=kw['hemi']
            hs=hemisphere+'h'
        else:
            print "hemi is required"
            raise(Exception("hemi is required"))
        if kw.get('index'):
            contents=os.listdir(path)
            pattern=re.compile(hs+r'.*\.annot$')
            annots=[m[3:-6] for m in contents if pattern.match(m)!=None]    
            morfs=[m for m in morph if hs+'.'+m in contents]
            return morfs+annots
        if kw.has_key('scalars'):
            scalar_name=kw['scalars']
        else:
            raise(Exception('scalars is required'))
        path=os.path.join(self.__root,str(subj),'Surf')
        if scalar_name in morph:
            if kw.get('lut'):
                return getMorphLUT(scalar_name)
            scalar_filename=path+'/'+hemisphere+'h.'+scalar_name
            scalar_array=read_morph_data(scalar_filename)
            return scalar_array
        else:
            #It should be an annotation
            annot_filename=path+'/'+hemisphere+'h.'+scalar_name+'.annot'
            labels, ctab  , names =read_annot(annot_filename)
            if kw.get('lut'):
                return surfLUT2VTK(ctab, names)
            return  labels
    def __cached_color_fibers(self,subj,color):
        "function that reads colored fibers from cache, if not available creates the structure and attempts to save the cache"
        color=color.lower()
        cache_name=os.path.join(self.getDataRoot(),subj,'camino','streams_%s.vtk'%color)
        cached=False
        if color=='orient':
            cache_name=os.path.join(self.getDataRoot(),subj,'camino','streams.vtk')
            cached=True
        try:
            cache_f=open(cache_name)
            cache_f.close()
        except IOError:
                pass
        else:
            cached=True
        if cached:
            fib_reader=vtk.vtkPolyDataReader()
            fib_reader.SetFileName(cache_name)
            try:
                fib_reader.Update()
            except:
                print "problems reading %s"%cache_name
                raise
            else:
                out=fib_reader.GetOutput()
                fib_reader.CloseVTKFile()
                return out
        else:
            fun_args=tuple()
            fibers=self.__cached_color_fibers(subj, 'orient')
            if color=='orient':
                return fibers
            elif color=='y':
                color_fun=braviz.readAndFilter.color_fibers.color_by_z
                braviz.readAndFilter.color_fibers.color_fibers_pts(fibers, color_fun)
            elif color=='fa':
                color_fun=braviz.readAndFilter.color_fibers.color_by_fa
                fa_img=self.get('fa',subj,format='vtk')
                fun_args=(fa_img,)
                braviz.readAndFilter.color_fibers.color_fibers_pts(fibers, color_fun,*fun_args)
            elif color=='rand':
                color_fun=braviz.readAndFilter.color_fibers.random_line
                braviz.readAndFilter.color_fibers.color_fibers_lines(fibers, color_fun)
            elif color=='curv':
                color_fun=braviz.readAndFilter.color_fibers.line_curvature
                braviz.readAndFilter.color_fibers.color_fibers_lines(fibers, color_fun)
            else:
                raise Exception('Unknown coloring scheme %s'%color)
            
            #Cache write
            try:
                fib_writer=vtk.vtkPolyDataWriter()
                fib_writer.SetFileName(cache_name)
                fib_writer.SetInputData(fibers)
                fib_writer.SetFileTypeToBinary()
                fib_writer.Update()
            except:
                print 'cache write failed'
            return fibers
    def __cached_filter_fibers(self,subj,waypoint):
        "Only one waypoint, returns a set"
        #print "filtering for model "+waypoint
        pickles_dir=os.path.join(self.getDataRoot(),'pickles')
        pickle_name='fibers_%s_%s.pickle'%(subj,waypoint)
        try:
            cache_file=open(os.path.join(pickles_dir,pickle_name),'rb')
        except IOError:
            print "cache not found"
        else:
            ids=cPickle.Unpickler(cache_file).load()
            cache_file.close()
            #print "read from cache"
            return ids
        
        fibers=self.get('fibers', subj,space='world')
        model=self.get('model', subj,name=waypoint,space='world')
        if model:
            ids=braviz.readAndFilter.filterPolylinesWithModel(fibers, model, do_remove=False)
        else:
            ids=set()
        
        try:
            cache_file=open(os.path.join(pickles_dir,pickle_name),'wb')
        except IOError:
            print "cache write failed: %s"%cache_file
        else:
            cPickle.Pickler(cache_file,2).dump(ids)
            cache_file.close()
        return ids        
        
        
    def __readFibers(self,subj,**kw):
        """Auxiliary function for reading fibers, uses all the cache available.
        First reades the correct color file,
        afterwards the lists for the corresponding waypoints from which an intersection is calculated,
        the list is then used to remove unwanted polylines,
        and finally the fibers are translated to the wanted space
        """   
        if kw.has_key('progress'):
            kw['progress'].set(5)
        if kw.has_key('waypoint') and kw.get('space','').lower()=='world':
            #Do filtering in world coordinates
            models=kw.pop('waypoint')
            if isinstance(models,str):
                models=(models,)
            valid_ids=None
            for nm,model_name in enumerate(models):
                #model=self.get('model', subj,name=model_name,space='world')
                #if model:
                #    filterPolylinesWithModel(fibers,model,progress=kw.get('progress'))
                new_ids=self.__cached_filter_fibers(subj, model_name)
                if valid_ids==None:
                    valid_ids=new_ids
                else:
                    valid_ids.intersection_update(new_ids)
                if kw.has_key('progress'):
                    kw['progress'].set(nm/len(models)*100)
            if valid_ids==None:
                valid_ids=set()
            
            #print valid_ids
            #Take advantage of buffer
            fibers=self.get('fibers', subj,space='world',color=kw.get('color','orient'))
            #print fibers
            for i in xrange(fibers.GetNumberOfCells()):
                if i not in valid_ids:
                    #print "marking %d for deletion"%i
                    fibers.GetCell(i)
                    fibers.DeleteCell(i)
            #print "removing cells"
            fibers.RemoveDeletedCells()
            cleaner=vtk.vtkCleanPolyData()
            cleaner.SetInputData(fibers)
            cleaner.Update()
            fibers2=cleaner.GetOutput()
            return fibers2
        if kw.has_key('waypoint'):
            #Always filter in world coordinates
            if kw.has_key('progress'):
                filtered_fibers=self.get('fibers', subj,space='world',waypoint=kw['waypoint'],color=kw.get('color','orient'),progress=kw['progress'])
            else:
                filtered_fibers=self.get('fibers', subj,space='world',waypoint=kw['waypoint'],color=kw.get('color','orient'))
            if kw.has_key('space'):
                streams_trans=self.__movePointsToSpace(filtered_fibers, kw['space'],subj)
                return streams_trans
            else:
                return filtered_fibers
        path=os.path.join(self.__root,str(subj),'camino')
        streams=self.__cached_color_fibers(subj, kw.get('color','orient'))
        if kw.has_key('space') and kw.get('space').lower() in set(['diff','native']):
            return streams
        matrix=readFlirtMatrix('diff2surf.mat','FA.nii.gz','orig.nii.gz',path)
        streams_mri=transformPolyData(streams,matrix)
        if kw.has_key('space') and kw.get('space').lower()!='world':
            streams_trans=self.__movePointsToSpace(streams_mri, kw['space'],subj)
            return streams_trans
        return streams_mri
    def __readTensors(self,subj,**kw):
        "Internal function to read a tensor file"
        path=os.path.join(self.__root,str(subj),'camino')
        tensor_file=os.path.join(path,'camino_dt.nii.gz')
        if kw.get('space')=='world':
            tensor_file=os.path.join(path,'camino2_dt.nii.gz')
        fa_file=os.path.join(path,'FA_masked.nii.gz')
        #tensor_data=readTensorImage(tensor_file, fa_file)
        tensor_data=cached_readTensorImage(tensor_file, fa_file)
        #tensor_data=readTensorImage(tensor_file)
        if kw.get('space')=='world':
            matrix=readFlirtMatrix('diff2surf.mat','FA.nii.gz','orig.nii.gz',path)
            tensors_mri=transformGeneralData(tensor_data,matrix)
            return tensors_mri
        return tensor_data
    def __movePointsToSpace(self,point_set,space,subj,inverse=False):
        """Transforms a set of points in 'world' space to the talairach or template spaces
        If inverse is True, the points will be moved from 'space' to world"""
        if space.lower()[:2]=='wo':
            return point_set
        elif space.lower()[:2]=='ta':
            talairach_file=os.path.join(self.__root,str(subj),'Surf','talairach.xfm')
            transform=readFreeSurferTransform(talairach_file)
            if inverse:
                transform=inv(transform)
            return transformPolyData(point_set,transform)
        elif space.lower() in ('template','dartel'):
            dartel_yfile=os.path.join(self.__root,'Dartel',"y_%s-forw.nii.gz"%subj)
            if inverse:
                dartel_yfile=os.path.join(self.__root,'Dartel',"y_%s-back.nii.gz"%subj)
            dartel_warp=dartel2GridTransform(dartel_yfile)
            return transformPolyData(point_set,dartel_warp)
        elif space[:4] in ('func','fmri'):
            #functional space
            paradigm = space[5:]
            trans=self.__read_func_transform(subj,paradigm,inverse)
            return transformPolyData(point_set, trans)
        else:
            print 'Unknown Space %s'%space
            raise Exception('Unknown Space %s'%space)

    def __create_surfer_lut(self):
        "returns a vtkLookUpTable based on the freeSurferColorLUT file"
        color_file_name=os.path.join(self.getDataRoot(),'FreeSurferColorLUT.txt')
        try:
            color_file=open(color_file_name)
        except IOError as e:
            print e
            raise
        color_lines=color_file.readlines()
        color_file.close()
        color_lists=[l.split() for l in color_lines if l[0] not in ['#','\n',' '] ]
        color_tuples=[(int(l[0]),
                      ( tuple( [float(c)/256 for c in l[2:2+3] ]+[1.0])
                        ,l[1]) ) 
                      for l in color_lists]           #(index,(color,annot) )
        color_dict=dict(color_tuples)
        out_lut=vtk.vtkLookupTable()
        out_lut.SetNanColor(0.0, 1.0, 0.0, 1.0)
        out_lut.SetNumberOfTableValues(max(color_dict.keys())+1)
        out_lut.IndexedLookupOn()
        for i in color_dict.keys():
            out_lut.SetAnnotation(i,color_dict[i][1])
        for i in color_dict.keys():    #HACKY.... maybe there is a bug?
            idx=out_lut.GetAnnotatedValueIndex(i)
            out_lut.SetTableValue(idx,color_dict[i][0] )

        return out_lut
    def __read_func_transform(self,subject,paradigm,inverse=False):
        "reads the transform from world to functional space"
        name=paradigm.upper()
        path = os.path.join(self.getDataRoot(), subject, 'spm')
        if inverse is False:
            dartel_warp=os.path.join(path,name,'y_seg_forw.nii.gz')
            T1_func=os.path.join(path,name,'T1.nii.gz')
            T1_world=os.path.join(path,'T1','T1.nii.gz')
            dartel_trans=dartel2GridTransform(dartel_warp, True)
            T1_func_img=nib.load(T1_func)
            T1_world_img=nib.load(T1_world)
            Tf=T1_func_img.get_affine()
            Tw=T1_world_img.get_affine()
            T_dif=np.dot(Tf,inv(Tw))
            aff_vtk = numpy2vtkMatrix(T_dif)

            vtkTrans = vtk.vtkMatrixToLinearTransform()
            vtkTrans.SetInput(aff_vtk)

            concatenated_trans=vtk.vtkGeneralTransform()
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
    def __read_func(self,subject,**kw):
        "Internal function to read functional images, deals with the SPM transforms"
        if not kw.has_key('name'):
            raise Exception('Paradigm name is required')
        name=kw['name']
        space=kw.get('space','world')
        name=name.upper()
        space=space.lower()
        if name not in ('PRECISION','POWERGRIP'):
            print " functional paradigm %s not available"%name
            return None
        path=os.path.join( self.getDataRoot(),subject,'spm')
        z_map=os.path.join(path,name,'spmT_0001.hdr')
        nii_z_map=nib.load(z_map)
        if kw.get('format','nifti').lower()=='nifti':
            return nii_z_map
        vtk_z_map=nibNii2vtk(nii_z_map)
        if space=='native':
            return vtk_z_map
        vtk_z_map=applyTransform(vtk_z_map, inv(nii_z_map.get_affine()))
        if space[:4]=='func':
            return vtk_z_map


        T1_world = self.get('mri',subject,format='vtk',space='world')
        origin2=T1_world.GetOrigin()
        dimension2=T1_world.GetDimensions()
        spacing2=T1_world.GetSpacing()
        fmri_trans=self.__read_func_transform(subject,name)
        world_z_map = applyTransform(vtk_z_map, fmri_trans, origin2, dimension2, spacing2)

        return self.__move_img_from_world(subject, world_z_map,True, kw.get('space','world'))

    def __read_bold(self,subj,paradigm):
        paradigm=paradigm.upper()
        route=os.path.join(self.getDataRoot(),subj,'spm',paradigm,'smoothed.nii.gz')
        img_4d = nib.load(route)
        return img_4d
    
    #def read_func_transform(self,subject,paradigm,inverse):
    #    return self.__read_func_transform(subject,paradigm,inverse)
        
    def getDataRoot(self):
        "Returns the data_root of this reader"
        return self.__root
    def transformPointsToSpace(self,point_set,space,subj,inverse=False):
        """Access to the internal coordinate transform function. Moves from world to space. 
        If inverse is true moves from space to world"""
        return self.__movePointsToSpace(point_set, space, subj, inverse)
        
#===============================================================================================
def autoReader(**kw_args):
    "Initialized a kmc40Reader based on the computer name"
    known_nodes={'IIND-EML753022': ('C:\\Users\\da.angulo39\\Documents\\Kanguro',200),
    'gambita.uniandes.edu.co': ('/media/DATAPART5/KAB-db',500),
    'Unidelosandes' : ('K:\\JohanaForero\\KAB-db',200),
    'dieg8' : (r'C:\Users\Diego\Documents\kmc40-db\KAB-db',200),}
    node_id=platform.node()
    
    if known_nodes.has_key(node_id):
        #print data_root
        #print max_cache
        data_root=known_nodes[node_id][0]
        if kw_args.get('max_cache',0)>0:
            max_cache=kw_args.pop('max_cache')
        else:
            max_cache=known_nodes[node_id][1]
        return kmc40Reader(data_root,max_cache=max_cache,**kw_args)
    else:
        print "Unknown node %s, please enter route to data"%node_id
        path=raw_input('KMC_root: ')
        return kmc40Reader(path,**kw_args)
        # add other strategies to find the project __root
    
    
