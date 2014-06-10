'''
Name:structural.py
Description: ArcToolbox tool script to convert map view coordinates
   of structural data points to cross-section view coordinates.
   python version of my CrossSection.dll written in VB to access ArcObjects
Requirements: python, 3D Analyst extension, ArcInfo license
Author: Evan Thoms, U.S. Geological Survey, ethoms@usgs.gov
Date: 7/23/07

beginning upgrades to 10.1 6/12/13
'''
# Import modules
import os
import sys
import math
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
  
    
def interpolate(DEM, feat, pref, name):
    # set the output shapefile name
    outZfeat = pref + name
    try:
        gp.AddMessage("Getting elevation values for selected features...")
        gp.Interpolateshape_3d(DEM, feat, outZfeat)
        return outZfeat
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Can't interpolate values!")
        raise SystemError

def measureZline(Zline, NameField, pref):
    outMZline = pref + "MZXS.shp"
    try:
        gp.AddMessage("Measuring the length of the cross section line...")
        gp.CreateRoutes_lr(Zline, NameField, outMZline, "LENGTH")
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Can't turn " + pref + "ZXS.shp into a route.")
        raise SystemError
    return outMZline    


def CalcApDips(Zpts, line, strike, dip, ve):
    pi = 4 * math.atan(1)
    d2r = pi/180
    r2d = 180/pi
    try:
        # add the new fields
        try:
            gp.AddField(Zpts, "DipDir", "DOUBLE")
            gp.AddField(Zpts, "ApDip", "DOUBLE")
            gp.AddField(Zpts, "VEDip", "DOUBLE")
            gp.AddField(Zpts, "DipRot", "DOUBLE")
        except:
            # get the traceback object
            gp.AddError(traceerr(sys.exc_info()[2]))
            gp.AddMessage("Can't add dip calculation fields to " + Zpts + "!")
            raise SystemError
        
        # Get start and end points of line for calculation of bearing (W to E) and anti-bearing (E to W)
        # important for calculating the dip symbol rotation angle (DipRot)
        try:
            # identify the geometry field
            dsc = gp.describe(line)
            shape = dsc.ShapeFieldName
            
            # create the search cursor    
            rows = gp.SearchCursor(line)
            row = rows.Next()

            # create the geometry object
            feat = row.GetValue(shape)
            # coordinates of first and last points of line
            first = feat.FirstPoint.split(" ") # FirstPoint a string of the x and y coordinates in format "X Y"
            firstx = float(first[0])
            firsty = float(first[1])
            last = feat.LastPoint.split(" ")
            lastx = float(last[0])
            lasty = float(last[1])
     
            # send the coordinates to David Finlayson's distbearing function to get a bearing
            XS = distbearing(firstx, firsty, lastx, lasty)
            # calculate the 'anti-bearing' based on this bearing
            if (XS + 180) <= 360:
                XSa = XS + 180
            else:
                XSa = XS - 180
        except:
            # get the traceback object
            gp.AddError(traceerr(sys.exc_info()[2]))
            gp.AddMessage("Problem getting the start and end points of line.")
            gp.AddMessage(gp.GetMessages())
            raise SystemError     
    
        # start an update cursor on the structure points
        rows = gp.UpdateCursor(Zpts)
        row = rows.Next()
        while row:
            # check the strike and dip values, skip to next row if invalid
            if checkvalues(row) == "true":
                s = float(row.GetValue(strike))
                d = float(row.GetValue(dip))
                # calculate the bearing of the segment of the cross-section line the point has been placed on
                # based on the 'NEAR_ANGLE' value calculated by the near analysis
                n_ang = int(round(row.GetValue("NEAR_ANGLE"), 0))
                if n_ang == 0:
                    b = 90

                if 0 < n_ang <= 90:
                    n_ang = 90 - n_ang
                    b = n_ang + 90

                if 90 < n_ang <= 180:
                    n_ang = 360 - (n_ang - 90)
                    b = (n_ang + 90) - 360

                if -180 <= n_ang < 0:
                    n_ang = 90 + abs(n_ang)
                    b = n_ang - 90

                # find the acute angle between strike and bearing of the cross-section segment
                if abs(b - s) > 90:
                    acute = abs((b + 180) - s)
                else:
                    acute = abs(b - s)

                # calculate the apparent dip
                ApDip = math.atan(math.tan(d * d2r) * math.sin(acute * d2r)) * r2d
                # calculate the apparent dip with VE
                VEDip = math.atan(float(ve) * math.tan(ApDip * d2r)) * r2d

                # find the dip direction
                if s + 90 >= 360:
                    dd = float(90 - (360 - s))
                else:
                    dd = float(s + 90)

                # The apparent dip (ApDip) is an angle between 0 and 90 regardless of the true dip
                # direction. If the dip direction is within 90 degrees of the bearing of the cross-
                # section (XS), than VEDip is the angle of rotation of the dip symbol in cross-
                # sectional view. If not, the rotation angle is VEDip + 180.
                # Use geographic rotation to rotate dip symbol.
                # First, if XS minus 90 degrees is a ray in the IVth quadrant then compare the strike
                # to XSa
                if (XS - 90) < 0:
                    if ((XSa - 90) < dd < (XSa + 90)):
                        DipRot = 270 - float(VEDip)
                    else:
                        DipRot = float(VEDip) + 90
                else:
                    if (XS - 90) < dd < (XS + 90):
                        DipRot = float(VEDip) + 90
                    else:
                        DipRot = 270 - float(VEDip)

                # update the row
                row.SetValue("DipDir", float(dd))
                row.SetValue("ApDip", ApDip) #round(ApDip, 2))
                row.SetValue("VEDip", VEDip) #round(VEdip, 2))
                row.SetValue("DipRot", DipRot) #round(DipRot, 2))
                rows.UpdateRow(row)
            row = rows.Next()
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Problem calculating apparent dips!")
        gp.AddMessage(gp.GetMessages())
        raise SystemError

