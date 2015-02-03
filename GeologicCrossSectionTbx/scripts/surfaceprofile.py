'''
Name: surfaceprofile.py
Description: ArcToolbox tool script to create one or more surface profiles from an ArcMap line layer
    in a  cross sectional view shapefile. Requires a line layer and a DEM in the same
    coordinate system.
Requirements: 3D Analyst extension, CreateRoutes extension is available with all Arc modules
Author: Evan Thoms, U.S. Geological Survey, ethoms@usgs.gov
Date: 8/8/07
mods beginning 5/21/10

updates to ArcGIS 10 beginning 3/18/11

updates to ArcGIS 10.1 beginning 6/5/13
primarily, removing unnecessary parameters, removing references to xsecdefs

'''

import sys
import os
import traceback
import arcpy


# FUNCTIONS
# ***************************************************************
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
    finally:
        arcpy.RefreshCatalog

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


def plan2side(ZMlines, ve):
    #flip map view lines to cross section view without creating a copy
    #this function updates the existing geometry
    arcpy.AddMessage('Flipping ' + ZMlines + ' from map view to  cross section view')
    try:
        rows = arcpy.UpdateCursor(ZMlines)
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
# ***************************************************************
arcpy.env.overwriteOutput = True

#  cross section(s) layer
linesLayer = arcpy.GetParameterAsText(0)

# elevation raster layer
dem = arcpy.GetParameterAsText(1)

#coordinate priority - corner from which the measuring will begin
cp = getCPValue(arcpy.GetParameterAsText(2))

# vertical exaggeration
ve = arcpy.GetParameterAsText(3)

#plot WRT to another line boolean
plotWRT = arcpy.GetParameterAsText(4)

#wrt line feature class
wrtLineFC = arcpy.GetParameterAsText(5)

# output feature class
outFC = arcpy.GetParameterAsText(6)
outName = os.path.splitext(os.path.basename(outFC))[0]

#append features boolean
appendBool = arcpy.GetParameterAsText(7)

#append to feature class...
appendFC = arcpy.GetParameterAsText(8)

#data frame name
dfName = arcpy.GetParameterAsText(9)

# BEGIN
# ***************************************************************
#do we have a place to put this?
try:
    if outFC == "" and appendFC == "":
        arcpy.AddError("Provide the name of a new feature class or one to which the features will be appended.")
        raise SystemError
    
    #check the availability of the 3d Analyst extension
    checkExtensions()
 
