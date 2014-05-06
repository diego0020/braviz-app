# Mac installation

## Dependencies

### Home Brew
If you don't have home brew installed go to the folder where you would like to install it and do:
    git clone https://github.com/Homebrew/homebrew.git
Afterwards, add the homebrew/bin directory to your path. This can be done for example by adding the following line to your .bash_profile file
    export PATH=home_brew_dir/homebrew/bin:$PATH

It is possible that it will give you warning about not having xcode, in this case you should install xcode from the apple app store, and then do
xcode-select in the terminal
### Python
It is recomended to use the python version from homebrew, this can be installed by doing
    brew install python

### Homebrew Python packages
The following python packages should also be installed from homebrew
- Numpy
- SciPy
- Matplotlib
- PyQt
This packages can be found in homebrew-python, and they can be installed by doing
    brew tap Homebrew/python
    brew install numpy
    brew install scipy
    brew install matplotlib
    brew install pyqt

### R
R can also be installed from homebrew, it is located in homebre-science. The commands are
    brew tap homebrew/science
    brew install r
After installing r, some additional r libraries should be installed, this can be done by opening R
    r
and then typing
    packages.install("car")
    packages.install("randomForest")
    quit()

### VTK
vtk can also be installed from homebrew-science. This should be done after installing PyQt. The command is
    brew tap homebrew/science
    brew install vtk --with-qt

### Mercurial
Mercurial is the version control software used by braviz, and the easyest way to be up to date


## Additional python packages

All this packages can be installed through pip, the basic syntax is
    pip install <package_name>
The following is the list of required packages
- nibabel
- colorbrewer
- rdflib
- httplib2
- psutil
- pandas
- mpltools

## Get braviz
Go to the directory where you would like braviz files downloaded and do
    hg clone <repository_adress>
You can contact jc.forero47@uniandes.edu.co to get the repository adress

You should now add the braviz directory containing the file setup.py to your PYTHONPATH environment variable
    export PYTHONPATH = $PYTHONPATH:<braviz_dict>
You can add that line to your .bash_profile file in order to have braviz always available when you start a terminal

After getting the braviz source files you should run
    python braviz/interaction/generate_qt_guis.py
To create qt interface files

## Run braviz
After meeting all the requirements, and having the code, you should be able to run braviz by doing
    python -m braviz.application.braviz_menu2

