@echo off

set source_file="%1"

for %%F in (%0) do set dirname=%%~dpF
echo %dirname%
cd %dirname%

if NOT %source_file%=="" (
	echo ########################################### > braviz.cfg
	echo #File copied from %source_file% >> braviz.cfg
	echo #Changes to this file will be overwritten, modify %source_file% instead >> braviz.cfg
	echo ########################################### >> braviz.cfg
	echo. >> braviz.cfg
	type %source_file% >> braviz.cfg
	echo Using %source_file% configuration
)

title Braviz
braviz_menu2.py