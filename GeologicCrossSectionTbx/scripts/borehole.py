'''
Name: borehole.py
Description: ArcToolbox tool script to plot borehole stick logs
   in a cross-sectional view.
   python version of the borehole part of my
   CrossSection.dll written in VB to access ArcObjects
Requirements: python, 3D Analyst extension
Author: Evan Thoms, U.S. Geological Survey, ethoms@usgs.gov
Date: 7/23/07
Edits beginning on 5/25/10
Upgraded to ArcGIS 10 on 7/7/11

upgrades beginning on 6/6/13, primarily removing references to xsecdefs.py

'''

# Import modules
import os
import sys
import math
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
  
def boreholeLines():
    #creates 2d cross section view sticklogs that show the depth of each borehole
    try:
        # create an empty output featureclass with the fields of the event table
    	arcpy.CreateFeatureclass_management(scratchDir, bhLines, 'POLYLINE', zBoreholes, 'ENABLED', 'ENABLED')
    
        # open search cursor on the event table
    	tRows = arcpy.SearchCursor(eventTable)
    		
        # open insert cursor on the output layer
    	cur = arcpy.InsertCursor(bhLines)
    
        # create point and array objects
    	pnt1 = arcpy.CreateObject('Point')
    	pnt2 = arcpy.CreateObject('Point')
    	array = arcpy.CreateObject('Array')
    	
    	#get a list of fields in the template table that does not include OBJECTID or FID or SHAPE
    	#anything else? add it to xf! ("excluded fields")
    	xf = ('shape', 'objectid', 'fid', 'shape_length')
    	lf = arcpy.ListFields(zBoreholes)
    	names = []
    	for f in lf:
    		if not f.name.lower() in xf:
    			names.append(f.name)
                #we also want the 'DISTANCE' value, calculated when the event table is built
                #to be saved to this fc so it's needs to be in this list
                names.append('distance')
    			
        # enter while loop for each row in events table
        for tRow in tRows:
            # set the point's X and Y coordinates
            # set Y depending on whether the user wants to use the elevation of the
            # borehole from the DEM or from a value in the collar z field
            try:
            	pnt1.Y = float(tRow.getValue(zField)) * float(ve)
            except:
            	arcpy.AddMessage('No collar elevation available for borehole ' + str(tRow.getValue(bhIdField)))
            	arcpy.AddMessage('Using a value of 10000 for collar elevation')
            	pnt1.Y = 10000
                
            pnt1.X = tRow.RouteM
            pnt2.X = pnt1.X
        
            #if there is no value in bhDepthField, subtract 5000 from the top
            #elevation as a way of flagging this point
            try:
            	pnt2.Y = pnt1.Y - (float(tRow.getValue(bhDepthField) * float(ve)))
            except:
            	arcpy.AddMessage('    No borehole depth available for borehole ' + str(tRow.getValue(bhIdField)))
            	arcpy.AddMessage('      Using a value of 5000 for borehole depth.')
            	pnt2.Y = pnt1.Y - 5000
            
            # add points to array
            array.add(pnt1)
            array.add(pnt2)
            
            # set array to the new feature's shape
            row = cur.newRow()
            row.shape = array
            
            # copy over the other attributes
            for name in names:
                #try to write the value, but maybe the field can't be found or the value can't be set
                #for some reason. Don't want the whole thing to blow up
                try:
                    row.setValue(name, tRow.getValue(name))
                except:
                    #if it can't be written, forget about it
                    pass
                    
            # insert the feature
            cur.insertRow(row)
        
            #cleanup
            array.removeAll()
    
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError


# PARAMETERS
# ***************************************************************
# Cross-section layer
lineLayer = arcpy.GetParameterAsText(0)

#might be a path, so we have to get the name of the file
if os.path.isabs(lineLayer):
    lineLayer = os.path.splitext(os.path.basename(lineLayer))[0]

#can't figure out how to put this in the validator class ??
result = arcpy.GetCount_management(lineLayer)
if int(result.getOutput(0)) > 1:
    arcpy.AddError(lineLayer + ' has more than one line in it.')
    raise SystemError

# elevation raster layer
dem = arcpy.GetParameterAsText(1)

#coordinate priority - corner from which the measuring will begin
cp = getCPValue(arcpy.GetParameterAsText(2))

# borehole locations points layer
bhLayer = arcpy.GetParameterAsText(3)

# borehole id field
bhIdField = arcpy.GetParameterAsText(4)

# collar Z field
bhzField = arcpy.GetParameterAsText(5)

