'''
Name: xsecdefs
Author: Evan Thoms
Purpose: collection of functions that are used more than once
        in the cross section toolbox.
Date: 5/21/10
Usage: import xsec_defs

       gp - the ArcGIS geoprocessor object
       linelayer - an ArcGIS layer of one or more line features
       nameField - the field that contains the name of the cross section
       dem - a raster dem that underlies the entire set of lines
       cp - 'coordinate priority; from which corner of the map to begin measuring
       ve - vertical exaggeration
       outName - the name of the output feature class
       outDir - the output workspace of the feature class (gdb or folder)
       scratchDir - the scratch GDB which needs to be in \CrossSectionToolbox\scripts\bin
'''
import os
import sys
import traceback
import bisect
import arcpy

'''traceback lines - copy this code into all except clauses. Can't seem to call it as a function
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
    arcpy.AddError(pymsg)
    raise SystemError
'''

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

def getCPValue(quadrant):
    cpDict = {'northwest':'UPPER_LEFT', 'southwest':'LOWER_LEFT', 'northeast':'UPPER_RIGHT', 'southeast':'LOWER_RIGHT'}

    return cpDict[quadrant]

def cleanup(keepf, scratchDir):
    #clean out the scratch gdb
    arcpy.workspace = scratchDir
    try:
        if keepf == 'false':
            for fc in arcpy.listFeatureClasses():
                try:
                    arcpy.delete(fc)
                except:
                    arcpy.AddMessage('Cannot delete ' + fc + ' from ' + scratchDir)
            for tb in arcpy.listtables():
                try:
                    arcpy.delete(tb)
                except:
                    arcpy.AddMessage('Cannot delete ' + tb + ' from ' + scratchDir)

            arcpy.AddMessage('Intermediate files deleted.')

    except:
        # get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError

def flipLines(linesLayer, dem, cp, ve, outName, outDir, scratchDir):
    #shouldn't need this function anymore
    #calls other defs in this script to create cross sectional view surface profiles

    desc = arcpy.Describe(linesLayer)
    idField = desc.OIDFieldName

    #add a key field so we can do a join later
    arcpy.AddField(linesLayer, 'OLD_OID', 'LONG')
    arcpy.CalculateField_management(linesLayer, 'OLD_OID', idField)
    arcpy.RefreshCatalog

    #interpolate elevation values
    Zlines = outName + '_Z'
    interpolate(linesLayer, dem, Zlines, scratchDir)

    #measure the line(s)
    ZMlines = outName + '_ZM'
    measureLines(Zlines, nameField, ZMlines, 'LENGTH', '#', '#', cp, scratchDir)

    #transfer attributes because when you measure, for some reason, only the route id
    #field comes across
    ZMlines2 = ZMlines + '2'
    transferAtts(arcpy, ZMlines, linesLayer, nameField, nameField, '', ZMlines2)

    #swap the m for x and z for y values to 'flip' the lines to 2d
    #cross section view.
    ZMlinesPath = os.path.join(scratchDir, ZMlines2)
    ZMprofiles = outName + '_profiles'
    plan2side(arcpy, ZMprofiles, ZMlinesPath, ve, scratchDir)

    #transfer attributes
    fInfo = 'Comments_1 Comments_1 HIDDEN; OBJECTID_1 OBJECTID_1 HIDDEN; OLD_OID_1 OLD_OID_1 HIDDEN'
    transferAtts(arcpy, ZMprofiles, ZMlines2, 'OLD_OID', 'OLD_OID', fInfo, outName)

    #delete the old_oid field
    arcpy.DeleteField(linesLayer, 'OLD_OID')
    arcpy.DeleteField(outName, 'OLD_OID_1')
    arcpy.DeleteField(outName, 'OBJECTID_1')

def interpolate(inLayer, dem, Zfeat):
    #interpolates elevations from dem, any feature type
    #creates new Z-aware feature class as a shapefile or gdb feature class
    #depending on the type of output workspace - folder or gdb.
    try:
        arcpy.AddMessage('Getting elevation values for features in ' + inLayer)
        arcpy.InterpolateShape_3d(dem, inLayer, Zfeat)
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError
    finally:
        arcpy.AddMessage(Zfeat + ' written to ' + arcpy.env.scratchWorkspace)

