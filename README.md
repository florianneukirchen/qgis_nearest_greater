# qgis_nearest_greater
QGIS Plugin to get name (or ID) of and distance to the nearest feature with greater value in a certain field of a point layer.

- Homepage: [https://www.riannek.de/code/qgis-nearest-with-greater/](https://www.riannek.de/code/qgis-nearest-with-greater/)
- Sourcecode: [https://github.com/florianneukirchen/qgis_nearest_greater](https://github.com/florianneukirchen/qgis_nearest_greater)
- QGIS Plugin Repository: https://plugins.qgis.org/plugins/qgis_nearest_greater/
- Bug Tracker: https://github.com/florianneukirchen/qgis_nearest_greater/issues


## About
Get name (or ID) of and distance to the nearest neighbour with greater value in a certain field. Input is a points layer. 
The main output is a points layer with added attributes 'neargtdist' (distance), 'neargtdelta' (difference of both values), 'neargtname' (name/ID) and 'neargtcount'. The field 'neargtcount' 
gives the count of incoming connecting lines linking to points with smaller value.
Also returns a lines layer with connecting lines, as well as basic statistics of the distances (min, max, mean, quartiles). 

Use cases: 
- Which is the next larger city? 
- How far away is the next higher building?
- Which is the closest peak with higher elevation? 
- Useful for spatial analysis 
- Useful to categorize features in order to apply different styles (e.g. major and minor summits). 

## Changelog

### 1.0 (2022-10)
- Add additional output field neargtdelta with the diffence of both values
- Calculate statistics for delta
- Improve strings in the UI

### 0.3 (2022-09)
- Fix a bug by changing the names of added fields to neargtdist, neargtname, neargtcount: Don't use underscore. Before, they were renamed by QGSIS when the layer was saved to a shapefile.

### 0.2 (2022-09)
- Return additional field 'neargtcount' with a count of the incoming links (i.e. connecting lines from points with smaller value)
- Better handling of the distance value for the feature with greatest value. Three options: "NULL", "1 Mio.", "max distance + 1".
- Warn if the selected name field contains NULL or non-unique values
- Add short help string

### 0.1 (2022-09)
- Initial release