# depth field
bhDepthField = arcpy.GetParameterAsText(6)

# intervals table
intervalsTable = arcpy.GetParameterAsText(7)

# borehole id field in interval table
intBhIdFld = arcpy.GetParameterAsText(8)

# interval top depth - depth in relation to the top of the borehole, not elevation
# if left blank will interpolate elevation from DEM
intTopDepthFld = arcpy.GetParameterAsText(9)

# interval bottom depth
intBotDepthFld = arcpy.GetParameterAsText(10)

# buffer distance
buff = arcpy.GetParameterAsText(11)

# vertical exaggeration
ve = arcpy.GetParameterAsText(12)

# output feature class
outFC = arcpy.GetParameterAsText(13)
outName = os.path.splitext(os.path.basename(outFC))[0]

#append features boolean
append = arcpy.GetParameterAsText(14)

#append to feature class...
appendFC = arcpy.GetParameterAsText(15)

if append == 'true':
	outName = os.path.splitext(os.path.basename(appendFC))[0]

#data frame name
dfName = arcpy.GetParameterAsText(16)


# BEGIN
# ***************************************************************
try:
    #check for 3DAnalyst extension
    checkExtensions()
    
    #environment variables
    arcpy.env.overwriteOutput = True
    scratchDir = arcpy.env.scratchWorkspace
    arcpy.env.workspace = scratchDir
    
    #add an ORIG_FID field to the table that consists of values from the OID
    desc = arcpy.Describe(lineLayer)
    idField = desc.OIDFieldName
    addAndCalc(lineLayer, 'ORIG_FID', '[' + idField + ']')
    
    #interpolate the line to add z values
    zLine = lineLayer + '_z'
    arcpy.AddMessage('Getting elevation values for the cross-section in  ' + lineLayer)
    arcpy.InterpolateShape_3d(dem, lineLayer, zLine)
    arcpy.AddMessage('   ' + zLine + ' written to ' + arcpy.env.scratchWorkspace)
    
    #measure it and turn it into a route
    zmLine = lineLayer + '_zm'
    arcpy.AddMessage('Measuring the length of ' + zLine)
    arcpy.CreateRoutes_lr(zLine, 'ORIG_FID', zmLine, 'LENGTH', '#', '#', cp)
    arcpy.AddMessage('   ' + zmLine + ' written to ' + arcpy.env.scratchWorkspace)
    
    #figure out where the collar elevation is coming from, a user specified field or to be
    #calculated by interpolation from the DEM and stored in 'zDEM'
    if not bhzField =='':
    	zField = bhzField
    	zBoreholes = bhLayer
    else:
    	#interpolate Z values for the boreholes
     	# first, select the borehole location points based on the buffer distance
        #to minimize the processing time
    	arcpy.SelectLayerByLocation_management(bhLayer, 'WITHIN_A_DISTANCE', zmLine, buff)
    	zBoreholes = outName + '_zBoreholes'
    	arcpy.InterpolateShape_3d(dem, bhLayer, zBoreholes)
    
    	#add DEM Z values to zBoreholes attribute table
        #might already be there so we'll try to add it
    	try:
    		arcpy.AddField_management(zBoreholes, 'zDEM', 'FLOAT')
    	except:
    		pass
        #and calc in the geometry x
        try:
            arcpy.CalculateField_management(zBoreholes, 'zDEM', '!SHAPE.FIRSTPOINT.Z!', 'PYTHON_9.3')
        except:
            #if the elevation cannot be determined for some reason, calc 0
            arcpy.CalculateField_management(zBoreholes, 'zDEM', 0, 'PYTHON_9.3')
        
    	#'DEM_Z' becomes the collar elevation field
    	zField = 'zDEM'
        
        #clear the selection
        arcpy.SelectLayerByAttribute_management(bhLayer, "CLEAR_SELECTION")
    
    # locate boreholes points along the cross-section
    eventTable = outName + '_bhEvents'
    rProps = 'rkey POINT RouteM'
    arcpy.AddMessage('Locating ' + zBoreholes + ' on ' + zmLine)
    arcpy.LocateFeaturesAlongRoutes_lr(zBoreholes, zmLine, 'ORIG_FID', buff, eventTable, rProps, '#', 'DISTANCE')
    arcpy.AddMessage('    ' + eventTable + ' written to ' + arcpy.env.scratchWorkspace)

    #remove duplicate records that result from what appears to be
    #an unresolved bug in the Locate Features Along Routes tool
    #some points will get more than one record in the event table
    #and slightly different, sub-mapunit, mValues
    arcpy.DeleteIdentical_management(eventTable, bhIdField)
    
    # make the borehole lines to be used as routes
    bhLines = outName + '_bhLines'
    arcpy.AddMessage('Building lines in cross-section view from ' + eventTable)
    boreholeLines()
    arcpy.AddMessage('    ' + bhLines + ' written to ' + arcpy.env.scratchWorkspace)
    
    #if no intervals table was provided, stop here and deliver the zBoreholes as
    #the final feature class
    if intervalsTable == '':
    	if append == 'true':
    		arcpy.AddMessage('Appending features to ' + appendFC)
    		#schemas do not have to match but no attributes will be copied over
    		#unless the fields are in both layers.
    		arcpy.Append_management(bhLines, appendFC, 'NO_TEST')
    		outLayer = appendFC
    	else:
    		#copy the final fc from the scratch gdb to the output directory/gdb
    		srcLogs = os.path.join(scratchDir, bhLines)
    		arcpy.CopyFeatures_management(srcLogs, outFC)
    		outLayer = outFC
        arcpy.AddMessage('No intervals table specified')
        arcpy.AddMessage('    ' + outFC + ' saved')     
    else:
    	#or continue and place the intervals as events along the borehole routes
    	#convert to routes
    	bhRoutes = outName + '_bhRoutes'
        arcpy.AddMessage("Measuring the length of borehole lines in " + bhLines)
    	arcpy.CreateRoutes_lr(bhLines, bhIdField, bhRoutes, 'ONE_FIELD', bhDepthField, '#', 'UPPER_LEFT')
        arcpy.AddMessage('    ' + bhRoutes + ' written to ' + arcpy.env.scratchWorkspace)
       
    	#place borehole intervals (line events) on borehole routes
        props = intBhIdFld + ' LINE ' + intTopDepthFld + ' ' + intBotDepthFld
        arcpy.AddMessage("Placing borehole intervals on routes in " + bhRoutes)
        arcpy.MakeRouteEventLayer_lr(bhRoutes, bhIdField, intervalsTable, props, 'lyr', '#', 'ERROR_FIELD')
        
        #extract only valid route events from this in-memory layer
        arcpy.AddMessage('Filtering interval records with location errors.')
        bhIntervals = outName + '_intervals'
        arcpy.Select_analysis('lyr', bhIntervals, "\"LOC_ERROR\" <> 'ROUTE NOT FOUND'")
        arcpy.AddMessage('    ' + bhIntervals + ' written to ' + arcpy.env.scratchWorkspace)
    
        #now, join to eventTable in order to pass over the 'DISTANCE' which is the distance
        #the sticklog is away from the cross-section line
        arcpy.AddField_management(bhIntervals, 'Dis2XSec', 'DOUBLE')
        layer2 = arcpy.MakeFeatureLayer_management(bhIntervals, 'lyr2')
        arcpy.env.qualifiedFieldNames = False
        arcpy.AddJoin_management('lyr2', bhIdField, eventTable, bhIdField)
        arcpy.CalculateField_management('lyr2', "Dis2XSec", "!Distance!", "PYTHON_9.3", "")

        #output options
        if append == 'true':
            arcpy.AddMessage('Appending intervals to ' + appendFC)
            arcpy.Append_management(bhIntervals, appendFC, 'NO_TEST')
            outLayer = appendFC
        else: 
            #copy the final fc from the scratch gdb to the output directory/gdb
            srcIntervals = os.path.join(scratchDir, bhIntervals)
            arcpy.CopyFeatures_management(srcIntervals, outFC)
            arcpy.AddMessage('    ' + bhIntervals + ' copied to ' + outFC)
            outLayer = outFC
    
    #now, check for whether the user wants the output in a particular data frame
    #seems to inconsistently activate the data frame
    #layer will not be added unless Geoprocessing > Geoprocessing Options >
    #   'Add results of geoprocessing operations to the display' is checked
    if not dfName == '' and not dfName == 'ArcMap only':
    	mxd = arcpy.mapping.MapDocument('Current')
    	df = arcpy.mapping.ListDataFrames(mxd, dfName)[0]
    	mxd.activeView = df
    	arcpy.SetParameterAsText(17, outLayer)
        
    #some cleanup
    arcpy.DeleteField_management(lineLayer, 'ORIG_FID')
    
except:
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
    arcpy.AddError(pymsg)
    raise SystemError
        
        #raise SystemError
