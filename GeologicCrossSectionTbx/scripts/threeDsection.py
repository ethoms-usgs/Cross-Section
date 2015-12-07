'''threeDsection.py
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

Edits beginning 7/31/13 to upgrade to 10.1 and eliminate references to xsecdefs
'''

import os
import sys
import arcpy
import traceback
import xsec_defs
import bisect

# FUNCTIONS
# *******************************************************
def checkExtensions():
    #Check for the 3d Analyst extension
    try:
        if arcpy.CheckExtension('3D') == 'Available':
            arcpy.CheckOutExtension('3D')
        else:
            raise 'LicenseError'

    except 'LicenseError':
        arcpy.AddMessage('3D Analyst extension is unavailable')
        raise SystemError
    except:
        print arcpy.GetMessages(2)

def getCPValue(quadrant):
    cpDict = {'northwest':'UPPER_LEFT', 'southwest':'LOWER_LEFT', 'northeast':'UPPER_RIGHT', 'southeast':'LOWER_RIGHT'}

    return cpDict[quadrant]

def addAndCalc(layer, field, calc):
    #adds a field to a table (layer) of name (field), and calcs a value
    #created as means to add an rkey value to line layers that consist
    #of OID values
    try:
        #add a key field if it doesn't already exist
        if len(arcpy.ListFields(layer, field)) ==0:
            arcpy.AddField_management(layer, field, 'LONG')

		#calculate the id value over to the new value so we always have it in the table
		#as it goes through it's various transformations, some of which will re-write
		#the id field.
        arcpy.CalculateField_management(layer, field, calc)

    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError
    finally:
        arcpy.RefreshCatalog

def addZ(ZptLayer):
    #adds the z value to the table so that it is in the event table when we locate
    #points along the line route
	try:
		arcpy.DeleteField_management(ZptLayers, 'DEM_Z')
	except:
		pass

	try:
		arcpy.AddField_management(ZptLayer, 'DEM_Z', 'DOUBLE')
		rows = arcpy.UpdateCursor(ZptLayer)
		for row in rows:
			# create the geometry object
			feat = row.Shape
			pnt = feat.getPart(0)
			# set the value
			row.setValue('DEM_Z', pnt.Z)
			# update the row
			rows.updateRow(row)

	except:
		tb = sys.exc_info()[2]
		tbinfo = traceback.format_tb(tb)[0]
		pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
		arcpy.AddError(pymsg)
		raise SystemError

def vertexDictionary(ZMline):
    #creates a dictionary of the geometry
    #values of each vertex in an interpolated and measured
    #line. Also creates a list of just the elevations
    try:
        #create the collection containers
        vDict = {}
        vList = []

        #create search cursor
        wkt = arcpy.da.SearchCursor(ZMline, ["SHAPE@WKT"]).next()[0]
        wkt = wkt[wkt.find("((") + 2: wkt.find("))")]
        vtxList = wkt.split(", ")
        for vtx in vtxList:
            valList = vtx.split(" ")
            x = float(valList[0])
            y = float(valList[1])
            m = float(valList[3])
            vDict[m] = (x, y)
            vList.append(m)
			
        #for k in vDict.keys():
        #    arcpy.AddMessage("{}, {}".format(k, vDict[k]))
        #sort the list numerically so we know we are evaluating m values
        #from min to max
        vList.sort()

        return vList, vDict

    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError
    
def lerpXY(distance, vList, vDict):
    #lerp, apparently, is a verb meaning 'to perform a linear interpolation'
    #Use the very handy bisect module to find where the distance (as reported
    #by the X coordinate in cross section view) would be inserted in the
    #sorted M values list.
    #arcpy.AddMessage("{}, {}".format(distance, min(vList)))
    try:
        #if our distance value is smaller than the M value at the beginning
        #of the line, use the smallest M value as the key for the dictionary
        #and use the XY of that entry, no interpolation
        if distance <= min(vList):
            #arcpy.AddMessage("{}, {}".format(distance, min(vList)))
            #arcpy.AddMessage(1)
            key = min(vList)
            newX = vDict[key][0]
            newY = vDict[key][1]

        #if our distance value is larger than the M value at the end of the line
        #use the largest M value of the key for the dictionary and use the XY
        #of that entry, no interpolation
        elif distance >= max(vList):
            #arcpy.AddMessage(2)
            key = max(vList)
            newX = vDict[key][0]
            newY = vDict[key][1]

        #otherwise, find the bracketing M-value pair for our distance and
        #interpolate the XY coordinates
        else:
            #bisect returns the index
            #arcpy.AddMessage('trying')
            #arcpy.AddMessage(3)
            insertN = bisect.bisect_right(vList, distance)

            floor = vList[insertN - 1]
            ceiling = vList[insertN]

            floorX = vDict[floor][0]
            floorY = vDict[floor][1]
            ceilingX = vDict[ceiling][0]
            ceilingY = vDict[ceiling][1]

            vFactor = (distance - floor) / (ceiling - floor)

            newX = floorX + (vFactor * (ceilingX - floorX))
            newY = floorY + (vFactor * (ceilingY - floorY))

    except:
        #if the try block fails, skip the point
        newX = 9999
        newY = 9999

    return newX, newY