def measureLines(inLayer, idField, Mlines, lengthVar, fromFld, toFld, cp):
    #measures the lines in Zlines and creates a new featureclass that is
    #M and Z aware
    try:
        arcpy.AddMessage('Measuring the length of the line(s) in ' + inLayer)
        arcpy.CreateRoutes_lr(inLayer, idField, Mlines, lengthVar, fromFld, toFld, cp)
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError
    finally:
        arcpy.AddMessage(Mlines + ' written to ' + arcpy.env.scratchWorkspace)

def plan2side(ZMlines, ve):
    #flip map view lines to cross section view without creating a copy
    #this function updates the existing geometry 
    arcpy.AddMessage('Flipping ' + ZMlines + ' from map view to cross-section view')
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

def createEventTable(features, ZMline, rkey, buff, eventTable, rProps):
    #builds event table of points located along a line route
    try:
        arcpy.AddMessage('Locating ' + features + ' on ' + ZMline)
        arcpy.LocateFeaturesAlongRoutes_lr(features, ZMline, rkey, buff, eventTable, rProps, 'FIRST', 'NO_DISTANCE', 'NO_ZERO')
        #return eventTable
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError

def boreholeLines(scratchDir, outFC, Zboreholes, eventTable, bhIdField, ZField, bhDepthField, ve):
    #creates 2d cross section view sticklogs that show the depth of each borehole
    try:
        # create an empty output featureclass with the fields of the event table
		arcpy.CreateFeatureclass_management(scratchDir, outFC, 'POLYLINE', Zboreholes, 'ENABLED', 'ENABLED')

        # open search cursor on the event table
		tRows = arcpy.SearchCursor(eventTable)
			
        # open insert cursor on the output layer
		cur = arcpy.InsertCursor(outFC)

        # create point and array objects
		pnt1 = arcpy.CreateObject('Point')
		pnt2 = arcpy.CreateObject('Point')
		array = arcpy.CreateObject('Array')

		arcpy.AddMessage('Building borehole lines in cross-section view...')
		
		#get a list of fields in the template table that does not include OBJECTID or FID or SHAPE
		#anything else? add it to xf! ("excluded fields")
		xf = ('shape', 'objectid', 'fid', 'shape_length')
		lf = arcpy.ListFields(Zboreholes)
		names = []
		for f in lf:
			if not f.name.lower() in xf:
				names.append(f.name)
				
        # enter while loop for each row in events table
		for tRow in tRows:
            # set the point's X and Y coordinates
            # set Y depending on whether the user wants to use the elevation of the
            # borehole from the DEM or from a value in the collar z field
			try:
				pnt1.Y = float(tRow.getValue(ZField)) * float(ve)
			except:
				arcpy.AddMessage('No collar elevation available for borehole ID ' + str(tRow.getValue(bhIdField)))
				arcpy.AddMessage('Using a value of 10000 for collar elevation')
				pnt1.Y = 10000

			pnt1.X = tRow.RouteM
			pnt2.X = pnt1.X

            #if there is no value in bhDepthField, subtract 5000 from the top
            #elevation as a way of flagging this point
			try:
				pnt2.Y = pnt1.Y - (float(tRow.getValue(bhDepthField) * float(ve)))
			except:
				arcpy.AddMessage('No borehole depth available for borehole OID ' + str(tRow.OBJECTID))
				arcpy.AddMessage('Using a value of 5000 for borehole depth')
				pnt2.Y = pnt1.Y - 5000

            # add points to array
			array.add(pnt1)
			array.add(pnt2)

            # set array to the new feature's shape
			row = cur.newRow()
			row.shape = array
			
			# copy over the other attributes
			for name in names:
				row.setValue(name, tRow.getValue(name))

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

