'''fenceDiagram.py
Description: ArcToolbox tool to take cross section features in cross section
    view and give them real-world 3D coordinates.
Requirements: 3D Analyst extension
Author: Evan Thoms, U.S. Geological Survey, ethoms@usgs.gov
Date: 7/2/10

Method explanation: We can edit the geometries of existing points and they
will plot correctly in 3D, but lines and polygons are different. If we edit the
coordinates of dead vertical lines or polygons they will collapse. When two or more
points in a feature share the same XY (or below the tolerance level so that they
are considered the same point) but different Z coordinates, ArcGIS will not 
recognize those as different points and they collapse to one. At least when 
editing the geometries of existing features. For some reason, when we export
the XYZ coordinates of the features to a text file and use the ASCII 3D to
Feature Class tool to create new features, it works. We get dead vertical lines and
polygons in the same plane. 
'''

import os
import sys
import arcgisscripting
import traceback
import xsec_defs
import bisect

# Create the Geoprocessing object
gp = arcgisscripting.create(9.3)
gp.overwriteoutput = 1

# FUNCTIONS
# *******************************************************
def checkExtensions():
    #Check for the 3d Analyst extension
    try:
        gp.AddMessage('Checking out 3D Analyst extension')
        if gp.CheckExtension('3D') == 'Available':
            gp.CheckOutExtension('3D')
        else:
            raise 'LicenseError'
            
    except 'LicenseError':
        gp.AddMessage('3D Analyst extension is unavailable')
        raise SystemError
            
    except:
        # get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        gp.AddError(pymsg)


def checkInputs(xSecLayer, rasterLayer):
    #check the geometries and data types of the inputs
    try:
        gp.AddMessage('Checking inputs')
        
        # check that input layers are appropriate geometry
        if not (gp.describe(xSecLayer).ShapeType == 'Polyline'):
            gp.AddError('Cross section layer input is not a polyline layer.')
            raise 'endIt'
            
        result = gp.GetCount_management(xSecLayer)
        if  int(result.GetOutput(0)) > 1:
            gp.AddError('The cross section layer has more than one line.')
            raise 'endIt'
            
        if not (gp.describe(linesLayer).ShapeType == 'Polyline'):
            gp.AddError('The lines layer input is not a line layer.')
            raise 'endIt'
                    
        if not (gp.describe(rasterLayer).DatasetType == 'RasterDataset'):
                gp.AddError('DEM input is not a raster layer!')
                raise 'endIt'
                
    except 'endIt':
        raise SystemError
    
    except:
        # get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        gp.AddError(pymsg)

# PARAMETERS
# *******************************************************
# Cross section(s) layer
xSecLayer = gp.GetParameterAsText(0)

# Cross section name field
nameField = gp.GetParameterAsText(1)

# elevation raster layer
dem = gp.GetParameterAsText(2)

#coordinate priority
cp = gp.GetParameterAsText(3)

#intersecting lines layer
#featList = gp.GetParameter(4)
featList = gp.GetParameterAsText(4).split(";")

# vertical exaggeration
ve = gp.GetParameterAsText(5)

# output directory
outDir = gp.GetParameterAsText(6)

# keep intermediate files?
keepf = gp.GetParameterAsText(7)

#BEGIN
#*******************************************************

#Check for the 3d Analyst extension
#gp.CheckExtension(3)
#checkExtensions()

#check inputs
#checkInputs(xSecLayer, dem)

#get the path to the scratch geodatabase
scriptsdir = os.path.dirname(sys.argv[0])
tbxdir = os.path.dirname(scriptsdir)
scratchDir = os.path.join(tbxdir, 'scratch', 'scratch.gdb')

#get the parent folder of the scratch directory, might be a folder
#itself.
scratchFolder = xsec_defs.returnParentFolder(gp, scratchDir)

#set default workspace to the scratch gdb
gp.workspace = scratchDir

#it's necessary to interpolate the line so that a new feature is created in
#the scratch gdb which has a length in the units of the SR of the dem.

