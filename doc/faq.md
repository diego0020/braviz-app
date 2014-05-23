#Braviz Frequenty Asked Questions

--------------------------------------------

## Subject Overview

#### Where do I start?
>This application can show you several types of data from a single subject.
>In the buttom frame you find some information about the current subj and the left panel provide controls over what you are seeing in the main view. The different tabs in the left panel allow you to control diferent kinds of data. There are tabs for controlling
>
> * Images
> * Segmented Structures
> * Tractography
> * Cortex parcelations
>
>Additionally there are two tabs that give additional tabular information of the subject. The arrows under the main view can be used to cycle through subjects.
>Finally the panel at the bottom left allows you to reset the camera to standard views, and to change the coordinate system.


#### How do I navigate the *3D* View?

> When you click over an image or a cortical surface, you will be able to query information about them. In order to move the camera it is necessary to click *outside* from any of these. 
> * To rotate the view, click, hold and move. Release the button to stop.
> * To rotate about an axis perpendicular to the screen, hold *control*, click, hold and move, as above.
> * To pan the view, middle-click hold and move. Release the button to stop. Alternatively use left click while holding shift.
> * To zoom the view right-click hold and move up or down. Release the button to stop. Alternatively you can use the mouse wheel.
> If you want to reset the camera look at the next question.

#### How do I reset the camera?

> In the bottom-left you will find a box labeled "camera to:", which will allow you to reset the camera to some useful predefined positions.

#### How do I change subject?

> Use the arrows under the main view. Alternatively, go to the subjects tab of the left panel and double click a subject in the list.

#### How do I change the current *coordinate* system ?

> In the bottom-left you will find a box labeled "Coordinates", which will allow you to choose a coordinate system for the viewer.

#### What *coordinate* systems are available?

> Currently there are three coordinate systems available:
> * World: This correspond to real world coordinates in *mm*. 
> * Talairach: Individuals are mapped to a talairach standard brain using an affine transform. This means that all objects are rotated and scaled in order to match the template. Relative distances are preserved.
> * Dartel: A non linear transformation is applied to map subjects to a Dartel template. Here each area of the brain is distorted in a different way, resulting in a very close match, but significant overall distortion. This is useful for comparing values at approximately similar locations across different subjects.

### Images

Most image manipulation tasks are carried out using the image tab of the left frame.

#### How do I change the Image *slice*

> Use the slice box or the slider in the Image tab. Alternatively hold the middle mouse button over the image and move the mouse.

#### How do I change the current Image?

> Use the modality box in the Image tab.

#### How do I *hide* the Image?

> Select None in the modality box of the image tab.

#### How do I change the *orientation* of the Image ?

> Use the Orientation box in the image tab. Notice the camera will not move when changing the orientation, so you will probably have to move it in order to get a good view of the new image.

### Segmented Structures

Most of the tasks in this list are accomplished using the Segmentation tab of the left panel.

#### How do I display structures?

> Use the list in the Segmentation tab to *check* the structures you want to see.

#### How do I change the *color* of the structures?

> Use the color box below the list in the Segmentation tab. Selecting Free Surfer will use the free surfer color table, selecting custom will allow you to select a color.

#### How can I display areas of the *dominant* cortex?

> By default the list displays the right and left cortex as two separate sub-trees. If you prefer to work with dominant and non-dominant cortexes, use the radio button on top of the list.

#### How can I *calculate* metrics from the structures?

> At the bottom of the tab there is a button which allows you to select among different metrics. Currently these are
>
> * Volume: The total volume of the structures (always in world coordinates)
> * Area: The surface area of the displayed structures. In case that more than one structure is showed, their values are added together.
> * FA Inside: The mean FA value of the voxels inside the displayed structures 
> * MD Inside: The mean MD value of the voxels inside the displayed structures 
>
> The calculated value will be displayed next to the box. The button labeled "Export to database" will open a dialog that will allow you to repeat the calculation for all subjects and save the results into the database.

### Tractography

> Most of the tasks in this list are accomplished using the Segmentation tab of the left panel.

#### How can I see the *full* tractography?

> Click on the "Select Saved Bundles" button and select the bundle called All near the top of the list.

#### How can I *filter* fibers?

> It is possible to filter the tractography using segmented structures. For these look at the box labeled "From Seg." There will be two options
>
> * Through Any: Display fibers that cross any of the displayed structures
> * Through All: Display fibers that pass through all the displayed structures
>
> Fiber bundles defined in this way can be *saved* using the "Save Bundle" button, and will be afterwards available in the Select Saved Bundle dialog.
> Most complex fiber selection operations will be available in a future tool.

#### How can I change the *color* of the current fibers ?

> The box labeled color has several options for coloring the fibers:
>
> * Orientation: Segments going from left to right will be colored red, segments from top to buttom will be blue and segments from back to front will be green
> * FA (Point): The colors of each point are determined by the FA value at the corresponding voxel. A color bar is available with the convention.
> * FA (Line): The colors of each line are determined by the mean FA value across the complete line. A color bar is available with the convention.
> * MD (Point): The colors of each point are determined by the MD value at the corresponding voxel. A color bar is available with the convention.
> * MD (Line): The colors of each line are determined by the mean MD value across the complete line. A color bar is available with the convention.
> * Length: The colors of each line are determined according to its length. A color bar is available.
> * By Line: A random color is assigned to each line, this makes it easy to follow a single line.
> * By Bundle: Each bundle (loaded through the "select saved bundles button") is assigned a different color

#### How can I view multiple *bundles* ?

> The "Select Saved Bundles" button can be used to add bundles to the current display.

#### How can I *calculate* metrics of the current fibers?

> First you have to select a bundle by double clicking it in the Bundles list. The selected bundle is shown at the end of the Tractography tab. 
> There is a box towards the bottom of the tab that can be used to select among different metrics, the value will be shown in the box next to it.
> The "Export to Database" button can be used to calculate this values for all subjects and save the results into the database.

### Context Panel

#### How can I change the displayed variables?

> Right click on anywhere in the context panel, and click on "Change Variables" in the context menu. A dialog will appear. To add a variable,
> double click on its name in the top list, review metadata, and then click on "Save and Add". The variable should now appear on the bottom list.
> To remove a variable, right click on its name in the bottom list, and click on "remove".

#### How can I define a new variable?

> Right click on anywhere in the context panel, and click on "Change Variables" in the context menu. The variable selection dialog will appear. Between the two 
> lists at the left you will find a button labeled "Create Variable". A dialog will appear, where you should enter the new variable name, its type, and description. 
> If the variable is nominal, it is highly recommended to use this dialog to define the *labels* for the different levels.

## Samples Overview

#### What am I looking at?

#### How do I change the current camera?

#### How do I change the *grouping* variable?

#### How do I change the *sorting* variable?

#### How do I change the current *coordinates*?

## Anova Analysis

#### How do I perform an Anova analysis?

#### What is an *outcome* variable?

#### What is the *residuals* plot ?

## Linear Regression

#### What is the *coefficients* plot?

## Scenarios

#### What are scenarios?

## Samples

#### What are samples?