# 3Dborehole.py
# Description: ArcToolbox tool script to plot 3D borehole lines from a
#   point layer of borehole locations and a related table of
#   borehole intervals for viewing in ArcScene
# Requirements: python, 3D Analyst extension, ArcInfo license
# Author: Evan Thoms, U.S. Geological Survey, ethoms@usgs.gov
# Date: 8/13/07

# code to add, maybe:
# although overwriteoutput may be set to true, gp can't delete
# those files if they have a schema lock on them from another program
# say, for instance, the user opened a file in ArcCatalog from the
# last run to check it out or to try to add a file.
# can gp report error that the file has a schema lock on it? I haven't
# seen this.
##def trydelete(dataset):
##    test = gp.TestSchemaLock(dataset)
##    if test == "true":
##        gp.delete(gp.workspace + "\\" + dataset)
##    else:
##        gp.AddMessage("Can't delete intermediate file " + dataset)
##        gp.AddMessage("Make sure all other programs that may have a")
##        gp.AddMessage("  schema lock on it are closed.")
##        raise SystemError

# Import modules
import arcgisscripting

# Create the Geoprocessing object
gp = arcgisscripting.create()
# overwrite intermediate files
gp.overwriteoutput = 1

# FUNCTIONS
# *******************************************************
def checkinputs(raster, pointlayer):
    try:
        gp.AddMessage("Checking inputs...")
        if not (gp.describe(raster).DatasetType == "RasterDataset"):
            gp.AddMessage("DEM input is not a raster layer!")
            raise SystemError

        if not (gp.describe(pointlayer).ShapeType == "Point"):
            gp.AddMessage("Borehole layer input is not a point layer!")
            raise SystemError
        
        # check that all layers have the same spatial reference
        # use the DEM SR to compare others against
        sr1 = gp.Describe(raster).SpatialReference.Name
        layerlist = [pointlayer]
        for layer in layerlist:
            sr2 = gp.Describe(layer).SpatialReference.Name
            if sr1 <> sr2:
                gp.AddMessage("Input layers do not share the same spatial reference!")
                raise SystemError
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
            
def interpolate(DEM, feat, pref):
    # set the output shapefile name
    outZfeat = pref + "Zbhpts.shp"
    try:
        gp.AddMessage("Getting elevation values for selected features...")
        gp.Interpolateshape_3d(DEM, feat, outZfeat)
        return outZfeat
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Can't interpolate values!")

def AddZ(Zbhpts):
    try:
        gp.AddField(Zbhpts, "DEM_Z", "DOUBLE")
        rows = gp.UpdateCursor(Zbhpts)
        row = rows.Next()
        while row:
            # create the geometry object
            feat = row.Shape
            pnt = feat.GetPart()
            # set the value
            row.SetValue("DEM_Z", pnt.Z)
            # update the row
            rows.UpdateRow(row)
            row = rows.next()
            
        # delete cursor and row objects    
        del rows, row
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Could not update table with 'DEM_Z' values!")
        gp.AddMessage(gp.GetMessages())
        raise SystemError

def makebhlines(Zbhpts, bhZ, bhDepth, pref, outdir):
    outname = pref + ("3DBHlines.shp")
    try:
        # create the output shapefile
        gp.AddMessage("Creating " + outname + " in " + outdir)
        sr = gp.describe(Zbhpts).SpatialReference
        outfc = gp.CreateFeatureClass_management(outdir, outname, "POLYLINE", Zbhpts, "ENABLED", "ENABLED", sr)

        # create short list of fields to ignore when moving field
        # values from input to output
        ignoreFields = []
        # use describe properties to identify the ShapeFieldName and OIDFieldName
        desc = gp.Describe(Zbhpts)
        ignoreFields.append(desc.ShapeFieldName)
        ignoreFields.append(desc.OIDFieldName)
        
        # create a list of fields to use when moving field values from input to output)
        fields = gp.ListFields(Zbhpts)
        field = fields.Next()
        fieldList = []
        while field:
            if field.Name not in ignoreFields:
                fieldList.append(field.Name)
            field = fields.Next()
            
        # open search cursor on the interpolated point layer
        scur = gp.SearchCursor(Zbhpts)
        srow = scur.Next()

        # open insert cursor on the output layer
        icur = gp.InsertCursor(outfc)

        # create point and array objects
        pnt1 = gp.CreateObject("Point")
        pnt2 = gp.CreateObject("Point")
        array = gp.CreateObject("Array")

        gp.AddMessage("Building 3D boreholes from interpolated borehole layer...")

        # enter while loop for each row in events table
        while srow:
            # set the coordinates
            # X and Y come from the input point
            # get the geometry object
            feat = srow.GetValue(desc.ShapeFieldName)
            pnt = feat.GetPart()
            # coordinates of the top of the borehole line
            pnt1.x = pnt.x
            pnt1.y = pnt.y
            # Z comes from the DEM_z (or CollarZ)
            if bhZ == "":  # if the parameter is empty
                pnt1.z = float(srow.GetValue("DEM_Z"))
            else:
                gp.AddMessage("bhZ")
                pnt1.z = float(srow.GetValue(bhZ))

            # coordinates of the bottom of the borehole line
            pnt2.x = pnt.x
            pnt2.y = pnt.y - .01
            pnt2.z = float(pnt1.z - float(srow.GetValue(bhDepth)))

            # add points to array
            array.add(pnt1)
            array.add(pnt2)

            # set array to the new feature's shape
            feat = icur.NewRow()
            feat.shape = array

            # shift attributes from table to output fc
            for fieldName in fieldList:
                feat.SetValue(fieldName, srow.GetValue(fieldName))

            # insert the feature
            icur.InsertRow(feat)
            array.RemoveAll()

            # get the next row in the table
            srow = scur.Next()
        return outname

    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Problem building lines from " + pref + "Zbhpts.shp")
        gp.AddMessage(gp.GetMessages())
        raise SystemError

