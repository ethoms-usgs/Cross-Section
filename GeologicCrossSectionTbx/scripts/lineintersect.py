'''lineintersect.py
Description: ArcToolbox tool to find the intersections between a line of
    cross section and all of the lines in a line layer crossing it and plot
    those locations in cross section view.
Requirements: 3D Analyst extension
Author: Evan Thoms, U.S. Geological Survey, ethoms@usgs.gov
Date: 6/29/10

Upgrades to ArcGIS 10 started 7/13/11

Upgrades to ArcGIS 10.1 started 6/5/13
primarily removing xsecdefs

Edits 5/30/18
'''

# Import modules
import os
import sys
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
    '''adds a field to a table (layer) of name (field), and calcs a value
    created as means to add an rkey value to line layers that consist
    of OID values'''
    try:
        #add a key field if it doesn't already exist
        if len(arcpy.ListFields(layer, field)) ==0:
            arcpy.AddField_management(layer, field, 'LONG')

		#calculate the id value over to the new value so we always have it in the table
		#as it goes through it's various transformations, some of which will re-write
		#the id field.
        arcpy.CalculateField_management(layer, field, calc)

    except:
        arcpy.AddError(traceback.format_exc())
        raise SystemError
    finally:
        arcpy.RefreshCatalog

def xsecLines(outFC, ZinterPts, eventTable, ZField):
    '''shows the intersections between the cross-section line and other lines
    in map view as lines in cross-section view'''
    try:
        # create an empty output featureclass with the fields of the event table
    	arcpy.CreateFeatureclass_management(scratchDir, outFC, 'POLYLINE', ZinterPts, 'ENABLED', 'ENABLED')

        # open search cursor on the event table
        tRows = arcpy.SearchCursor(eventTable)

        # open insert cursor on the output layer
    	cur = arcpy.InsertCursor(outFC)

        # create point and array objects
        pnt1 = arcpy.CreateObject('Point')
        pnt2 = arcpy.CreateObject('Point')
        array = arcpy.CreateObject('Array')

        arcpy.AddMessage('Building intersecting lines in cross-section view...')

        #get a list of fields in the template table that does not include OBJECTID or FID or SHAPE
        #anything else? add it to xf! ("excluded fields")
        xf = ['shape', 'objectid', 'fid', 'shape_length']
        lf = arcpy.ListFields(ZinterPts)
        names = []
        for f in lf:
            if not f.name.lower() in xf:
                names.append(f.name)

        #enter while loop for each row in events table
        for tRow in tRows:
            #set the line's start coordinates
            #set Y1 equal = DEM_Z value * the ve
            try:
                pnt1.Y = float(tRow.getValue(ZField)) * float(ve)
            except:
                arcpy.AddMessage('No elevation for feature ' + str(tRow.getValue('OBJECTID')))
                arcpy.AddMessage('Using a value of ' + str(100 * float(ve)) + ' for elevation')
                pnt1.Y = 100 * float(ve)

            pnt1.X = tRow.RouteM
            pnt2.X = pnt1.X
            #set Y2 to the surface elevation + 500 map units (* ve)
            pnt2.Y = pnt1.Y + (500 * float(ve))
            #pnt2.Y = pnt1.Y + 550

            #add points to array
            array.add(pnt1)
            array.add(pnt2)

            #set array to the new feature's shape
            row = cur.newRow()
            row.shape = array

            #copy over the other attributes
            for name in names:
                row.setValue(name, tRow.getValue(name))

            #insert the feature
            cur.insertRow(row)

            #cleanup
            array.removeAll()

    except:
        arcpy.AddError(traceback.format_exc())
        raise SystemError