#Bug at 10.1 makes it impossible to check for a schema lock
#http://support.esri.com/fr/knowledgebase/techarticles/detail/40911
#During testing of this section, all calls to arcpy.TestSchemaLock resulted in False
#    #try to get a schema lock
##    if not arcpy.TestSchemaLock(linesLayer):
##        arcpy.AddMessage("Cannot acquire a schema lock on " + linesLayer)
##        raise SystemError
#still at 10.2, apparently

    #if wrtLineFC was provided, check for only one line
    if plotWRT == 'true':
        if wrtLineFC <> '':
            #if the 'Single line layer' parameter is not empty first check that the layer contains line
            desFC = arcpy.Describe(wrtLineFC)
            if desFC.shapeType <> 'Polyline':
                arcpy.AddError("Select a line layer for the 'Single line layer' parameter.")
                raise SystemError
            #and then check that there is only one feature in the layer or in the selection
            result = int(arcpy.GetCount_management(wrtLineFC).getOutput(0))
            if result > 1:
                arcpy.AddError("'Single line layer' has more than one line in it or more than one line selected.")
                raise SystemError
            #now select only those profile lines that intersect the the WRT line
            arcpy.SelectLayerByLocation_management(linesLayer, "INTERSECT", wrtLineFC)
        else:
            arcpy.AddError("'Single line layer' parameter is empty.")
            raise SystemError
    
    #environment variables
    arcpy.env.overwriteOutput = True
    scratchDir = arcpy.env.scratchWorkspace
    arcpy.env.workspace = scratchDir

    #add an rkey field to the table that consists of values from the OID
    desc = arcpy.Describe(linesLayer)
    idField = desc.OIDFieldName
    addAndCalc(linesLayer, 'ORIG_FID', '[' + idField + ']')
    
    #interpolate the lines
    zLines = outName + '_z'
    arcpy.AddMessage('Getting elevation values for features in ' + linesLayer)
    arcpy.InterpolateShape_3d(dem, linesLayer, zLines)
    arcpy.AddMessage('    ' + zLines + ' written to ' + arcpy.env.scratchWorkspace)
    
    #measure the lines
    zmLines = outName + '_zm'
    arcpy.AddMessage('Measuring the length of the line(s) in ' + zLines)
    arcpy.CreateRoutes_lr(zLines, 'ORIG_FID', zmLines, 'LENGTH', '#', '#', cp)
    arcpy.AddMessage('    ' + zmLines + ' written to ' + arcpy.env.scratchWorkspace)
    
    #hook the attributes back up
    #transferAtts(inFC, joinTable, parentKey, childKey, fInfo, outName)
    zmAtts = outName + '_zmAtts'
    transferAtts(zmLines, linesLayer, 'ORIG_FID', 'ORIG_FID', '#', zmAtts)

    #make an empty container with an 'Unknown' SR
    zmProfiles = outName + '_profiles'
    arcpy.CreateFeatureclass_management(scratchDir, zmProfiles, 'POLYLINE', linesLayer, 'ENABLED', 'ENABLED')
    arcpy.Append_management(zmAtts, zmProfiles, 'NO_TEST')
    plan2side(zmProfiles, ve)

    #check plotWRT boolean
    if plotWRT == 'true':

        #create points that represent the intersections between the profile lines
        #and the single intersection line
        intersectFC = outName + '_intersectPts'
        arcpy.Intersect_analysis([linesLayer, wrtLineFC], intersectFC, '#', '#', 'POINT')

        #now, locate those points on the profile routes
        #a field called 'mValue' will be created that shows the distance
        #from the beginning of the profile line to the point of intersection
        #the offset required to plot the profile wrt to the intersecting line
        intersectTab = outName + '_intersectTab'
        rProps = 'rkey POINT mValue'
        arcpy.AddMessage('Locating ' + linesLayer + ' on ' + zmLines)
        arcpy.LocateFeaturesAlongRoutes_lr(intersectFC, zmLines, 'ORIG_FID', 1, intersectTab, rProps, 'FIRST', 'NO_DISTANCE', 'NO_ZERO')

        #now update the profiles
        profiles = arcpy.UpdateCursor(zmProfiles)

        maxY = 0
        minY = 0
        for profile in profiles:
            #get the offset for this profile
            #first, get the route key of this profile
            rte = profile.ORIG_FID
            if not rte == None:
                #and create a search cursor of hopefully just one row where the rkeys
                #in the profiles fc and the intersect table are the same
                where = '"rkey" = ' + str(rte)
                #rows = arcpy.SearchCursor(intersectTab, where)
                with arcpy.da.SearchCursor(intersectTab, "mValue", where) as rows:
                    try:
                        #get the offset distance
                        #offset = rows.next().mValue
                        offset = rows.next()[0]
        
                        #create an empty container for the re-calced profile geometry
                        newProf = arcpy.CreateObject('array')
        
                        #get the existing geometry
                        feat = profile.shape
                        part = feat.getPart(0)
        
                        for pnt in part:
                            #recalc each x coordinate and add it to the new array object
                            pnt.X = pnt.X - offset
                            newProf.add(pnt)
        
                            #compare Y values for the min and max of the dataset
                            if pnt.Y > maxY: maxY = pnt.Y
                            if pnt.Y < minY: minY = pnt.Y
        
                        #set the old profile shape to the new and update
                        profile.shape = newProf
                        profiles.updateRow(profile)
                    except:
                        pass 


        #now insert one last vertical line to show the location of intersection
        rows = arcpy.InsertCursor(zmProfiles)
        row = rows.newRow()

        #create some empty geometry objects
        lineArray = arcpy.Array()
        pnt1 = arcpy.Point()
        pnt2 = arcpy.Point()

        #update the properties of the objects
        pnt1.X = 0
        pnt1.Y = (minY - 500.0)
        lineArray.add(pnt1)

        pnt2.X = 0
        pnt2.Y = (maxY + 500.0)
        lineArray.add(pnt2)

        #add the new feature
        row.shape = lineArray
        rows.insertRow(row)

    #some cleanup
    arcpy.DeleteField_management(zmProfiles, 'ORIG_FID')
    arcpy.DeleteField_management(linesLayer, 'ORIG_FID')
    arcpy.SelectLayerByAttribute_management(linesLayer, "CLEAR_SELECTION")
    arcpy.Delete_management("lay")

    #now, to worry about the output
    #check to see if we are to append the features to an existing fc
    if appendBool == 'true':
        arcpy.AddMessage('Appending features to ' + appendFC)
        arcpy.Append_management(zmProfiles, appendFC)
        outLayer = appendFC

    else:
        #or copy the final fc from the scratch gdb to the output directory/gdb
        srcProfiles = os.path.join(scratchDir, zmProfiles)
        arcpy.CopyFeatures_management(srcProfiles, outFC)
        outLayer = outFC

    #now, check for whether the user wants the output in a particular data frame
    #seems to inconsistently activate the data frame
    #layer will not be added unless Geoprocessing > Geoprocessing Options >
    #   'Add results of geoprocessing operations to the display' is checked
    if not dfName == '':
        mxd = arcpy.mapping.MapDocument('Current')
        df = arcpy.mapping.ListDataFrames(mxd, dfName)[0]
        mxd.activeView = df
        arcpy.SetParameterAsText(10, outLayer)

except:
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
    arcpy.AddError(pymsg)
    raise SystemError