def zPoints2XSec (outName, Zpts, eventTable, ZField, ve, scratchDir):
    #creates 2d cross section view sticklogs that show the depth of each borehole
    try:
        # create the output featureclass
        #arcpy.CreateFeatureClass_management(scratchDir, outName, 'POLYLINE', Zboreholes, 'ENABLED', 'ENABLED')
        outFC = outName + '_idonly'
        arcpy.CreateFeatureClass_management(scratchDir, outFC, 'POINT', '#', 'ENABLED', 'ENABLED')

        # open search cursor on the event table
        tRows = arcpy.SearchCursor(eventTable)
        tRow = tRows.Next()

        # open insert cursor on the output layer
        cur = arcpy.InsertCursor(outFC)

        # create point and array objects
        pnt1 = arcpy.CreateObject('Point')

        arcpy.AddMessage('Placing points in cross-section view...')

        # enter while loop for each row in events table
        while tRow:
            # set the point's X and Y coordinates
            # set Y depending on whether the user wants to use the elevation of the
            # borehole from the specified Z value field.
            try:
                pnt1.y = float(tRow.GetValue(ZField)) * float(ve)
            except:
                arcpy.AddMessage('No elevation available for borehole OID ' + str(tRow.OBJECTID))
                arcpy.AddMessage('Using a value of 5000')
                pnt1.y = 5000

            pnt1.x = float(tRow.GetValue('RouteM'))

            # set array to the new feature's shape
            row = cur.newRow()
            row.shape = pnt1

            # insert the feature
            cur.insertRow(row)

            # get the next row in the table
            tRow = tRows.Next()

        #join the output fc with the events table and transfer the attributes
        fInfo = 'OBJECTID OBJECTID HIDDEN; rkey rkey HIDDEN; RouteM RouteM HIDDEN'
        transferAtts(arcpy, outFC, eventTable, 'OBJECTID', 'OBJECTID', fInfo, outName)

        #arcpy.DeleteField(outName, 'rkey; RouteM; OBJECTID')

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

def intersectFeatures(interList, outFC, attParm, clusterParm, outType):
    #creates feature class of points located along a line route
    try:
        #arcpy.AddMessage('Intersecting features: ' + interList)
        arcpy.Intersect_analysis(interList, outFC, attParm, clusterParm, outType)
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)
        raise SystemError

        
def xsecPoints(outFC, Zpts, eventTable, bhZField, ve, scratchDir):
    #creates 2d cross section view sticklogs that show the depth of each borehole
	try:
		# create the output featureclass
		#arcpy.CreateFeatureClass_management(scratchDir, outName, 'POLYLINE', Zboreholes, 'ENABLED', 'ENABLED')
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

			#set the point's X and Y coordinates
			pnt.X = float(tRow.getValue('RouteM'))
			pnt.Y = float(tRow.getValue(bhZField)) * float(ve)

			#set the point to the new feature's shape
			row = cur.newRow()
			row.shape = pnt
			
			#copy over the other attributes
			for name in names:
				row.setValue(name, tRow.getValue(name))

			#insert the feature
			cur.insertRow(row)

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
        rows = arcpy.SearchCursor(ZMline)
        row = rows.Next()
        feat = row.Shape
        part = feat.GetPart(0)
        pnt = part.Next()
        while pnt:
            vDict[pnt.m] = (pnt.x, pnt.y)
            vList.append(pnt.m)
            pnt = part.Next()

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

    try:
        #if our distance value is smaller than the M value at the beginning
        #of the line, use the smallest M value as the key for the dictionary
        #and use the XY of that entry, no interpolation
        if distance <= min(vList):
            key = min(vList)
            newX = vDict[key][0]
            newY = vDict[key][1]

        #if our distance value is larger than the M value at the end of the line
        #use the largest M value of the key for the dictionary and use the XY
        #of that entry, no interpolation
        elif distance >= max(vList):
            key = max(vList)
            newX = vDict[key][0]
            newY = vDict[key][1]

        #otherwise, find the bracketing M-value pair for our distance and
        #interpolate the XY coordinates
        else:
            #bisect returns the index
            #arcpy.AddMessage('trying')
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
     desc = arcpy.describe(path)
     while not desc.datatype == 'Folder':
         path = os.path.dirname(path)
         desc = arcpy.describe(path)

     return path

def XYZfile2features(xyzFile, threeDFC, shpType):
    #arcpy.AddMessage(xyzFile + ', ' + 'GENERATE' + ', ' + threeDFC + ', ' + shpType)
    try:
        arcpy.ascii3dtofeatureclass_3d(xyzFile, 'GENERATE', threeDFC, 'POLYGON') #, '#', '#', '#', '#', 'DECIMAL_POINT')

    except:
        # get the traceback object
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
        arcpy.AddError(pymsg)

        raise SystemError