def xsecPoints(outFC, Zpts, eventTable, ZField):
    '''shows the intersections between the cross-section line and other lines
    in map view as points in cross-section view'''
    try:
        # create the output featureclass
        arcpy.CreateFeatureclass_management(scratchDir, outFC, 'POINT', Zpts, 'ENABLED', 'ENABLED')

        # open search cursor on the event table
        tRows = arcpy.SearchCursor(eventTable)

        # open insert cursor on the output layer
        cur = arcpy.InsertCursor(outFC)

        arcpy.AddMessage('Building points in cross-section view...')

        #get a list of fields in the template table that does not include OBJECTID or FID or SHAPE
        #anything else? add it to xf! ("excluded fields")
        xf = ('shape', 'objectid', 'fid', 'shape_length')
        lf = arcpy.ListFields(Zpts)
        names = []
        for f in lf:
            if not f.name.lower() in xf:
                names.append(f.name)

        for tRow in tRows:
    	    #create point and array objects
    	    pnt = arcpy.CreateObject('Point')
            try:
                pnt.Y = float(tRow.getValue(ZField)) * float(ve)
            except:
                arcpy.AddMessage('    No elevation for feature ' + str(tRow.getValue('OBJECTID')))
                arcpy.AddMessage('      Using a value of 0 for elevation')
                pnt.Y = 0

    		#set the point's X and Y coordinates
            pnt.X = float(tRow.getValue('RouteM'))

    		#set the point to the new feature's shape
            row = cur.newRow()
            row.shape = pnt

    		#copy over the other attributes
            for name in names:
    		    row.setValue(name, tRow.getValue(name))

    		#insert the feature
            cur.insertRow(row)

    except:
        arcpy.AddError(traceback.format_exc())
		raise SystemError

def transferAtts(inFC, joinTable, parentKey, childKey, outName):
    '''transfers attributes from a table to a fc: OIDs must match!
    get the attributes through a join which only works on a feature layer'''
    try:
        lName = 'lay'
        layer = arcpy.MakeFeatureLayer_management(inFC, lName)[0]

        #before the join, set the QualifiedFieldNames environment setting so that
        #we don't see the source table name as a prefix in the field names
        qualBool = arcpy.env.qualifiedFieldNames
        arcpy.env.qualifiedFieldNames = False

        #make the join based on key field
        arcpy.AddJoin_management(lName, parentKey, joinTable, childKey)

        #copy features out to the output name
        arcpy.CopyFeatures_management(lName, outName)

        #set the qualifiedFieldNames environment back to what it was
        arcpy.env.qualifiedFieldNames = qualBool

        #get a list of fields in linesLayer
        lineFlds = []
        for foo in arcpy.ListFields(linesLayer):
            lineFlds.append(foo.name)
        #and delete all others from the output here
        for fld in arcpy.ListFields(outName):
            if fld.name not in lineFlds:
                try:
                    arcpy.DeleteField_management(outName, fld.name)
                except:
                    pass

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

#use this as the basename for intermediate files (because lineLayer may 
#have slashes in the name/path)
xsecName = arcpy.Describe(xsecLayer).name
# and might be a shapefile where the name ends in .shp
xsecName = os.path.split(xsecName)[0]

#might be a path, so we have to get the name of the file
if os.path.isabs(xsecLayer):
    xsecLayer = os.path.splitext(os.path.basename(xsecLayer))[0]

#can't figure out how to put this in the validator class ??
result = arcpy.GetCount_management(xsecLayer)
if int(result.getOutput(0)) > 1:
    arcpy.AddError(xsecLayer + ' has more than one line in it.')

# elevation raster layer
dem = arcpy.GetParameterAsText(1)

#coordinate priority - corner from which the measuring will begin
cp = getCPValue(arcpy.GetParameterAsText(2))

#intersecting lines layer
linesLayer = arcpy.GetParameterAsText(3)

#output features to be points or lines?
outShape = arcpy.GetParameterAsText(4)

# vertical exaggeration
ve = arcpy.GetParameterAsText(5)

# output feature class
outFC = arcpy.GetParameterAsText(6)
outName = os.path.splitext(os.path.basename(outFC))[0]

#append to existing feature class?
append = arcpy.GetParameterAsText(7)

#append target
appendFC = arcpy.GetParameterAsText(8)
if append == 'true':
	outName = os.path.splitext(os.path.basename(appendFC))[0]

#data frame name
dfName = arcpy.GetParameterAsText(9)