def makeroutes(lines, rkey, bhDepth, pref):
    outroutes = pref + "3DBHroutes.shp"
    try:
        gp.AddMessage("Measuring the length of lines in " + lines + "...")
        gp.CreateRoutes_lr(lines, rkey, outroutes, "ONE_FIELD", bhDepth)

    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Can't turn " + lines + " into a route.")
        raise SystemError
    return outroutes

def placeintervals(rts, rid, tbl, tblid, fmp, tmp, pref):
    try:
        gp.AddMessage("Placing intervals on borehole lines...")
        props = tblid + " LINE " + fmp + " " + tmp
        gp.MakeRouteEventLayer_lr(rts, rid, tbl, props, "lyr")
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Can't place intervals from table onto borehole lines.")
        gp.AddMessage(gp.GetMessages())
        raise SystemError

    outfc = pref + "3Dboreholes"
    try:    
        gp.AddMessage("Saving temp layer as shapefile...")
        gp.CopyFeatures("lyr", outfc)
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Problem saving temp layer to shapefile.")
        raise SystemError

def cleanup(keepf, pref, outdir):
    try:
        if keepf == "false":
            gp.delete(outdir + "\\" + pref + "Zbhpts.shp")
            gp.delete(outdir + "\\" + pref + "3DBHlines.shp")
            gp.delete(outdir + "\\" + pref + "3DBHroutes.shp")
            gp.AddMessage("Intermediate files deleted.")
    except:
        # get the traceback object
        gp.AddError(traceerr(sys.exc_info()[2]))
        gp.AddMessage("Problem cleaning up intermediate files.")
        gp.AddMessage(gp.GetMessages())

def traceerr(tb):
    # tbinfo contains the line number that the code failed on and the code from that line
    tbinfo = traceback.format_tb(tb)[0]
    # concatenate information together concerning the error into a message string
    pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo
    return pymsg        

# PARAMETERS
# *******************************************************
# structural data points layer
bhlayer = gp.GetParameterAsText(0)
# borehole id field
bhidField = gp.GetParameterAsText(1)
# collar Z field
bhZ = gp.GetParameterAsText(2)
# depth field
bhDepth = gp.GetParameterAsText(3)
# elevation raster layer
DEM = gp.GetParameterAsText(4)
# intervals table
inttbl = gp.GetParameterAsText(5)
# borehole id field in interval table
intbhidField = gp.GetParameterAsText(6)
# interval top depth - depth in relation to the top of the borehole, not elevation
# if left blank will interpolate elevation from DEM
intTopDepth = gp.GetParameterAsText(7)
# interval bottom depth
intBotDepth = gp.GetParameterAsText(8)
# prefix for output filenames
pref = gp.GetParameterAsText(9)
pref = pref + "_"
# output directory
outdir = gp.GetParameterAsText(10)
#keep intermediate files?
keepf = gp.GetParameterAsText(11)

# BEGIN
# *******************************************************
# Check for ArcInfo license
if gp.CheckProduct("ArcInfo") <> "Available":
    gp.AddMessage("ArcInfo license is required to run this tool.")
    raise SystemError

# Check for the 3d Analyst extension
#gp.CheckExtension(3)
if gp.CheckExtension("3D") == "Available":
    try:
        gp.CheckOutExtension("3D")
    except:
        gp.AddMessage("3D Analyst extension is unavailable")
        gp.AddMessage(gp.GetMessages())
        raise SystemError

# set the workspace to the output directory so that we
# don't need to include outdir in output pathnames
gp.workspace = outdir

# check inputs
checkinputs(DEM, bhlayer)

# Get Z values for the boreholes off the DEM
Zbhpts = interpolate(DEM, bhlayer, pref)
gp.AddMessage(pref + "Zbhpts.shp created in " + outdir)

# Add DEM Z values to Zbhpts.shp attribute table
AddZ(Zbhpts)

# make the borehole lines to be used as routes
bhlines = makebhlines(Zbhpts, bhZ, bhDepth, pref, outdir)
gp.AddMessage(pref + "3DBHlines.shp created in " + outdir)

# convert to routes
bhroutes = makeroutes(bhlines, bhidField, bhDepth, pref)
gp.AddMessage(pref + "3DBHroutes.shp created in " + outdir)

# place borehole intervals (line events) on borehole routes
placeintervals(bhroutes, bhidField, inttbl, intbhidField, intTopDepth, intBotDepth, pref)
gp.AddMessage(pref + "3Dboreholes.shp created in " + outdir)