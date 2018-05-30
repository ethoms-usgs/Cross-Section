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
        arcpy.AddError(traceback.format_exc())
        raise SystemError
    finally:
        arcpy.RefreshCatalog
        
def cartesianToGeographic(angle):
    ctg = -90 - angle
    if ctg < 0:
        ctg = ctg + 360
    return ctg

def obliq(b1, b2):
    return 180 - abs(abs(b1 - b2) - 180)
    
def bearing_sum(b1, b2):
    '''given two bearings between 0 and 360, find the bearing of the sum,
    which may be more than 360'''
    s = (b1 + b2 + 360) % 360
    if s == 0:
        return 360
    else:
        return s
    
def symbol_rotation(inclination_direction, local_xs_azi, app_inc_VE):
    '''If the bearing of the cross section was 90, it would be easy to find out
    if the dip direction was + or - 90, that is, dipping in the direction of the
    bearing or dipping the other direction. So, rotate the coordinate system by
    the amount necessary to bring the xs bearing to 90, and then compare the dip
    direction'''
    #rotation amount
    delta_a = 90 - local_xs_azi
    #if positive, it's a cw rotation of the axis
    if delta_a > 0:
        rotate_inc = inclination_direction + delta_a
        #bearings in the fourth quadrant (geographic) will move to the first;
        #they will be more than 360, so reduce.
        if rotate_inc > 360:
            rotate_inc = rotate_inc - 360 
    else:
    #if negative it's a ccw rotation
        rotate_inc = inclination_direction - abs(delta_a)
        
    #for arithmetic rotation of symbol in map view.
    if rotate_inc in [0, 180]:
        return 90
    elif 0 < rotate_inc < 180:
        return 360 - app_inc_VE
    else:
        return 180 + app_inc_VE
    
def apparentDip(azi, inc, thetaXS):
    try:
        alpha = obliq(azi, thetaXS)
        complement =  180 - alpha
        if alpha < complement:
            obliquity = alpha
        else:
            obliquity = complement
            
        #appIncVE for debugging
        appIncVE = math.degrees(math.atan(math.tan(math.radians(inc)) * math.sin(math.radians(obliquity))))
        appInc = math.degrees(math.atan(ve * math.tan(math.radians(inc)) * math.sin(math.radians(obliquity))))
        return obliquity, appInc, appIncVE
    except:
        arcpy.AddError(traceback.format_exc())
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
ptz_field = arcpy.GetParameterAsText(4)

#strike field
strike_field = arcpy.GetParameterAsText(5)

#dip field
dip_field = arcpy.GetParameterAsText(6)

