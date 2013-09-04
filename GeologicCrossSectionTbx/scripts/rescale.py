# changeve.py
# Description: ArcToolbox tool script to rescale one or more layers in the
#  X and/or Y direction. Principally intended for changing the vertical
#  exaggeration of cross-section layersi
# Requirements: python 2.5 or greater
# Author: Evan Thoms, U.S. Geological Survey, ethoms@usgs.gov
# Date: 8/18/07
# some edits 7/19/10
#
#Upgraded to ArcGIS 10 and arcpy module on 3/25/11


# Import modules
import arcpy
import string
import sys
import traceback 

#errors during testing were not getting reported with this function
#works in other scripts ??!!
def tracebackReport():
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    pymsg = tbinfo + '\n' + str(sys.exc_type)+ ': ' + str(sys.exc_value)
    arcpy.AddError(pymsg)
    raise SystemError

arcpy.env.overwriteOutput = True

# PARAMETERS
# *******************************************************
# one or more layers in cross-section view, multi-value input
xslayers = string.split(arcpy.GetParameterAsText(0), ';')

# factor by which to rescale in the Y direction
ve = arcpy.GetParameterAsText(1)

# factor by which to rescale in the X direction
he = arcpy.GetParameterAsText(2)


# BEGIN
# *******************************************************
try:
    for layer in xslayers:
        arcpy.AddMessage(layer)
                
        # open an update cursor
        upcur = arcpy.UpdateCursor(layer)
        shptype = arcpy.Describe(layer).ShapeType
                    
        # enter while loop for each feature/row
        for row in upcur:
            # Create the geometry object
            feat = row.shape
        
            #special (simple) case for points
            if shptype == 'Point':
                oldPnt = feat.GetPart(0)
                newPnt = arcpy.Point()
                newPnt.Y = float(oldPnt.Y) * float(ve)
                newPnt.X = float(oldPnt.X) * float(he)
                row.shape = newPnt
                upcur.updateRow(row)
        
                        
            #lines and polygons
            else:
                new_Feat_Shape = arcpy.Array()
                a = 0
                while a < feat.partCount:
                    # Get each part of the geometry)
                    array = feat.getPart(a)
                    newarray = arcpy.Array()
                                                    
                    # otherwise get the first point in the array of points
                    pnt = array.next()
                                    
                    while pnt:
                        pnt.Y = float(pnt.Y) * float(ve)
                        pnt.X = float(pnt.X) * float(he)
                                    
                        #Add the modified point into the new array
                        newarray.add(pnt)
                        pnt = array.next()
            
                    #Put the new array into the new feature  shape
                    new_Feat_Shape.add(newarray)
                    a = a + 1
                                
                #Update the row object's shape  
                row.shape = new_Feat_Shape
                
                #Update the feature's information in the workspace using the cursor
                upcur.updateRow(row)

except:
    #del upcur
    tracebackReport