def checkvalues(row):
    check = "true"
    try:
        s = float(row.GetValue(strike))
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Strike value for FID " + row.fid + "is not valid.")
        check = "false"
    
    try:
        d = float(row.GetValue(dip))
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Dip value for FID " + row.fid + "is not valid.")
        check = "false"
    del s, d
    return check

def LocateStxPoints(ptsLayer, MZline, NameField, buff, pref):
    outTbl = pref + "LocateStxPts.dbf"
    try:
        gp.AddMessage("Locating structural points within " + buff + " of cross section...")
        gp.LocateFeaturesAlongRoutes_lr(ptsLayer, MZline, NameField, buff, outTbl, "rkey POINT RouteM", "#", "NO_DISTANCE")
        return outTbl
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Can't intersect " + pref + "MZline with structural points layer!")
        gp.AddMessage(gp.GetMessages())
        raise SystemError

def distbearing(firstx, firsty, lastx, lasty):
    try:
        # returns the bearing of a point (lastx, lasty) from a benchmark (firstx, firsty)
        # I think this is a snippet from some code written by David Finlayson - ET
        delx = (lastx - firstx)
        dely = (lasty - firsty)
        
        # Calculate the bearing (right-triangle)
        if (delx == 0 and dely == 0):
            bearing = None
        else:
            angle = math.atan2(dely, delx)
            angle = math.degrees(angle)
            bearing = (90 - angle) + 360.0
            bearing = bearing % 360	
        return bearing
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))

def PlaceStxEvents(rt, rid, tbl, pref):
    outfile = pref + "StxEvents.shp"
    try:
        gp.AddMessage("Placing structural points on surface profile...")
        # can't use angle parameters of MakeRouteEventLayer, known bug at 9.2
        gp.MakeRouteEventLayer_lr(rt, rid, tbl, "rkey POINT RouteM", "lyr")
        gp.AddMessage("Copying temporary features to " + gp.Workspace + "\\" + outfile)
        gp.CopyFeatures("lyr", outfile)
        return outfile
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Problem placing structural data points!")
        gp.AddMessage(gp.GetMessages())
        raise SystemError