#update the orientation data boolean if these fields are filled in
if not strike_field == '' and not dip_field == '': isOrientationData = True

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
    
    #check for an output
    if outName == ''  and appendFC == '':
        arcpy.AddMessage('Select a new feature class or one to which new features will be appended')
        raise SystemError
    
    #environment variables
    arcpy.env.overwriteOutput = True
    scratchDir = arcpy.env.scratchWorkspace
    arcpy.env.workspace = scratchDir
    
    if arcpy.Exists(outFC): arcpy.Delete_management(outFC)
    
    #add an ORIG_FID field to the table that consists of values from the OID
    desc = arcpy.Describe(lineLayer)
    idField = desc.OIDFieldName
    addAndCalc(lineLayer, 'ORIG_FID', '[' + idField + ']')
    
    #measure it and turn it into a route
    mLine = lineLyrName + '_m'
    if arcpy.Exists(mLine): arcpy.Delete_management(mLine)
    arcpy.AddMessage('Measuring the length of cross-section line')
    arcpy.CreateRoutes_lr(lineLayer, 'ORIG_FID', mLine, 'LENGTH', '#', '#', cp)
    arcpy.AddMessage('{} written to {}'.format(mLine, scratchDir))
    
    #select points according to the section distance
    arcpy.SelectLayerByLocation_management(ptLayer, 'WITHIN_A_DISTANCE', mLine, buff)
    points_near_line = os.path.join(scratchDir, outName + '_sel')
    #copy to a new feature classe
    arcpy.CopyFeatures_management(ptLayer, points_near_line)
    #clear the selection
    arcpy.SelectLayerByAttribute_management(ptLayer, 'CLEAR_SELECTION')
    
    #figure out where the point elevation is coming from: a user specified field or to be
    #calculated by interpolation from the DEM and stored in 'zDEM'
    if not ptz_field =='':
        arcpy.AddMessage('Using elevations stored in the field {}'.format(ptz_field))
        #if the elevation values are in the table, copy the selection to an
        #output fc
        z_field = ptz_field
    else:
        arcpy.AddMessage('Adding elevations from {}'.format(dem))
        #otherwise, add Z values for the points from the DEM surface
        #arcpy.InterpolateShape_3d(dem, ptLayer, points_near_line)
        arcpy.AddSurfaceInformation_3d(points_near_line, dem, 'Z')
        z_field = 'Z'
 
    #add ORIG_ID for deleting identical events and for joining attributes later
    addAndCalc(points_near_line, 'ORIG_PTID', '[OBJECTID]')
    
    # locate points along the cross-section
    eventTable = outName + '_ptEvents'
    rProps = 'rkey POINT RouteM'
    arcpy.AddMessage('Locating {} on {}'.format(points_near_line, mLine))
    arcpy.LocateFeaturesAlongRoutes_lr(points_near_line, mLine, 'ORIG_FID', buff, eventTable, rProps, '#', 'DISTANCE')
    arcpy.AddMessage('   {} written to {}'.format(eventTable, scratchDir))

    #remove duplicate records that result from what appears to be
    #an unresolved bug in the Locate Features Along Routes tool
    #some points will get more than one record in the event table
    #and slightly different, sub-mapunit, mValues
    try:
        arcpy.DeleteIdentical_management(eventTable, 'ORIG_PTID')
    except:
        pass

    #place points as events on the measured cross section line
    #TANGENT location angle is in cartesian coordinate system,
    #0 is to the right, not north.
    eventLyr = '_lyr'
    rProps = 'rkey POINT RouteM'
    arcpy.MakeRouteEventLayer_lr(mLine, 'ORIG_FID', eventTable, rProps, eventLyr, '#', 'ERROR_FIELD', 'ANGLE_FIELD', 'TANGENT')
    eventPts = outName + '_events'
    arcpy.CopyFeatures_management(eventLyr, eventPts)
    arcpy.AddMessage('   {} feature layer written to {}'.format(eventPts, scratchDir))
    
    # add DistanceFromSection
    arcpy.AddField_management(eventPts,'DistanceFromSection','FLOAT')
    
    #in the case where isOrientationData is false, we can't call orientation related
    #fields or the cursor blows up
    fldList = ['OBJECTID', 'SHAPE@M', z_field, 'SHAPE@XY', 'LOC_ANGLE', 'DISTANCE', 'DistanceFromSection' ]

    #check for whether these are structural data
    if not strike_field == '':
        isOrientationData = True
        arcpy.AddMessage('is Orientation Data') 
        arcpy.AddField_management(eventPts,'LocalXSAzimuth','FLOAT')
        arcpy.AddField_management(eventPts,'Obliquity','FLOAT')
        arcpy.AddField_management(eventPts,'ApparentInclination','FLOAT')
        arcpy.AddField_management(eventPts,'ApparentIncVE','FLOAT')
        arcpy.AddField_management(eventPts,'SymbolRotation','FLOAT')
        fldList.extend((strike_field, dip_field, 'LocalXSAzimuth', 'Obliquity', 
                                     'ApparentInclination', 'ApparentIncVE', 'SymbolRotation'))
    else:
        isOrientationData = False       
    
    #open a data access update-cursor, edit geometries, and calculate attributes
    #discovered during development: for some reason, when a few structural points are
    #directly on top of each other (co-located) instead of being spread out along the
    #cross-section line, the updateRow function takes a very long time. 
    #I had 17 points split into two groups, all points in a group were snapped to the
    #same point. This script took over 3 minutes to complete. When the 17 points 
    #were spread roughly equally along the cross-section line, it took 17 seconds
    #Maybe something to do with the spatial index?
    arcpy.AddMessage('Calculating shapes and attributes from {}'.format(eventPts))
    rows = arcpy.da.UpdateCursor(eventPts, fldList)
    for row in rows:
        arcpy.AddMessage('OBJECTID: {}'.format(str(row[0])))
        #swap M,Z for X,Y
        try:
            #M for X
            x = row[1]
            #Z for Y
            if row[2] == None:
                y = -999
                arcpy.AddMessage('    OBJECTID {} has no elevation value'
                    .format(str(row[0])))
                arcpy.AddMessage('        Maybe it does not lie over the DEM?')
                arcpy.AddMessage('        calculating a value of -999')
            else:
                y = row[2] * ve
            #write geometry through SHAPE@XY
            row[3] = [x, y]

        except:
            arcpy.AddMessage('    Failed to make shape: OBJECTID {}, M = {}, Z = {}'
                .format(str(row[0]), str(row[1]), str(row[2])))
            ## need to do something to flag rows that failed?
            #   convert from cartesian  to geographic angle

        row[6] = row[5]            #DistanceFromSection = Distance  
        #Ralph's code allows for the mixing of strike/dip and lineation/plunge measurements.
        #He can do this because the 'structural type' field in the geodatabase
        #is controlled by a domain, so he can hard-code the parsing of the orientation types and
        #run them through different functions row by row. 
        #apparent dip calculation is different for planar measurements than for axial - don't know how to fix this
        #strike will have to be converted to dip-direction beforehand
        #   use this field calculation
        #   !strike! + 90 if ((!strike! + 90) < 360) else (!strike! + 90) - 360
        if isOrientationData == True:
            local_azimuth = cartesianToGeographic(row[4])   #LOC_ANGLE (tangent)
            row[9] = local_azimuth                          #Local azimuth
            oblique, appInc, appIncVE = apparentDip(row[7], row[8], local_azimuth)
            row[10] = round(oblique, 2)   #Obliquity
            row[11] = round(appInc, 2)    #ApparentInclination
            row[12] = round(appIncVE,2)   #exaggerated apparent inclination
            
            inclination_direction = bearing_sum(row[7], 90)
            plotAzi = symbol_rotation(inclination_direction, local_azimuth, appInc)

            row[13] = round(plotAzi, 2)   #SymoblRotation
            
        rows.updateRow(row)
        
    #clear the spatial reference of the final feature class
    unknown = arcpy.SpatialReference()
    unknown.loadFromString(u'{B286C06B-0879-11D2-AACA-00C04FA33C20};-450359962737.05 -450359962737.05 10000;#;#;0.001;#;#;IsHighPrecision')
    arcpy.DefineProjection_management(eventPts, unknown)
    
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
    mxd = arcpy.mapping.MapDocument('Current')
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
    path_parent = (dirname(dirname(thisFile)))
    symLyr = os.path.join(path_parent, 'docs', 'structureTicks.lyr')
    arcpy.ApplySymbologyFromLayer_management(stxLyr, symLyr)

except:
    arcpy.AddError(traceback.format_exc())
    raise SystemError
    
    
    

