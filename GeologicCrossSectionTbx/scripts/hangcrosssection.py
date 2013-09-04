# hangcrosssection.py
# Description: ArcToolbox tool script to convert cross-sectional view
#   feature coordinates to real-world coordinates 
# Requirements: python, 3D Analyst extension, ArcInfo license
# Author: Evan Thoms, U.S. Geological Survey, ethoms@usgs.gov
# Date: 8/14/07

# Import modules
import arcgisscripting, string
import sys, traceback  # for error handling
from shutil import copy

# Create the Geoprocessing object
gp = arcgisscripting.create()
# overwrite intermediate files
gp.overwriteoutput = 1

# FUNCTIONS
# ***************************************************************
def addtracking(layer, xsid):
    try:
        # add fields to store the new values necessary to rebuild the features in the hung view
        gp.AddMessage("Adding tracking attributes to %s..." % layer)
        
        # check for the existence of the fields
        if not gp.listfields(layer, "OrigID").Next():  # if the list object cannot return a single value it couldn't find the name
            gp.AddField(layer, "OrigID", "SHORT")
        if not gp.listfields(layer, "Shape").Next():
            gp.AddField(layer, "OrigShape", "TEXT", "#", "#", 10)
        if not gp.listfields(layer, "rkey").Next():
            gp.AddField(layer, "rkey", "TEXT")
            
        rows = gp.UpdateCursor(layer)
        row = rows.Next()
        shape = gp.describe(layer).ShapeType
        while row:
            # add the OID, ShapeType, and routekey values
            row.SetValue("OrigID", row.GetValue(gp.describe(layer).OIDFieldName))
            row.SetValue("OrigShape", shape)
            row.SetValue("rkey", xsid)
            rows.UpdateRow(row)
            row = rows.Next()
        return "success"
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))

        # add message specific to this def
        gp.AddMessage("Could not add tracking attribute fields to %s." % layer)
        gp.AddMessage(gp.GetMessages())
        return "fail"


def conv2pts(layer):
    try:
        outname = layer + "_pts.shp"
        st = gp.describe(layer).ShapeType
        if st == "Point":
            # all we have to do is make a copy with the M-enabled environment set to enable
            # space for the M value (added in def AddM)
            gp.AddMessage("Copying %s to M-enabled file (%s)" % (outfc, outname))
            outfc = gp.copy(layer, outname)
        else:
            gp.AddMessage("Converting %s to point shapefile (%s)" % (layer, outname))
            gp.FeatureVerticesToPoints(layer, outname, "ALL")
        return "success"

    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        
        # add message specific to this def
        gp.AddMessage("Can't convert %s to point shapefile") % outname
        gp.AddMessage(gp.GetMessages())
        return "fail"


def AddMY(layer):
    try:
        gp.AddMessage("Adding M and Z values to %s_pts.shp..." % layer)
        mlyr = layer + "_pts.shp"
        
        # add the XSY field
        gp.AddField(mlyr, "MapViewZ", "DOUBLE")
        
        # add the FromM field
        gp.AddField(mlyr, "MapViewM", "DOUBLE")

        # add the MLyrFID field
        gp.AddField(mlyr, "MLyrFID", "SHORT")

        # create the row enumeration
        rows = gp.UpdateCursor(mlyr)
        row = rows.Next()
        shapefn = gp.describe(mlyr).ShapeFieldName

        # update the M and Z values
        while row:
            # create the geometry object
            feat = row.GetValue(shapefn)
            pnt = feat.GetPart()
            # add the map view M value (the X value of the feature in XS view),
            row.SetValue("MapViewM", pnt.x)
            # ...the map view Z value (the Y value of the feature in XS view)
            row.SetValue("MapViewZ", pnt.y)
            # ...and the FID of this feature so that we sort on this value when rebuilding
            row.SetValue("MLyrFID", row.GetValue(gp.describe(mlyr).OIDFieldName))
            rows.UpdateRow(row)
            row = rows.Next()
        return "success"
    
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))

        # add message specific to this def
        gp.AddMessage("Couldn't add M and Z values to %s_pts.shp!" % layer)
        gp.GetMessages()
        return "fail"


def MakeEventLyr(layer, NameField):
    try:
        gp.AddMessage("Placing points from %s_pts.shp onto cross-section line..." % layer)
        rt = "MXS.shp"
        rid = NameField
        tbl = layer + "_pts.dbf"
        props = "rkey POINT MapViewM"
        lyr = layer + "_ev"
        gp.MakeRouteEventLayer_lr(rt, rid, tbl, props, lyr)

        # if the proto shape is point, write to a permanent shapefile,
        # this is the new geometry.
        cur = gp.searchcursor(tbl)
        row = cur.next()
        shape = row.getvalue("OrigShape")
        if shape.lower() == "point":
            gp.copyfeatures(lyr, layer + "_ev.shp")
        
        return "success"
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))

        # add message specific to this def
        gp.AddMessage("Problem placing points from %s_pts.shp" % layer)
        gp.AddMessage(gp.GetMessages())
        return "fail"