def returnParentFolder(path):
     desc = arcpy.Describe(path)
     while not desc.datatype == 'Folder':
         path = os.path.dirname(path)
         desc = arcpy.Describe(path)

     return path

def XYZfile2features(xyzFile, threeDFC, shpType):
    #arcpy.AddMessage(xyzFile + ', ' + 'GENERATE' + ', ' + threeDFC + ', ' + shpType)
    try:
        arcpy.ASCII3DToFeatureClass_3d(xyzFile, 'GENERATE', threeDFC, 'POLYGON') #, '#', '#', '#', '#', 'DECIMAL_POINT')

    except:
        # get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)

        raise SystemError
    
def transferAtts(inFC, joinTable, parentKey, childKey, fInfo, outName):
    try:
        #transfers attributes from a table to a fc: OIDs must match!
        #get the attributes through a join which only works on a feature layer
        lName = 'lay'
        layer = arcpy.MakeFeatureLayer_management(inFC, lName)[0]
        
        #before the join, set the QualifiedFieldNames environment setting so that
        #we don't see the source table name as a prefix in the field names
        arcpy.env.qualifiedFieldNames = False
        
        #make the join based on key field
        arcpy.AddJoin_management(lName, parentKey, joinTable, childKey)
        
        #copy features out to the output name
        arcpy.CopyFeatures_management(lName, outName)
        
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError

# PARAMETERS
# *******************************************************
# Cross section layer, use this as a reference to the feature layer
xsecLayer = arcpy.GetParameterAsText(0)
xsecLayer = arcpy.Describe(xsecLayer).featureClass.name

#use this as the basename for intermediate files (because lineLayer may 
#have slashes in the name/path)
xsecName = arcpy.Describe(xsecLayer).featureClass.name 

#can't figure out how to put this in the validator class ??
result = arcpy.GetCount_management(xsecLayer)
if int(result.getOutput(0)) > 1:
    arcpy.AddError(xsecLayer + ' has more than one line in it.')
    
# elevation raster layer
dem = arcpy.GetParameterAsText(1)

#coordinate priority - corner from which the measuring will begin
cp = getCPValue(arcpy.GetParameterAsText(2))

#intersecting lines layer
#featList = arcpy.GetParameter(4)
featList = arcpy.GetParameterAsText(3).split(";")

# vertical exaggeration
ve = arcpy.GetParameterAsText(4)

# output directory
outDir = arcpy.GetParameterAsText(5)


#BEGIN
#*******************************************************
try:  
    #check for 3DAnalyst extension
    checkExtensions()