'''
If you have an existing ZMline fom a previously run process, comment out the 
next 5 lines, uncomment the line where ZMline is explicitly set, and put in the 
path. This will take less time than interpolating and measuring the cross section 
line from scratch
'''
##Zline = xSecLayer + '_Z'
##xsec_defs.interpolate(gp, xSecLayer, dem, Zline, scratchDir)
##
###measure it and turn it into a route
##ZMline = xSecLayer + '_ZM'
##xsec_defs.measureLines(gp, Zline, nameField, ZMline, 'LENGTH', '#', '#', cp, scratchDir)

ZMline = r'D:\Workspace\PNW\Edmonds\CrossSections\scratch\scratch.gdb\SectionC_ZM'

#load the coordinates of the vertices into a dictionary and a list of M values
dl = xsec_defs.vertexDictionary(gp, ZMline)
vList = dl[0]
vDict = dl[1]

#set the workspace to the scratch directory
gp.workspace = scratchDir

#all output classes need to be Z-aware
gp.OutputZFlag = 'enabled'

#write all copies out to the SR of the cross section line
desc = gp.describe(ZMline)
gp.OutputCoordinateSystem = desc.SpatialReference

for layer in featList:
    gp.AddMessage('Assigning 3D coordinates to %s' % layer)
    baseName = os.path.basename(layer)
    layCopy = os.path.join(scratchDir, baseName + '_copy')
    
    #make a copy in the scratch directory so that we can edit the geometries
    #of the features
    gp.CopyFeatures(layer, layCopy)
    
    #find out what kind of features we're dealing with
    shpType = gp.describe(layer).ShapeType
    
    #special case of point feature type (fewer nested loops for the parts > vertices)
    #and we can edit the geometry directly
    if shpType == 'Point':
        #open an update cursor on the copy
        rows = gp.UpdateCursor(layCopy)
        row = rows.next()
        
        while row:
            #get the geometry of this point
            feat = row.Shape
            pnt = feat.GetPart()
            
            #get the XY of this point based on the M value
            xDistance = pnt.x
            newXY = xsec_defs.lerpXY(gp, xDistance, vList, vDict)
            newPnt = gp.CreateObject('Point')
            
            #gp.AddMessage('old :' + str(pnt.x) + ', ' + str(pnt.y))
            #gp.AddMessage('new :' + str(newPnt[0]) + ', ' + str(newPnt[1]) + ', ' + str(pnt.y / float(ve)))
            
            #write the coordinates to the new point
            newPnt.x = newXY[0]
            newPnt.y = newXY[1]
            newPnt.z = (pnt.y / float(ve))
            
            #update the row's shape
            row.shape = newPnt
            rows.UpdateRow(row)
            row = rows.next()
            
    else: #we're dealing with lines or polygons which are not so easy to edit
        #the geometries of
        idl = []
        
        #open a search cursor
        rows = gp.SearchCursor(layCopy)
        row = rows.next()
        
        #open a text file to start writing coordinates to
        xyzFile = os.path.join(scratchFolder, baseName + '_xyz.txt')
        gp.AddMessage('Writing XYZ coordinates to %s' % xyzFile)
        
        outF = open(xyzFile, 'w')
        
        #start looping through the features
        while row:
            #get the shape of each feature
            feat = row.Shape
            
            #write the object id to the file
            idl.append(row.objectid)
            outF.write(str(row.objectid) + '\n')
            
            #this might be a multipart feature
            #if there is only one part, the next loop is only visited once
            partnum = 0
            partcount = feat.partCount
            
            while partnum < partcount:
                #put the points of this part into an array
                part = feat.getPart(partnum)

                #get each vertex
                pnt = part.next()
                pntcount = 0

                while pnt:
                    #get the XY of this point from the vertex dictionary based on the M value
                    xDistance = pnt.x
                    newXY = xsec_defs.lerpXY(gp, xDistance, vList, vDict)
                    
                    #if we can get valid coordinates from lerpXY
                    if not newXY[0] == 9999:
                        outF.write(str(newXY[0]) + ' ' + str(newXY[1]) + ' ' + str(pnt.y / float(ve)) + '\n')
                    else:
                        gp.AddMessage('9999 exception with ' + str(row.OBJECTID) + ' : ' + str(pnt.x))
                        
                    #otherwise just go on to the next point
                    pnt = part.next()
                    
                #put the array of vertices into the row array
                partnum += 1
            
            #update the row's shape
            outF.write('END\n')
            row = rows.next()
            
    outF.write('END')
    outF.close
    
    #the del statement below is somehow critical to finishing the writing of the
    #file. During development, until I added that, all but the last two polygons 
    #would get created when I ran the text file through the ascii 3d tool.
    del outF
    
    #run the text file through ASCII 3D to Feature tool
    threeDFC = baseName + '_noAtts'
    gp.AddMessage('Using %s in ASCII 3D to Features Tool' % xyzFile)
    gp.AddMessage(shpType)
    xsec_defs.XYZfile2features(gp, xyzFile, threeDFC, shpType)

    #join the attributes to the output file
    outName = baseName + '_3D'
    fInfo = 'ID ID HIDDEN;OBJECTID OBJECTID HIDDEN;OBJECTID_12 OBJECTID_12 HIDDEN;OBJECTID_1 OBJECTID_1 HIDDEN'
    xsec_defs.transferAtts(gp, threeDFC, layCopy, 'ID', 'OBJECTID', fInfo, outName)
    
    #copy the final fc from the scratch gdb to the output directory/gdb
    gp.AddMessage('Copying %s to %s' % (outName, outDir))
    srcFC = os.path.join(scratchDir, outName)
    gp.workspace = outDir
    gp.CopyFeatures(srcFC, outName)
    