def XYZGenerate(layer, ve):
    try:
        # open a search cursor on the events layer
        evlyr = layer + "_ev"
        rows = gp.SearchCursor(evlyr, "", "", "", "MLyrFID")
        row = rows.next()
        # get the proto-layer shape type
        # write the geometry to a text file
        # points are addressed in Rebuild
        shape = row.getvalue("OrigShape")

        # polylines and polygons we will take care of here
        if shape.lower() == "polyline" or shape.lower() == "polygon":
            gp.AddMessage("Writing geometry for %s_ev out to a XYZ generate text file..." % layer)
            # open a text file
            xyz = gp.workspace + "\\" + layer + "_gen.txt"
            outf = open(xyz, "w")

            # create a point object
            pnt = gp.createobject("point")
            
            # initialize a variable to keep track of feature IDs
            ID = 0
            outf.write("0\n")

            # enter row loop
            while row:
                # create the geometry object
                feat = row.shape
                pnt = feat.getpart()
                x = row.getvalue("origid")
                # divide the z value by the vertical exaggeration factor
                z = int(row.getvalue("mapviewz"))/int(ve)
                if x == ID:
                    outf.write(str(pnt.x) + " " + str(pnt.y) + " " + str(z) + "\n")
                else:
                    outf.write("END\n")
                    outf.write(str(row.getvalue("origid")) + "\n")
                    outf.write(str(pnt.x) + " " + str(pnt.y) + " " + str(z) + "\n")
                    ID = ID + 1
                row = rows.next()

            # need one last END at the end of the file
            outf.write("END\n")
            outf.write("END")
            outf.close()
            return "success"

    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))

        # add message specific to this def
        gp.AddMessage("Problem writing %s events layer to XYZ generate file." % layer)
        gp.AddMessage(gp.GetMessages())
        return "fail"


def Rebuild(layer, XSecLayer, ve):
    try:
        gp.AddMessage("Building final 3D features from input %s" % layer)
        # get the proto-shape
        cur = gp.searchcursor(layer + "_pts.shp")
        row = cur.next()
        shape = row.getvalue("OrigShape")

        # if the proto-shape is point, just update the z of the point in the events shapefile
        if shape.lower() == "point":
            evlyr = layer + "_ev.shp"
            upRows = gp.UpdateCursor(evlyr)
            upRow = upRows.Next()
            pnt = gp.CreateObject("point")
            while row:
                # create the geometry object
                feat = upRow.shape
                pnt = feat.getpart()
                # set the Z value
                upRow.SetValue(pnt.x, row.getvalue("MapViewZ")/ve)
                upRow.UpdateRow(upRow)
                upRow = upRows.Next()
            
            # write the results to a permanent shapefile
            outf = layer + "_3D.shp"
            gp.CopyFeatures(evlyr, outf)
            
            # delete the extra processing fields
            gp.deletefield_management(outf, "rkey; OrigID; OrigShape")
            return "success"
        
        # if proto-shape is polyline or polygon, build the features from the XYZ generate files
        elif shape.lower() == "polyline" or shape.lower() == "polygon":

            # Check for the 3d Analyst extension
            if gp.CheckExtension("3D") == "Available":
                try:
                    gp.CheckOutExtension("3D")
                except:
                    # get the traceback object
                    gp.AddError(traceerr(sys.exc_info()[2]))
                    gp.AddMessage("3D Analyst extension is unavailable.")
                    gp.AddMessage(gp.GetMessages())
                    return "fail"

            # continue
            genfile = layer + "_gen.txt"
            outshp = layer + "_3d.shp"
            gp.ascii3dtofeatureclass_3d(genfile, "generate", layer + "_3d.shp", shape)

            # copy the attribute table from the source to the newly created 3d shapefile
            copy(gp.workspace + "\\" + layer + ".dbf", gp.workspace + "\\" + layer + "_3d.dbf")

            # delete the extra processing fields
            gp.deletefield_management(layer + "_3d.shp", "rkey; OrigID; OrigShape")
            return "success"
            
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))

        # add message specific to this def
        gp.AddMessage("Problem rebuilding %s into 3D features..." % layer)
        gp.AddMessage(gp.getmessages())
        return "fail"