def Plan2Side(inlayer, ve, snap, pref, outdir):
    outname = pref + "StxPoints.shp"
    try:
        gp.AddMessage("Creating output structural points shapefile...")
        # create the output feature class
        outfc = gp.CreateFeatureClass_management(outdir, outname, "POINT", inlayer, "ENABLED", "ENABLED")

        # create short list of fields to ignore when moving field
        # values from input to output
        ignoreFields = []
        # use describe properties to identify the ShapeFieldName and OIDFieldName
        desc = gp.Describe(inlayer)
        ignoreFields.append(desc.ShapeFieldName)
        ignoreFields.append(desc.OIDFieldName)
        
        # create a list of fields to use when moving field values from input to output)
        fields = gp.ListFields(inlayer)
        field = fields.Next()
        fieldList = []
        while field:
            if field.Name not in ignoreFields:
                fieldList.append(field.Name)
            field = fields.Next()
        
        # open search cursor on the input layer
        inRows = gp.SearchCursor(inlayer)
        inRow = inRows.Next()

        # open insert cursor on the output layer
        outRows = gp.InsertCursor(outfc)

        # create point object
        pntObj = gp.CreateObject("Point")
        
        # enter while loop for each input feature/row
        gp.AddMessage("Flipping " + inlayer + " to cross-sectional view...")
        while inRow:
            # create the geometry object
            inShape = inRow.Shape

            # assuming only one part per feature
            pnt = inShape.GetPart(0)
            
            # swap m for x
            pntObj.X = pnt.m

            # "snap" point to cross-section line?
            if snap == "true":
                # if true, use the z of the point as calculated during location of events on
                # cross-section line
                pntz = pnt.z
            else:
                # if false, use the DEM_Z value of the point as calculated in
                pntz = inRow.GetValue("DEM_Z")

            # calculate outputY from inputZ and ve    
            pntObj.Y = pntz * float(ve)

            # create new row for output feature
            feat = outRows.NewRow()
            
            # shift attributes from input to output
            for fieldName in fieldList:
                feat.SetValue(fieldName, inRow.GetValue(fieldName))
            
            # assign new point object to the shape field of the output feature
            feat.Shape = pntObj
            
            # insert the feature
            outRows.InsertRow(feat)

            # get the next feature in searchcursor
            inRow = inRows.Next()

        del inRows, outRows, pnt, pntObj
        
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        del inRows, outRows
        gp.AddMessage(gp.GetMessages())
        raise SystemError

def cleanup(keepf, pref, outdir):
    try:
        if keepf == "false":
            gp.delete(outdir + "\\" + pref + "ZXS.shp")
            gp.delete(outdir + "\\" + pref + "MZXS.shp")
            gp.delete(outdir + "\\" + pref + "ZStx.shp")
            gp.delete(outdir + "\\" + pref + "LocateStxPts.dbf")
            gp.delete(outdir + "\\" + pref + "StxEvents.shp")
            gp.AddMessage("Intermediate files deleted.")
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Problem cleaning up intermediate files!")
        gp.AddMessage(gp.GetMessages())

def traceerr(tb):
    # tbinfo contains the line number that the code failed on and the code from that line
    tbinfo = traceback.format_tb(tb)[0]
    # concatenate information together concerning the error into a message string
    pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo
    return pymsg        

# PARAMETERS
# ***************************************************************
# Cross-section(s) layer
lineLayer = gp.GetParameterAsText(0)

#might be a path, so we have to get the name of the file
if os.path.isabs(lineLayer):
    lineLayer = os.path.splitext(os.path.basename(lineLayer))[0]

#can't figure out how to put this in the validator class ??
result = arcpy.GetCount_management(lineLayer)
if int(result.getOutput(0)) > 1:
    arcpy.AddError(lineLayer + ' has more than one line in it.')
    raise SystemError

# elevation raster layer
dem = gp.GetParameterAsText(1)

#coordinate priority - corner from which the measuring will begin
cp = getCPValue(arcpy.GetParameterAsText(2))

# structural data points layer
ptsLayer = gp.GetParameterAsText(2)