#BEGIN
#*******************************************************
try:
    #is there a better place to put this?
    if outFC == "" and appendFC == "":
        arcpy.AddError("Provide the name of a new feature class or one to which the features will be appended.")
        raise SystemError
    
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

    #measure the cross section line
    mLine = xsecName + '_m'
    arcpy.AddMessage('Measuring the length of the cross section')
    arcpy.CreateRoutes_lr(xsecLayer, 'ORIG_FID', mLine, 'LENGTH', '#', '#', cp)
    arcpy.AddMessage('    ' + mLine + ' written to ' + scratchDir)

    #intersect the cross section with the lines layer
    #creates a table with only the original FIDs of the input features.
    #FID field is named FID_<fcname> so we can find it later to transfer attributes
    #otherwise, we get a ton of fields, which may be redundant if the same feature class
    #(with different selections or definition queries) is being passed for both
    #the cross-section layer and the lines layer, which was the case when I was developing,
    #that is, I was looking for intersections between the main cross-section line and
    #all other cross-sections
    intersectPts = outName + '_interPts'
    inList = linesLayer + ';' + xsecLayer
    arcpy.AddMessage('Intersecting lines in {} with the line of cross-section'.
        format(linesLayer))
    try:
        arcpy.Intersect_analysis(inList, intersectPts, 'ONLY_FID', '#', 'point')
    except:
        arcpy.AddWarning('Intersect process failed!')
        arcpy.AddWarning('You may need to permanently project all layers')
        arcpy.AddWarning('to the same spatial reference.')
    arcpy.AddMessage('    {} written to {}'.format(intersectPts, scratchDir))
    
    #f-ing intersect analysis created multipoints, on which you can't call
    #AddSurfaceInformation
    explode_pts = intersectPts + '_exp'
    arcpy.MultipartToSinglepart_management(intersectPts, explode_pts)

    #get elevations for the intersection locations
    arcpy.AddMessage('Adding elevations from {}'.format(dem))
    arcpy.AddSurfaceInformation_3d(explode_pts, dem, 'Z')
  
    #locate intersection points on measured cross-section
    eventTable = outName + '_interEvents'
    rProps = 'rkey POINT RouteM'
    arcpy.AddMessage('Locating lines in {} on {}'.format(linesLayer, mLine))
    arcpy.LocateFeaturesAlongRoutes_lr(explode_pts, mLine, 'ORIG_FID', '10', 
        eventTable, rProps, 'FIRST', 'NO_DISTANCE', 'NO_ZERO')
    arcpy.AddMessage('    {} written to {}'.format(eventTable, scratchDir))
    
    if outShape == 'lines':
    	xInterFeats = outName + '_xsecLines'
    	xsecLines(xInterFeats, explode_pts, eventTable, 'Z')
    else:
    	xInterFeats = outName + '_xsecPts'
    	xsecPoints(xInterFeats, explode_pts, eventTable, 'Z')
    
    #I think we're done with 'ORIG_FID' here, nuke it
    arcpy.DeleteField_management(xsecLayer, 'ORIG_FID')
    
    #transfer attributes from linesLayer to xInterFeats
    #first, what is the ID field of linesLayer (could be 'OBJECTID' or 'FID')
    descLines = arcpy.Describe(linesLayer)
    linesIDF = descLines.OIDFieldName
    trueName = descLines.name #need the name of the table in the workspace, not the ArcMap layer name
    xInterFeatsAtts = xInterFeats + '_atts'
    #transfer the attributes
    transferAtts(xInterFeats, linesLayer, 'FID_' + trueName , linesIDF, xInterFeatsAtts)

    #now, to worry about the output
    #check to see if we are to append the features to an existing fc
    if append == 'true':
    	arcpy.AddMessage('Appending features to ' + appendFC)
    	arcpy.Append_management(xInterFeatsAtts, appendFC, "NO_TEST")
    	outLayer = appendFC
    else:
    	#or copy the final fc from the scratch gdb to the output directory/gdb
    	arcpy.AddMessage('Writing ' + outFC)
    	srcInterLines = os.path.join(scratchDir, xInterFeatsAtts)
    	arcpy.CopyFeatures_management(srcInterLines, outFC)
    	outLayer = outFC

    #add the layer to the map if a data frame was chosen
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
