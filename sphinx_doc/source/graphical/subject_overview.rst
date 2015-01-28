Subject Overview
==================

.. image:: images/subj_overview.png
    :align: center
    :width: 90%
    :alt: Subject overview screenshot

This is the largest application in the braviz systems. It provides access to several kinds of neuro-image based data
for a single subject in the same view. The kind of data and visualization parameters can be configured using individual
controls. Afterwards it is possible to cycle through the subjects keeping this parameters constant.

This application sends a message to the rest of the system when the current subject changes. It also listens for
messages indicating a subject change, and when it receives one switches to that subject. If you want to avoid that
behaviour, press the keychain button at the right side of the subject widget.

Most of the application interface is occupied by a 3d viewer (see :doc:`3dviews`). At the left side is the control
panel, where the graphical attributes for the different data types can be set. This panel includes tabs for controling
the list of available subjects, and for showing additional details.  At the lower left is a small panel for changing
the coordinate system (see :doc:`concepts`) and for resetting the camera to pre defined locations.

Under the main 3d viewer is a widget that displays the current subject and allows you to change it, and at the
very bottom is a *context panel* which provides values for certain variables for the current subject.

.. hint::
    The control panel, context panel, and the subject widget can be hidden in order to provide more room
    for the 3d view. Move the mouse to their border until you get
    a cursor with two arrows, then click and drag to hide (or enlarge) these panels.

Changing subjects
-------------------

.. image:: images/subject_overview/select_subject.png
    :align: center
    :alt: Subject selection widget

This widget displays the current subject and lets you change it. The arrow buttons can be used to select the
previous and next subjects based on the list shown in the *Subjects tab* of the control panel. You can also click
on the text area and write the id of a subject using the keyboard. Notice a message will be broad-casted to all other
applications indicating the new subject.

The keychain button allows you to lock the current subject. In the locked status it will become impossible to change
the current subject, neither by using the other controls in this widget nor by messages from other applications.

.. hint::
    You can also use the left and right arrow keys in the keyboard to change subjects.

The context panel
------------------

.. image:: images/subject_overview/context.png
    :align: center
    :width: 100%
    :alt: Context panel

The context panel displays the values of some variables for the current subject. It is meant to provide additional
information about the subject useful when interpreting the images. At the start the variables shown are those
found in the configuration file (see :doc:`configuration`), but you may choose the ones that are more important
for the actual analysis. In order to do that right click inside the panel and from the context menu select
*change variables*. A dialog for selecting variables will appear. This dialog includes a secondary table at the
bottom left containing the actual variables. From this dialog you may also create a new variable and
optionally give it initial values. The current variables table has a column indicating the variable type and a
check-box indicating if it should be possible to modify the variable value from the panel.
A panel with editable variables will look like this

.. image:: images/subject_overview/context_edit.png
    :align: center
    :width: 100%
    :alt: Context panel with editable variables

In this case you may modify the variable values based on your observations of the image. Values are only saved
into the database after clicking on the *Save* button.


The view panel
---------------

.. image:: images/subject_overview/view.png
    :align: center
    :width: 30%
    :alt: View panel

This panel has two functions. First it lets you select the coordinate system used in the 3d viewer. Second, it allows
you to reset the camera to a predefined position. Using *Talairach* or *Dartel* coordinates will make it easier to
compare different subjects, but it will add some distortion to the objects in the viewer.

The control panel
------------------

.. image:: images/subject_overview/control.png
    :align: center
    :width: 80%
    :alt: Control panel tabs

The control panel houses the controls for adding, removing, and modifying visual properties of the objects in the
viewer. It also lets you modify the order in which subjects are traversed and the current subsample. Finally it lets
you see additional details of the current subject. All of these features are available under different tabs.

Subject tab
^^^^^^^^^^^^

.. image:: images/subject_overview/subject_tab.png
    :align: center
    :width: 50%
    :alt: Subject tab

This tab shows a table with the subjects in the current sample. By default they are ordered by code, but you can
click on the header of any column to change the order. The *select sample* button allows you to select a subsample
of subjects to use in the application. By pressing the *select table columns* button will open a dialog where you
can select which variables you want to be displayed as columns in the table. If you double click on any of the rows
of the table the application will switch to that subject. Finally, notice that the order in which subjects are
traversed using the *subject selection widget* is determined by this table.

Details tab
^^^^^^^^^^^^

.. image:: images/subject_overview/details_tab.png
    :align: center
    :width: 50%
    :alt: Details tab

This tab lets you view additional variable values for the current subject. In this case each variable is displayed
as a row in the table with the value in front. For real variables the minimum and maximum values found inside the
reference population (see :doc:`configuration`). A star is shown next to the values that fall outside this range.
Clicking the *select variables* button will display a dialog where you can select the variables that will be used as
rows for the table.

.. hint::
    You may change the order of the rows by dragging them with the mouse.

At the bottom of the tab is a large text field where you can write general comments about the subject. This comments
will be saved into the database when you click on *save*. The next time you open the same subject the previously
entered comments will show again. You can use this to register remarks or peculiarities about a subject that should
be taken into account when looking at him.


Images tab
^^^^^^^^^^^^

.. image:: images/subject_overview/images_tab.png
    :align: center
    :width: 50%
    :alt: Images tab

Here you can control the image shown in the main view, or switch it off. The *modality* field is where you select the
kind of image you want to see. Available options include anatomical MRI, color DTI, FA, freesurfer *APARC* segmentation
and fMRI paradigms. In case you choose an fMRI paradigm the second field, labeled *Contrast* will become active. You
can then use it to select the contrast of interest.
The orientation box lets you select the orientation of the image plane.

In some kinds of images you can manipulate the window and level values from the lookup-table using the corresponding
fields. Notices you can achieve the same effect by right clicking and dragging the mouse on top of the image in the
3d view. The *Reset* button can be used to reinitialize the window and level values.

Finally the slice field and slider display the current slice and allows you to move it.

.. hint::
    You can use the mouse wheel to change slice while the cursor is on top of the slider or the slice number field.
    You can also use the top and down arrows in the keyboard when the cursor is on the slice number field.


fMRI tab
^^^^^^^^^^^^

.. image:: images/subject_overview/fmri_tab.png
    :align: center
    :width: 50%
    :alt: fMRI tab

This tab allows you to display iso-contours of fMRI statistical maps. The *paradigm* and *contrast* fields are used
to select the map of interest. The *contours* checkbox activates or deactivates the contours, and the value in front
is the T-score value at which you want to show contours. The color of the contours will be the color used for that
value in the fMRI lookup-table.

Segmentation tab
^^^^^^^^^^^^^^^^^^

.. image:: images/subject_overview/segmentation_tab.png
    :align: center
    :width: 50%
    :alt: Subject tab

Tractography tab
^^^^^^^^^^^^^^^^^^

.. image:: images/subject_overview/tractography_tab.png
    :align: center
    :width: 50%
    :alt: Tractography tab


Tracula tab
^^^^^^^^^^^^^^^^^^

.. image:: images/subject_overview/tracula_tab.png
    :align: center
    :width: 50%
    :alt: Tracula tab

Surfaces tab
^^^^^^^^^^^^^^^^^^

.. image:: images/subject_overview/surfaces_tab.png
    :align: center
    :width: 50%
    :alt: Surfaces tab

Scenarios
------------

Saving and loading