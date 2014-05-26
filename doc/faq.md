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

#### What *coordinate* systems are available?{#coordinates}

> Currently there are three coordinate systems available:
> * World: This correspond to real world coordinates in *mm*. 
> * Talairach: Individuals are mapped to a talairach standard brain using an affine transform. This means that all objects are rotated and scaled in order to match the template. Relative distances are preserved.
> * Dartel: A non linear transformation is applied to map subjects to a Dartel template. Here each area of the brain is distorted in a different way, resulting in a very close match, but significant overall distortion. This is useful for comparing values at approximately similar locations across different subjects.

#### How can I *Save* my work?

> Click in the "file" menu and afterwards in "save scenario". You will be given the option to write a description that could be helpful in the future to identify this scenario.

#### How can I *Load* a previous state?

> Click in the "file" menu and afterwards in "load scenario". A dialog will appear where you can select among all the scenarios you have saved.

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

> Right click anywhere in the context panel, and click on "Change Variables" in the context menu. A dialog will appear. To add a variable,
> double click on its name in the top list, review metadata, and then click on "Save and Add". The variable should now appear on the bottom list.
> To remove a variable, right click on its name in the bottom list, and click on "remove".

#### How can I define a new variable?

> Right click on anywhere in the context panel, and click on "Change Variables" in the context menu. The variable selection dialog will appear. Between the two 
> lists at the left you will find a button labeled "Create Variable". A dialog will appear, where you should enter the new variable name, its type, and description. 
> If the variable is nominal, it is highly recommended to use this dialog to define the *labels* for the different levels.

## Samples Overview

#### What am I looking at?

> This tool shows you data from several subjects at the same time. 3d data is organized in groups and sorted from left to right. The data inside each of the views is loaded from a scenario defined in the *Subject* *overview* tool. 
> In order to load a view, click in the "file" menu and then in "load visualization". A dialog will appear where you can access all of your saved scenarios.

#### How do I change the current camera?

> You can click in an empty space in any of the 3d viewers and navigate as if you were in the subject overview application. Afterwards you may use the "Camera" box in order to copy the camera to all the viewers or to reload the original camera.

#### How do I change the *grouping* variable?

> Use the "Facet Variable" box. Notice that only *nominal* variables can be selected for this role.

#### How do I change the *sorting* variable?

> Use the "Sort Variable" box. Notice that only *rational* variables can be selected for this role.

#### How do I change the current *coordinates*?

> Use the coordinates box. For an overview of the available coordinates look at [What coordinates systems are available?](#coordinates)

## Anova Analysis

#### How do I perform an Anova analysis?

#### What is an *outcome* variable (Dependent variable)?

> This is the variable that is affected by a change in the other variables. Also called response, dependent variable or $y$.
> This could also be a variable we are interested in predict based on the other variables (regressors).

#### How do I add regressors or independent variables?

> To add independent variables click on the "add regressor" button. A dialog where you can select variables will be shown. Select a variable by double clicking on its name, review the meta data information at the middle of the dialog, and afterwards click on "save and add" in the left.

#### How do I add interactions?

> Click in the "add interaction" button. A dialog with the current regressors on top and the current interactions in the button will be shown.
> To add a single interaction term, select the factors in the top list (by hodling ctrl and clicking on their names) and then click on add single term. If you want to add all the possible interactions between the variables click in add all combinations. When you are done close the dialog by clicking on the close button at the top of the window.

#### How do I remove a regressor or interaction ?

> Right click on its name in the regressors list, and select remove.

#### What is the *residuals* plot ?

> The residuals plot show the distribution of the residuals after fitting the model. If the Anova's pre conditions are met, these residuals should be distributed in a normal distribution, and they should be independent from the outcome variable. 
> If you notice that the residuals histogram is skewed or that the variance changes with the outcome variable, you should rethink your model. Maybe you are missing a variable, or maybe variables should be transformed.

#### What type of sum of squares is being used for the calculation?

> We are using a type 3 sum of squares, as defined in the [car](http://cran.r-project.org/web/packages/car/) anova function. We chose this type of sum because
> that is the default in many of the statistical software used in the domain.

## Linear Regression

#### Are variables in the linear model centered?

> Yes, all rational variables are standardized by substracting the mean and dividing by 2 standard deviations. 
> All nominal variables with two levels are standardized in such a way that the mean is zero, and the standard deviation is 1. 
> Nominal variables with more than two levels are left as they are.
> The outcome variable is also standardized. All of this is accomplished using the 
> "Standardize" function in the [ARM](http://cran.r-project.org/web/packages/arm/index.html) package.

#### What is the *coefficients* plot?

> The coefficients plot gives a quick indication of which coefficients are important for the model. The thick line corresponds to 1 standard deviation, and the thin line to the 95% confidence interval. If any of these lines cross the zero line, then that coefficient is not significantly different from zero. Also, the further away the coefficients are from the zero, the largest the effect size.

## Scenarios

#### What are scenarios?

> Scenarios inside braviz correspond to states of the different tools. These include the selected variables, cameras for 3d views, selected structures in views, etc. The idea is to keep track of your exploration, to enable you to go back to a previous state, and to re visit interesting visializations.

## Subsamples

#### What are samples?

> Samples allow you to run all kinds of analyses in a subset of the population.
> You may define for example a sample for only female participants and run specific
> tests in this smaller population. Most of the tools in the braviz toolkit have an option
> to select a subsample.

#### How do I define a new subsample?

> When clicking in "new" in the subsamples dialog a dialog will appear. The left panel provides
> a working space, and the right panel provides a view of the current sample. In the middle there are
> buttons which allow you to move data between the two panels. You may hover the mouse over them
> to get a better idea of what they do.
> You may also right click in a single subject in the left panel to show a context menu with the
> option of adding him manually to the sample. In the same way you can right click in individual subjects in the right
> panel in order to remove them from the sample (for example outliers or erroneus data).