##Bug at 10.1 makes it impossible to check for a schema lock
##http://support.esri.com/fr/knowledgebase/techarticles/detail/40911
##During testing of this section, all calls to arcpy.TestSchemaLock resulted in False
##    #try to get a schema lock
##    if not arcpy.TestSchemaLock(linesLayer):
##        arcpy.AddMessage("Cannot acquire a schema lock on " + linesLayer)
##        raise SystemError

    #environment variables
    arcpy.env.overwriteOutput = True
    scratchDir = arcpy.env.scratchWorkspace
    arcpy.env.workspace = scratchDir
    
    #add an rkey field to the table that consists of values from the OID
    desc = arcpy.Describe(xsecLayer)
    idField = desc.OIDFieldName
    addAndCalc(xsecLayer, 'ORIG_FID', '[' + idField + ']')

    #interpolate the line to add z values
    #despite the documentation for InterpolateShape, the function may not deal
    #appropriately with spatial references that differ between the features and the surface
    #particularly if one is UTM and one is state plane in feet
    #the user may have to re-project the surface to the same as the features
    #should this be a fatal error with a warning?
    zLine = xsecName + '_z'
    arcpy.AddMessage('Getting elevation values for cross-section line in ' + xsecLayer)
    arcpy.InterpolateShape_3d(dem, xsecLayer, zLine)
    arcpy.AddMessage('    ' + zLine + ' written to ' + scratchDir)

    #measure the line
    zmLine = xsecName + '_zm'
    arcpy.AddMessage('Measuring the length of the line in ' + zLine)
    arcpy.CreateRoutes_lr(zLine, 'ORIG_FID', zmLine, 'LENGTH', '#', '#', cp)
    arcpy.AddMessage('    ' + zmLine + ' written to ' + scratchDir)

    #load the coordinates of the vertices into a dictionary and a list of M values
    dl = vertexDictionary(zmLine)
    vList = dl[0]
    vDict = dl[1]
    
    #all output classes need to be Z-aware
    arcpy.env.outputZFlag = 'Enabled'
    
    #write all copies out to the SR of the cross section line
    desc = arcpy.Describe(zmLine)
    arcpy.OutputCoordinateSystem = desc.SpatialReference

    for layer in featList:
        arcpy.AddMessage('Converting %s to 3D features' % layer)
        baseName = os.path.basename(layer)
        layCopy = os.path.join(scratchDir, baseName + '_copy')
        
        #make a copy in the scratch directory so that we can edit the geometries
        #of the features
        arcpy.CopyFeatures_management(layer, layCopy)
        
        #find out what kind of features we're dealing with
        shpType = arcpy.Describe(layer).ShapeType
        
        #special case of point feature type (fewer nested loops for the parts > vertices)
        #and we can edit the geometry directly
        if shpType == 'Point':
            #open an update cursor on the copy
            rows = arcpy.da.UpdateCursor(layCopy, ["SHAPE@XY", "SHAPE@Z"])
            
            for row in rows:
                #get the geometry of this point
                oldXY = row[0]
                oldX = oldXY[0]
                oldY = oldXY[1]
                
                #get the XY of this point based on the M value
                xDistance = oldX
                newXY = lerpXY(xDistance, vList, vDict)
                newX = newXY[0]
                newY = newXY[1]
                newPnt = arcpy.CreateObject('Point')
                
                arcpy.AddMessage('old :' + str(oldX) + ', ' + str(oldY))
                arcpy.AddMessage('new :' + str(newXY[0]) + ', ' + str(newXY[1]) + ', ' + str(oldY / float(ve)))
                
                #write the coordinates to the new point
                #newX = newXY[0]
                #newY = newXY[1]
                newZ = (oldY / float(ve))
                
                #update the row's shape
                row[0] = [newX, newY]
                row[1] = newZ
                rows.updateRow(row)
                
        else: #we're dealing with lines or polygons which are not so easy to edit
            #get the parent folder of the scratch directory, might be a folder
            #itself.
            scratchFolder = returnParentFolder(scratchDir)
            
            #open a text file to start writing coordinates to
            xyzFile = os.path.join(scratchFolder, baseName + '_xyz.txt')
            arcpy.AddMessage('Writing XYZ coordinates to %s' % xyzFile)
            outF = open(xyzFile, 'w')
			
			#ID list
            idl = []
            
            #open a search cursor
            rows = arcpy.da.SearchCursor(layCopy, ["OID@", "SHAPE@"])
            
            #start looping through the features
            for row in rows:
                #write the object id to the file
                idl.append(row[0])
                outF.write(str(row[0]) + '\n')
                arcpy.AddMessage("OBJECTID {}".format(row[0]))
				
                #get the shape of each feature
                feat = row[1]
                              
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
                        xDistance = pnt.X
                        newXY = lerpXY(xDistance, vList, vDict)
                        
                        #if we can get valid coordinates from lerpXY
                        if not newXY[0] == 9999:
                            outF.write(str(newXY[0]) + ' ' + str(newXY[1]) + ' ' + str(pnt.Y / float(ve)) + '\n')
                        else:
                            arcpy.AddMessage('9999 exception with ' + str(row[0]) + ' : ' + str(pnt.X))
                            
                        #otherwise just go on to the next point
                        pnt = part.next()
                        
                    #put the array of vertices into the row array
                    partnum += 1
                
                #update the row's shape
                outF.write('END\n')

            outF.write('END')
            outF.close
    
            #the del statement below is somehow critical to finishing the writing of the
            #file. During development, until I added that, all but the last two polygons 
            #would get created when I ran the text file through the ascii 3d tool.
            del outF
                
            #run the text file through ASCII 3D to Feature tool
            threeDFC = baseName + '_noAtts'
            arcpy.AddMessage('Using %s in ASCII 3D to Features Tool' % xyzFile)
            XYZfile2features(xyzFile, threeDFC, shpType)
            
            #join the attributes to the output file
            outName = baseName + '_3D'
            fInfo = 'ID ID HIDDEN;OBJECTID OBJECTID HIDDEN;OBJECTID_12 OBJECTID_12 HIDDEN;OBJECTID_1 OBJECTID_1 HIDDEN'
            transferAtts(threeDFC, layCopy, 'ID', 'OBJECTID', fInfo, outName)
                
            #copy the final fc from the scratch gdb to the output directory/gdb
            arcpy.AddMessage('Copying %s to %s' % (outName, outDir))
            srcFC = os.path.join(scratchDir, outName)
            arcpy.workspace = outDir
            outPath = os.path.join(outDir, outName)			
            arcpy.CopyFeatures_management(srcFC, outPath)

        #raise SystemError   
except:
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
    arcpy.AddError(pymsg)
    raise SystemError