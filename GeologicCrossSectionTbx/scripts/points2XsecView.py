'''
Name: points2XsecView.py
Description: ArcToolbox tool script to plot map-view points in a cross-sectional view

Requirements: python, 3D Analyst extension 
Author: Evan Thoms, U.S. Geological Survey, ethoms@usgs.gov
Date: 7/23/07
Edits beginning on 5/25/10

Edits beginning on 6/12/13, primarily to remove references to xsecdefs and 
to add functionality of plotting apparent dip of structural measurements.

Much credit goes to Ralph Haugerud for the code that calculates apparent dip

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

def cartesianToGeographic(angle):
    ctg = -90 - angle
    if ctg < 0:
        ctg = ctg + 360
    return ctg

def obliq(theta1, theta2):
    try:
        obl = abs(theta1 - theta2)
        if obl > 180:
            obl = obl - 180
        if obl > 90:
            obl = 180 - obl
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError         
    return obl

def angleDiff(facingAngle, angleOfTarget):
    return (facingAngle - angleOfTarget + 180) % 360 - 180

def plotAzimuth(azi, thetaXS, apparentInclination):
    thetaXSB = thetaXS + 180
    if thetaXSB > 360:  thetaXSB = thetaXSB - 360
    
    #find the absolute angle between the bearing of the cross section
    #and the azimuth of the structural measurement
    #if it is within 90 degrees of the direction of the xs, that should plot
    #as a tick mark dipping to the right of the panel, if not, to the left.
    forwardAngle = abs(angleDiff(azi, thetaXS))
    backwardAngle = abs(angleDiff(azi, thetaXSB))
    
    if forwardAngle < 90:
        return apparentInclination + 90
    elif backwardAngle < 90:
        return 270 - apparentInclination   
    else: 
        return 270

def apparentPlunge(azi, inc, thetaXS):
    try:
        obliquity = obliq(azi, thetaXS)
        appInc = math.degrees(math.atan(float(ve) * math.tan(math.radians(inc)) * math.cos(math.radians(obliquity))))
        return appInc, obliquity
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError        


# PARAMETERS
# ***************************************************************
#set the orientation data boolean here
isOrientationData = False

# Cross-section layer, use this as a reference to the feature layer
lineLayer = arcpy.GetParameterAsText(0)

#use this as the basename for intermediate files (because lineLayer may 
#have slashes in the name/path)
lineLyrName = arcpy.Describe(lineLayer).name 

#can't figure out how to put this in the validator class ??
result = arcpy.GetCount_management(lineLayer)
if int(result.getOutput(0)) > 1:
    arcpy.AddError(lineLayer + ' has more than one line in it.')
    raise SystemError

# elevation raster layer
dem = arcpy.GetParameterAsText(1)

#coordinate priority - corner from which the measuring will begin
cp = getCPValue(arcpy.GetParameterAsText(2))

# structural data points layer
ptLayer = arcpy.GetParameterAsText(3)

# collar Z field
ptZField = arcpy.GetParameterAsText(4)

#strike field
strikeField = arcpy.GetParameterAsText(5)

#dip field
dipField = arcpy.GetParameterAsText(6)

#update the orientation data boolean if these fields are filled in
if not strikeField == "" and not dipField == "": isOrientationData = True

#buffer/search distance
buff = arcpy.GetParameterAsText(7)

# vertical exaggeration
ve = float(arcpy.GetParameterAsText(8))

# output feature class
outFC = arcpy.GetParameterAsText(9)
outName = os.path.splitext(os.path.basename(outFC))[0]

#append features boolean
append = arcpy.GetParameterAsText(10)

#append to feature class...
appendFC = arcpy.GetParameterAsText(11)

if append == 'true':
	outName = os.path.splitext(os.path.basename(appendFC))[0]
    
#data frame name
dfName = arcpy.GetParameterAsText(12)

# BEGIN
# ***************************************************************
try:
    #check for 3DAnalyst extension
    checkExtensions()
    
    #environment variables
    arcpy.env.overwriteOutput = True
    scratchDir = arcpy.env.scratchWorkspace
    arcpy.env.workspace = scratchDir
    
    if arcpy.Exists(outFC): arcpy.Delete_management(outFC)
    
    #add an ORIG_FID field to the table that consists of values from the OID
    desc = arcpy.Describe(lineLayer)
    idField = desc.OIDFieldName
    addAndCalc(lineLayer, 'ORIG_FID', '[' + idField + ']')
    
    #interpolate the line to add z values
    zLine = lineLyrName + '_z'
    arcpy.AddMessage('Getting elevation values for the cross-section in ' + lineLyrName)
    arcpy.InterpolateShape_3d(dem, lineLayer, zLine)
    arcpy.AddMessage('   ' + zLine + ' written to ' + arcpy.env.scratchWorkspace)
    
    #measure it and turn it into a route
    zmLine = lineLyrName + '_zm'
    if arcpy.Exists(zmLine): arcpy.Delete_management(zmLine)
    arcpy.AddMessage('Measuring the length of ' + zLine)
    arcpy.CreateRoutes_lr(zLine, 'ORIG_FID', zmLine, 'LENGTH', '#', '#', cp)
    arcpy.AddMessage('   ' + zmLine + ' written to ' + arcpy.env.scratchWorkspace)
    
    #select points according to the section distance
    arcpy.SelectLayerByLocation_management(ptLayer, 'WITHIN_A_DISTANCE', zmLine, buff)
    zPts = outName + '_z'
    
    #figure out where the point elevation is coming from: a user specified field or to be
    #calculated by interpolation from the DEM and stored in 'zDEM'
    if not ptZField =='':
        #if the elevation values are in the table, copy the selection to an
        #output fc
    	zField = ptZField
    	zPts = arcpy.CopyFeatures_management(ptLayer, zPts)
    else:
    	#otherwise, interpolate Z values for the points
    	arcpy.InterpolateShape_3d(dem, ptLayer, zPts)
    
    	#add DEM Z values to zPts attribute table
        #might already be there so we'll try to add it
    	try:
    		arcpy.AddField_management(zPts, 'zDEM', 'FLOAT')
    	except:
    		pass
        #and calc in the geometry x
        try:
            arcpy.CalculateField_management(zPts, 'zDEM', '!SHAPE.FIRSTPOINT.Z!', 'PYTHON_9.3')
        except:
            #if the elevation cannot be determined for some reason, calc 0
            arcpy.CalculateField_management(zPts, 'zDEM', -999, 'PYTHON_9.3')
        
    	#'DEM_Z' becomes the collar elevation field
    	zField = 'zDEM'
        
        #clear the selection
        arcpy.SelectLayerByAttribute_management(ptLayer, "CLEAR_SELECTION")
     
    #add ORIG_ID for deleting identical events and for joining attributes later
    addAndCalc(zPts, 'ORIG_PTID', '[OBJECTID]')
    
    # locate points points along the cross-section
    eventTable = outName + '_ptEvents'
    rProps = 'rkey POINT RouteM'
    arcpy.AddMessage('Locating ' + zPts + ' on ' + zmLine)
    arcpy.LocateFeaturesAlongRoutes_lr(zPts, zmLine, 'ORIG_FID', buff, eventTable, rProps, '#', 'DISTANCE')
    arcpy.AddMessage('   ' + eventTable + ' written to ' + arcpy.env.scratchWorkspace)

    #remove duplicate records that result from what appears to be
    #an unresolved bug in the Locate Features Along Routes tool
    #some points will get more than one record in the event table
    #and slightly different, sub-mapunit, mValues
    arcpy.DeleteIdentical_management(eventTable, 'ORIG_PTID')

    #place points as events on the cross section line
    eventLyr = '_lyr'
    rProps = 'rkey POINT RouteM'
    arcpy.MakeRouteEventLayer_lr(zmLine, 'ORIG_FID', eventTable, rProps, eventLyr, '#', 'ERROR_FIELD', 'ANGLE_FIELD', 'TANGENT')
    eventPts = outName + '_events'
    arcpy.CopyFeatures_management(eventLyr, eventPts)
    arcpy.AddMessage('   ' + eventPts + ' feature layer written to  '+ arcpy.env.scratchWorkspace)
    
    # add DistanceFromSection and LocalXsAzimuth fields
    arcpy.AddField_management(eventPts,'DistanceFromSection','FLOAT')
    arcpy.AddField_management(eventPts,'LocalCSAzimuth','FLOAT')
    
    #check for whether these are structural data
    if not strikeField == '':
        isOrientationData = True
        arcpy.AddField_management(eventPts,'ApparentInclination','FLOAT')
        arcpy.AddField_management(eventPts,'Obliquity','FLOAT')
        arcpy.AddField_management(eventPts,'PlotAzimuth','FLOAT')
    else:
        isOrientationData = False       
    
    #open an data access update-cursor, edit geometries, and calculate attributes
    #discovered during development: for some reason, when a few structural points are
    #directly on top of each other (co-located) instead of being spread out along the
    #cross-section line, the updateRow function takes a very long time. 
    #I had 17 points split into two groups, all points in a group were snapped to the
    #same point. This script took over 3 minutes to complete. When the 17 points 
    #were spread roughly equally along the cross-section line, it took 17 seconds
    #Maybe something to do with the spatial index?
    arcpy.AddMessage('Calculating shapes and attributes from ' + eventPts)
    
    #in the case where isOrientationData is false, we can't call orientation related
    #fields or the cursor blows up
    if isOrientationData:
        arcpy.AddMessage("is Orientation Data") 
        fldList = ["OBJECTID", "SHAPE@M", zField, "SHAPE@XY", "LOC_ANGLE", "LocalCSAzimuth", 
                                     "DistanceFromSection", "Distance", strikeField, dipField,"Obliquity", 
                                     "ApparentInclination", "PlotAzimuth"]
    else:
        arcpy.AddMessage("is not Orientation Data")
        fldList = ["OBJECTID", "SHAPE@M", zField, "SHAPE@XY", "LOC_ANGLE", "LocalCSAzimuth", 
                                     "DistanceFromSection", "Distance"]
                               
    rows = arcpy.da.UpdateCursor(eventPts, fldList)
    for row in rows:
        arcpy.AddMessage('OBJECTID ' + str(row[0])) 
        #swap M,Z for X,Y
        try:
            #M for X
            x = row[1]
            if row[2] == None:
                y = -999
                arcpy.AddMessage('    OBJECTID '+ str(row[0]) +' has no elevation value')
                arcpy.AddMessage('        calculating a value of -999')
            else:
                y = row[2] * float(ve)
            row[3] = [x, y]
        except:
            arcpy.AddMessage('    Failed to make shape: OBJECTID = '+str(row.OBJECTID)+', M = '+str(row[1]) +', Z = '+str(row[2]))
            ## need to do something to flag rows that failed?
            #   convert from cartesian  to geographic angle
        csAzi = cartesianToGeographic(row[4])   #LOC_ANGLE
        row[5] = csAzi                          #LocalCSAzimuth
        row[6] = row[7]                         #DistanceFromSection = Distance
        
        #Ralph's code allows for the mixing of strike/dip and lineation/plunge measurements.
        #He can do this because the 'structural type' field in the geodatabase
        #is controlled by a domain, so he can hard-code the parsing of the orientation types and
        #run them through different functions row by row. 
        #To avoid forcing the use of a domain or running the tool multiple times based on
        #user-made selection sets of the orientation data, this code will just require
        #that all orientation data are in lineation/plunge or azimuth/dip format
        #strike will have to be converted to dip-direction beforehand
        #   use this field calculation
        #   !strike! + 90 if ((!strike! + 90) < 360) else (!strike! + 90) - 360
        if isOrientationData == True:
            appInc, oblique = apparentPlunge(row[8], row[9], csAzi)
            plotAzi = plotAzimuth(row[8], csAzi, appInc)
            row[10] = round(oblique, 2)   #Obliquity
            row[11] = round(appInc, 2)    #ApparentInclination
            row[12] = round(plotAzi, 2)   #PlotAzimuth
        rows.updateRow(row)
    
    #some cleanup
    for fld in 'DISTANCE', 'LOC_ANGLE', 'ORIG_FID':
        arcpy.DeleteField_management(eventPts, fld)
    del row, rows
    arcpy.DeleteField_management(lineLayer, 'ORIG_FID')
        
    #output options
    if append == 'true':
        arcpy.AddMessage('Appending intervals to ' + appendFC)
        arcpy.Append_management(eventPts, appendFC, 'NO_TEST')
        outLayer = appendFC
    else: 
        #copy the final fc from the scratch gdb to the output directory/gdb
        srcPts = os.path.join(scratchDir, eventPts)
        arcpy.CopyFeatures_management(srcPts, outFC)
        arcpy.AddMessage('    ' + eventPts + ' copied to ' + outFC)
        outLayer = outFC
         
    #now, check for whether the user wants the output in a particular data frame
    #seems to inconsistently activate the data frame
    #layer will not be added unless Geoprocessing > Geoprocessing Options >
    #   'Add results of geoprocessing operations to the display' is checked
    if not dfName == '' and not dfName == 'ArcMap only':
    	mxd = arcpy.mapping.MapDocument('Current')
    	df = arcpy.mapping.ListDataFrames(mxd, dfName)[0]
    	mxd.activeView = df
        
    #next line is irrelevant if the output symbology property doesn't work
   	#arcpy.SetParameterAsText(13, outLayer)
    
    #setting the symbology property of the output parameter is not working, thus...
    #get the current map document
    mxd = arcpy.mapping.MapDocument("Current")
    #make a map layer from the output feature class
    addLayer = arcpy.mapping.Layer(outLayer)
    #add that layer to the map and currently active data frame
    arcpy.mapping.AddLayer(mxd.activeDataFrame, addLayer)
    #now find the layer in the map (not the same as addLayer for some reason!)
    stxLyr = arcpy.mapping.ListLayers(mxd, outName)[0]
    
    #look for the symbology layer
    thisFile = __file__  #I love this! I never knew it was so easy to get the 
    #path of the current script!
    dirname = os.path.dirname
    paParent = (dirname(dirname(thisFile)))
    symLyr = os.path.join(paParent, 'docs', 'structureTicks.lyr')
    arcpy.ApplySymbologyFromLayer_management(stxLyr, symLyr)

except:
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
    arcpy.AddError(pymsg)
    raise SystemError
    
    
    

