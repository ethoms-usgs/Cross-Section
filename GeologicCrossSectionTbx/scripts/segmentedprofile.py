'''segmentedprofile.py
Description: ArcToolbox tool to create a geologic cross-section template, that is,
    a surface profile made up of contiguous lines that represent the intersection
    of a line of cross section with a layer of geologic map unit polygons displayed
    in cross-section view.
Requirements: 3D Analyst extension

Author: Evan Thoms, U.S. Geological Survey, ethoms@usgs.gov
Date: 7/10/07
Edits beginning: 6/7/10

Upgrades to 10.1 beginning 6/5/13, primarily removing references to xsecdefs
'''

import sys
import os
import traceback
import arcpy


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
        if len(arcpy.ListFields(layer, field)) == 0:
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


def createEventTable(features, zmLine, rkey, buff, eventTable, rProps):
    #builds event table of points located along a line route
    try:
        arcpy.AddMessage('Locating ' + features + ' on ' + zmLine)
        arcpy.LocateFeaturesAlongRoutes_lr(features, zmLine, rkey, buff, eventTable, rProps, 'FIRST', 'NO_DISTANCE', 'NO_ZERO')
        #return eventTable
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError

def placeEvents(inRoutes, idRteFld, eventTable, eventRteFld, fromVar, toVar, eventLay):
    #place events along routes, creates a temporary layer
    try:
		arcpy.AddMessage('Placing line events on ' + inRoutes)
		props = eventRteFld + ' LINE ' + fromVar + ' ' + toVar

		#this makes an event layer where the table includes all records even if they were not located
		#on any routes
		arcpy.MakeRouteEventLayer_lr(inRoutes, idRteFld, eventTable, props, 'lyr')
		arcpy.AddMessage(eventTable + ' written to temporary memory')

		#one way to select only events that were located on a valid route is to
		#save the layer to a feature class,
		arcpy.CopyFeatures_management('lyr', 'lyr2')

		#...create an in-memory layer based on that feature class and limited to where
		#Shape_Length <> 0,
		arcpy.MakeFeatureLayer_management('lyr2', 'lyr3', "Shape_Length <> 0")

		#make a new selection
		#arcpy.SelectLayerByAttribute_management('lyr2', "NEW_SELECTION", "Shape_Length <> 0")

		arcpy.AddMessage('Saving temp layer to permanent memory')

		#...and copy to the output feature class
		arcpy.CopyFeatures_management('lyr3', eventLay)
		arcpy.AddMessage(eventLay + ' written to ' + arcpy.env.scratchWorkspace)

    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError

def plan2side(zmLines, ve):
    #flip map view lines to cross section view without creating a copy
    #this function updates the existing geometry
    arcpy.AddMessage('Flipping ' + zmLines + ' from map view to cross-section view')
    try:
        rows = arcpy.UpdateCursor(zmLines)
        n = 0
        for row in rows:
            # Create the geometry object
            feat = row.shape
            new_Feat_Shape = arcpy.Array()
            a = 0
            while a < feat.partCount:
                # Get each part of the geometry)
                array = feat.getPart(a)
                newarray = arcpy.Array()

                # otherwise get the first point in the array of points
                pnt = array.next()

                while pnt:
                    pnt.X = float(pnt.M)
                    pnt.Y = float(pnt.Z) * float(ve)

                    #Add the modified point into the new array
                    newarray.add(pnt)
                    pnt = array.next()

                #Put the new array into the new feature  shape
                new_Feat_Shape.add(newarray)
                a = a + 1

            #Update the row object's shape
            row.shape = new_Feat_Shape

            #Update the feature's information in the workspace using the cursor
            rows.updateRow(row)
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError

# PARAMETERS
# *******************************************************
# Cross section(s) layer
lineLayer = arcpy.GetParameterAsText(0)
#in a map, the layer might be nested within a group or more than one group
#for naming intermediate files, we want the last term in the group\group\<etc>\layer string
#and we want the path to the source file
if lineLayer.find('\\') > -1:
    r = lineLayer.split('\\')
    line_layer_name = r[len(r)-1]
else:
    line_layer_name = lineLayer
    
d = arcpy.Describe(lineLayer)
line_layer_path = d.catalogPath


#can't figure out how to put this in the validator class ??
result = arcpy.GetCount_management(lineLayer)
if int(result.getOutput(0)) > 1:
    arcpy.AddError(lineLayer + ' has more than one line in it.')
    raise SystemError

