Cross Section toolbox for ArcGIS 10.2

Evan Thoms, USGS

A toolbox of python-based geoprocessing tools for performing a variety of tasks associated with (primarily, but not limited to) geologic cross-sections:

-convert lines of cross-section over a DEM to surface profiles
-convert a line of cross-section over a DEM and a geologic polygon layer to a surface profile of contiguous line segments attributed the same as the polygon layer
-convert borehole location points and an optional table of borehole interval descriptions to sticklogs
-convert structural measurement points to cross-section points attributed with the apparent dip

To install:
-open up https://github.com/evanthoms/Cross-Section
-go to the lower right and click on Download Zip
-this will download the file Cross-Section-master.zip.
-extract the contents of that zip file to a suitable folder
-that will extract a folder called GeologicCrossSectionTbx, a file called .gitattributes, .gitignore, and README.txt. You can delete the latter three files. They have nothing to do with the ArcGIS toolbox. They are only for the case where you want to collaborate on github.
-Go into GeologicCrossSectionTbx, that is where you will see the .tbx file, a folder called docs and a folder called scripts. You need to keep all three of these things together within the same folder. You can move them where ever you like, but they have to stay together. 
-Now, in ArcToolbox, whether opened from ArcMap or ArcCatalog, you can right-click over some empty white space to get the context menu, and choose 'Add Toolbox'. Browse to Cross Section Tools 10.2.tbx and select it.

Demo data:
An ArcGIS 10.2 file geodatabase and mxd are included in \GeologicCrossSectionTbx\demo. All of the different types of data sources necessary to run any of the tools in the toolbox are there. A tutorial will follow.