__author__ = 'diego'


from braviz.readAndFilter.base_reader import BaseReader
from sphinxcontrib.napoleon import Config
config = Config(napoleon_use_param=True, napoleon_use_rtype=True)


import sphinxcontrib.napoleon
#docstring=BaseReader.get.__doc__

docstring="""Provides access to geometric data in an specified coordinate system.

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
        subject             Defined by the MRI image

        talairach         MRI image after applying an affine transformation to the Talairach coordinates

        dartel            Non-linear warp towards a template

        diff              Defined by the diffusion images

        fmri-<pdgm>       Defined by the SPM results

        native            Ignores all transformations, raw voxels data
        ===============   ==================================

        Notice that some data types are not available in every space, in this case an exception will be risen.
    **kwargs: Arguments specific to each data type

"""


docstring2 = """Creates the basic directory structure used for braviz starting at the specified path.

Args:
    dir_name(str): The path where the structure will be created.
        If None, the value returned by :meth:`get_auto_dyn_data_root` will be used
"""
res=sphinxcontrib.napoleon.GoogleDocstring(docstring2,config,what="method")
print res