def cleanup(keepf, xslayers, outdir):
    gp.delete("MXS.shp")
    for layer in xslayers:
        try:
            if gp.exists(layer + "_pts.shp"):
                gp.delete(layer + "_pts.shp")
            if gp.exists(layer + "_M.shp"):
                gp.delete(layer + "_M.shp")
            
            # only exists for cross-section point layers
            if gp.exists(layer + "_ev.shp"):  
                gp.delete(layer + "_ev.shp")

            # gen.txt files only written for polyline and polygon layers
            if gp.exists(layer + "_gen.txt"):  
                gp.delete(layer + "_gen.txt")
            gp.AddMessage("")
            gp.AddMessage("*******************************************")
            gp.AddMessage("Intermediate files deleted.")
            return "success"
        
        except:
            # get the traceback object
            gp.AddError(traceerr(sys.exc_info()[2]))

            # add message specific to this def
            gp.AddMessage("")
            gp.AddMessage("*******************************************")
            gp.AddMessage("Problem deleting intermediate files.")
            gp.AddMessage("Problem cleaning up intermediate files!")
            gp.AddMessage(gp.GetMessages())
            return "fail"



def traceerr(tb):
    # tbinfo contains the line number that the code failed on and the code from that line
    tbinfo = traceback.format_tb(tb)[0]
    # concatenate information together concerning the error into a message string
    pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo
    return pymsg

# PARAMETERS
# ***************************************************************
# map view cross-section line layer
XSecLayer = gp.GetParameterAsText(0)
# id field of cross-section layer
NameField = gp.GetParameterAsText(1)
# SQL statement to select one line
sql = gp.GetParameterAsText(2)
# interpreted cross-sectional view layers, multi-value input
xslayers = string.split(gp.GetParameterAsText(3), ";")
# vertical exaggeration
ve = gp.GetParameterAsText(4)
# output directory
outdir = gp.GetParameterAsText(5)
# keep intermediate files boolean
keepf = gp.GetParameterAsText(6)

# BEGIN
# ***************************************************************
# set the workspace to the output directory
gp.workspace = outdir

# set environment variables
# feature classes are always m-enabled if they are z-enabled -- known bug!
# gp.OutputMFlag = "ENABLED"
# set output feature classes to be Z enabled
gp.OutputZFlag = "ENABLED"
gp.XYTolerance = 0.00001

try:
    gp.AddMessage("")
    gp.AddMessage("*******************************************")
    gp.AddMessage("Making line layer in memory...")
    if sql == "":
        gp.MakeFeatureLayer(XSecLayer, "lyr")
        rows = gp.SearchCursor("lyr")
        row = rows.Next()
        xsid = row.GetValue(NameField)
    else:
        gp.MakeFeatureLayer(XSecLayer, "lyr", sql)
        
    # check the results - one line only!
    if gp.GetCount_management("lyr") > 1:
        gp.AddMessage("SQL expression failed to select only one line!")
except:
    gp.AddMessage(gp.GetMessages())
    raise SystemError


# measure the cross section line
try:
    gp.AddMessage("Measuring the length of the cross section line...")
    gp.CreateRoutes_lr("lyr", NameField, "MXS.shp", "LENGTH")
except:
    gp.AddMessage("Can't turn " + XSecLayer + " into a route.")
    gp.AddMessage(gp.GetMessages())
    raise SystemError
gp.AddMessage("MXS.shp created in " + outdir)

# evaluate each layer in the list
i = 0
for layer in xslayers:
    gp.AddMessage("")
    gp.AddMessage("*******************************************")

    # add necessary fields and values to keep track of original feature geometry and ids
    if addtracking(layer, xsid) == "fail":
        success == "fail"
        break
    
    # convert each cross-section layer into points (if needed)
    if conv2pts(layer) == "fail":
        success == "fail"
        break

    # Add M and Z values to table of new point layer
    # M = cross-section view X and Z = cross-section view Y
    if AddMY(layer) == "fail":
        success == "fail"
        break

    # place points, as events, along the measured cross-section route
    if MakeEventLyr(layer, NameField) == "fail":
        success == "fail"
        break

    # make a XYZ Generate text file from the event layer
    if XYZGenerate(layer, ve) == "fail":
        success == "fail"
        break

    # run each XYZ Generate file through the ASCII 3D to Feature tool  
    if Rebuild(layer, XSecLayer, ve) == "fail":
        success == "fail"  
        break
            
    i = i + 1


gp.AddMessage("")
gp.AddMessage("*******************************************")
gp.AddMessage("Succeeded in converting %s layers" % i)

# clean up
if keepf == "false":
    if cleanup(keepf, xslayers, outdir) == "fail":
        raise SystemError