xsec_defs.cleanup(gp, keepf, scratchDir)

if keepf == 'false':
    for fname in os.listdir(scratchFolder):
        if '_xyx.txt' in fname:
            os.remove(scratchFolder)

#raise SystemError


## #extra code
    ## elif shpType == 'Polyline':
        ## #need nested loops to visit each feature > part > vertex
        ## while row:
            ## #get the shape of each feature
            ## feat = row.Shape
            
            ## #create a new empty array to hold the vertices of this feature
            ## rowArray = gp.CreateObject('Array')
            
            ## #this might be a multipart feature
            ## #if there is only one part, the next loop is only visited once
            ## partnum = 0
            ## partcount = feat.partCount
            
            ## #dead vertical lines cannot be converted to 3D
            ## #one way to deal with this to very slightly offset each vertex from
            ## #the previous one
            ## offset = .001
            ## while partnum < partcount:
                ## #put the points of this part into an array
                ## part = feat.getPart(partnum)

                ## #create an empty array to hold the vertices of this part
                ## partArray = gp.CreateObject('Array')

                ## #get each vertex
                ## pnt = part.next()
                ## pntcount = 0

                ## while pnt:
                    ## #get the XY of this point from the vertex dictionary based on the M value
                    ## xDistance = pnt.x
                    ## newXY = xsec_defs.lerpXY(gp, xDistance, vList, vDict)
                    
                    ## offset = offset * -1
                    ## #if we can get valid coordinates from lerpXY
                    ## if not newXY[0] == 9999:
                        ## #create a new empty point to hold the new coordinates
                        ## newPnt = gp.CreateObject('Point')
                        ## newPnt.x = newXY[0] + offset
                        ## newPnt.y = newXY[1] + offset
                        ## newPnt.z = (pnt.y / float(ve))
                            
                        ## #put this point into the array
                        ## partArray.add(newPnt)
                    
                    ## #otherwise just go on to the next point
                    ## pnt = part.next()
                    
                ## #put the array of vertices into the row array
                ## rowArray.add(partArray)
                ## partnum += 1
            
            ## #update the row's shape
            ## row.shape = rowArray
            ## rows.UpdateRow(row)
            ## row = rows.next()