# elevation raster layer
dem = arcpy.GetParameterAsText(1)

#coordinate priority
cp = getCPValue(arcpy.GetParameterAsText(2))

# Geology polygon layer
polyLayer = arcpy.GetParameterAsText(3)
if polyLayer.find('\\') > -1:
    r = polyLayer.split('\\')
    poly_layer_name = r[len(r)-1]
else:
    poly_layer_name = polyLayer
    
d = arcpy.Describe(polyLayer)
poly_layer_path = d.catalogPath

# vertical exaggeration
ve = arcpy.GetParameterAsText(4)

# output directory
outFC = arcpy.GetParameterAsText(5)
outName = os.path.splitext(os.path.basename(outFC))[0]

#append features boolean
append = arcpy.GetParameterAsText(6)

#append to feature class...
appendFC = arcpy.GetParameterAsText(7)
if append:
    outName = os.path.splitext(os.path.basename(appendFC))[0]

#data frame name
dfName = arcpy.GetParameterAsText(8)

#BEGIN
#*******************************************************
try:
    #Check for the 3d Analyst extension
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
    arcpy.AddMessage(scratchDir)

    #add an ORIG_FID field to the table that consists of values from the OID
    desc = arcpy.Describe(lineLayer)
    idField = desc.OIDFieldName
    addAndCalc(lineLayer, 'ORIG_FID', '[' + idField + ']')

    #it's necessary to interpolate the line so that a new feature is created in
    #the scratch gdb which has a length in the units of the SR of the dem.
    #interpolate the line to add z values
    zLine = line_layer_name + '_z'
    arcpy.AddMessage('Getting elevation values for the cross-section in ' + lineLayer)
    arcpy.InterpolateShape_3d(dem, lineLayer, zLine)

    #measure it and turn it into a route
    zmLine = line_layer_name + '_zm'
    arcpy.AddMessage('Measuring the length of the line in ' + zLine)
    arcpy.CreateRoutes_lr(zLine, 'ORIG_FID', zmLine, 'LENGTH', '#', '#', cp)

    #intersect with geology layer
    eventTable = poly_layer_name + '_polyEvents'
    rProps = 'rkey LINE FromM ToM'
    arcpy.AddMessage('Locating ' + polyLayer + ' on ' + zmLine)
    arcpy.LocateFeaturesAlongRoutes_lr(polyLayer, zmLine, 'ORIG_FID', '#', eventTable, rProps, 'FIRST', 'NO_DISTANCE', 'NO_ZERO')

    #place line events on interpolated route
    locatedEvents = polyLayer + '_located'
    placeEvents(zmLine, 'ORIG_FID', eventTable, 'rkey', 'FromM', 'ToM', locatedEvents)

    #flip the surface profile events
    #create an empty container for the features that has no spatial reference
    zmProfiles = outName + '_profiles'
    arcpy.AddMessage(scratchDir)
    arcpy.AddMessage(zmProfiles)
    arcpy.CreateFeatureclass_management(scratchDir, zmProfiles, 'POLYLINE', locatedEvents, 'ENABLED', 'ENABLED')

    #append the features from locatedEvents (map view) to locatedEvents2 (unknown SR)
    arcpy.Append_management(locatedEvents, zmProfiles)

    #flip the lines, swapping M for X and Z for Y
    plan2side(zmProfiles, ve)

    #some cleanup
    #comment out the next two lines for troubleshooting
    for fld in ['rkey', 'FromM', 'ToM']:
        arcpy.DeleteField_management(zmProfiles, fld)
    arcpy.DeleteField_management(lineLayer, 'ORIG_FID')

    #now, to worry about the output
    #check to see if we are to append the features to an existing fc
    if append == 'true':
        arcpy.AddMessage('Appending features to ' + appendFC)
        arcpy.Append_management(zmProfiles, appendFC)
        outLayer = appendFC
    else:
        #or copy the final fc from the scratch gdb to the output directory/gdb
        arcpy.AddMessage('Writing ' + outFC)
        srcProfiles = os.path.join(scratchDir, zmProfiles)
        arcpy.CopyFeatures_management(srcProfiles, outFC)
        outLayer = outFC

    #add the layer to the map if a data frame was chosen
    if not dfName == '':
        mxd = arcpy.mapping.MapDocument('Current')
        df = arcpy.mapping.ListDataFrames(mxd, dfName)[0]
        mxd.activeView = df
        arcpy.SetParameterAsText(9, outLayer)

except:
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
    arcpy.AddError(pymsg)
    raise SystemError

