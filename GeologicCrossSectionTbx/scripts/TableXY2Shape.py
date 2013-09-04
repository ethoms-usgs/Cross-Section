"""
TableXY2Shape.py
A script that reads the 'latitude' and 'longitude' fields in
C:\Workspace\PNW\Edmonds\Geology\Edmonds.gdb\Geology\Boreholes,
updates the geometry to those values, and re-writes the
'Easting' and 'Northing' fields.
"""

import arcpy

#fc = r'C:\Documents and Settings\ethoms\My Documents\ArcGIS\Default.gdb\Export_Output'
fc = r'C:\Workspace\PNW\Edmonds\Geology\Edmonds.gdb\Geology\Boreholes'

WGS84 = arcpy.CreateSpatialReference_management(r'C:\ArcGIS\Desktop10.0\Coordinate Systems\Geographic Coordinate Systems\World\WGS 1984.prj')

rows = arcpy.UpdateCursor(fc, '', WGS84)
for row in rows:
    if row.Longitude:
        lon = row.Longitude
        lat = row.Latitude
        pt = arcpy.CreateObject('point')
        pt.X = lon
        pt.Y = lat
        row.Shape = pt
        rows.updateRow(row)
        print row.Shape.getPart().X, row.Shape.getPart().Y
        row.Easting = row.Shape.getPart().X
        row.Northing = row.Shape.getPart().Y
        rows.updateRow(row)
