# qgis_nearest_greater
QGIS Plugin to get ID of and distance to the nearest feature with greater value in a certain field of a point layer.

Get ID of and distance to the nearest neighbour with greater value in a certain field. Input is a points layer. 
The main output is a points layer with added attributes nearest_gt_dist and nearest_gt_id.
Also returns a lines layer with connecting lines, as well as basic statistics of the distances (min, max, mean, quantiles).

Use cases: 
- Which is the next larger city? 
- Which is the closest peak with higher elevation? 
- Useful for spatial analysis or to categorize features in order to apply different styles (e.g. major and minor summits). 