# strike field
strike = gp.GetParameterAsText(3)

# dip field
dip = gp.GetParameterAsText(4)

# buffer distance
buff = gp.GetParameterAsText(5)


# vertical exaggeration
ve = gp.GetParameterAsText(7)
# files prefix
pref = gp.GetParameterAsText(8)
pref = pref + "_"
# output directory
outdir = gp.GetParameterAsText(9)

# BEGIN
# ***************************************************************
try:
    #check for 3DAnalyst extension
    checkExtensions()
r

# set the workspace to the output directory so that we
# don't need to include outdir in output pathnames
gp.workspace = outdir

# check inputs
checkinputs(xsecLayer, DEM, ptsLayer)
    
# make a temporary layer in memory with just one cross section line based on the SQL expression
try:
    gp.AddMessage("Making line layer in memory...")
    if sql == "":
        gp.MakeFeatureLayer(xsecLayer, "lyr")
    else:
        gp.MakeFeatureLayer(xsecLayer, "lyr", sql)
        
    if gp.GetCount_management("lyr") > 1:
        gp.AddMessage("SQL expression failed to select only one line!")
        raise SystemError
    
except:
    gp.AddMessage("Problem making temporary line layer from " + xsecLayer)
    gp.AddMessage(gp.GetMessages())
    raise SystemError
        
# interpolate line to 3d
Zline = interpolate(DEM, "lyr", pref, "ZXS.shp")
gp.AddMessage(pref + "ZXS.shp created in " + outdir)

# measure the Zline
MZline = measureZline(Zline, NameField, pref)
gp.AddMessage(pref + "MZXS.shp created in " + outdir)

# select the points based on the buffer distance
try:
    gp.AddMessage("Selecting structural data within " + buff  + " of cross-section...")
    gp.SelectLayerByLocation(ptsLayer, "WITHIN_A_DISTANCE", MZline, buff)
except:
    gp.AddMessage("Could not select points!")
    gp.AddMessage(gp.GetMessages())
    raise SystemError

# Get Z values for the points off the DEM
Zpts = interpolate(DEM, ptsLayer, pref, "ZStx.shp")
gp.AddMessage(pref + "Zstx.shp created in " + outdir)

# If 'snap' is false, the user wants to use the true elevations of the structure points
# in the cross-sectional view. The Z value does not carry through to the creation of the
# route event layer, so we have to add it explicitly to the table
# If 'snap' is true, the route event points will pick up the Z
# of the point on the interpolated cross-section line
# Add true z values to ZStx.shp
AddZ(Zpts)

# clear the selection of structural points
try:
    gp.SelectLayerByAttribute(ptsLayer, "CLEAR_SELECTION")
except:
    gp.AddMessage("Problem clearing the selection of points in " + ptsLayer)
    gp.AddMessage(gp.GetMessages())
    raise SystemError

# run near_analysis on points
# the only value this analysis returns that I am really interested in is the
# NEAR_ANGLE value from which I will calculate the bearing of the cross-section
# line segment nearest the point
try:
    gp.near_analysis(Zpts, MZline, "#", "LOCATION", "ANGLE")
except:
    gp.AddMessage("Problem running near analysis on points.")
    gp.AddMessage(gp.GetMessages())
    
# calculate apparent dip now that we have a location angle
CalcApDips(Zpts, "lyr", strike, dip, ve)

# locate structural points along cross section
StxEventsTab = LocateStxPoints(Zpts, MZline, NameField, buff, pref)
gp.AddMessage(pref + "LocateStxPts.dbf created in " + outdir)
 
# place structural points along route and write temp layer file to shapefile
StxPtsEvents = PlaceStxEvents(MZline, NameField, StxEventsTab, pref)
gp.AddMessage(pref + "StxEvents.shp created in " + outdir)

# flip coordinates to cross sectional view
Plan2Side(StxPtsEvents, ve, snap, pref, outdir)
gp.AddMessage(pref + "StxPoints.shp created in " + outdir)

# cleanup if required
cleanup(keepf, pref, outdir)
