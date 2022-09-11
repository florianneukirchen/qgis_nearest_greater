# -*- coding: utf-8 -*-

"""
/***************************************************************************
 NearestGreater
                                 A QGIS plugin
 Get name (or ID) of and distance to the nearest feature with greater value 
 in a certain field of a point layer. Returns point layer with added 
 attributes and a line layer with connecting lines.
                              -------------------
        begin                : 2022-09-07
        copyright            : (C) 2022 by Florian Neukirchen
        email                : mail@riannek.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Florian Neukirchen'
__date__ = '2022-09-07'
__copyright__ = '(C) 2022 by Florian Neukirchen'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from statistics import quantiles, mean
from qgis.PyQt.QtCore import QCoreApplication, QVariant, NULL
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterField,
                       QgsFields,
                       QgsField,
                       QgsFeature,
                       QgsExpression,
                       QgsFeatureRequest,
                       QgsSpatialIndex,
                       QgsProcessingOutputNumber,
                       QgsProcessingParameterNumber,
                       QgsGeometry,
                       QgsWkbTypes,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterEnum,
                       NULL)

class NearestGreaterAlgorithm(QgsProcessingAlgorithm):
    """
    Get name (or ID) of and distance to the nearest feature with greater value in a certain field of a point layer.
    
    Get name (or ID) of and distance to the nearest neighbour with greater value in a certain field. Input is a points layer. 
    The main output is a points layer with added attributes nearest_gt_dist and nearest_gt_name.
    Also returns a lines layer with connecting lines, as well as basic statistics of the distances (min, max, mean, quartiles).
    The distance to be returned for the feature with the greatest value can be set, 
    it should be 0 (replaced by NULL in the output) or a very large number.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = 'OUTPUT'
    INPUT = 'INPUT'
    COMPARE_FIELD = 'COMPARE_FIELD'
    DIST_FOR_MAX = 'DIST_FOR_MAX'
    LINEOUTPUT = 'LINEOUTPUT'
    KEEP = 'KEEP'
    NAME_FIELD = 'NAME_FIELD'


    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer'),
                [QgsProcessing.TypeVectorPoint]
            )
        )

        # Select the field containing values to be compared
        self.addParameter(
            QgsProcessingParameterField(
                self.COMPARE_FIELD,
                self.tr('Field with values to compare'),
                '',
                self.INPUT))


        # Set how distance for the feature with
        # the greatest value should be handled
        self.distoptions = ['NULL',
                            self.tr('1 Mio.'),
                            self.tr('max distance + 1')]

        self.addParameter( 
            QgsProcessingParameterEnum(
                self.DIST_FOR_MAX, 
                self.tr('Choose a distance value for the greatest feature'),
                options=self.distoptions,
                defaultValue='NULL'
                ))
          
      
        # Select the field of name or ID to identify nearest neighbor
        self.addParameter(
            QgsProcessingParameterField(
                self.NAME_FIELD,
                self.tr('Identify nearest greater neighbor by field'),
                '',
                self.INPUT))


        # Should features with NULL value be added to the output layer?
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.KEEP, 
                self.tr('Keep features with NULL value in output layer'),
                True))                
                
        # Add some additional output fields
        self.addOutput(
            QgsProcessingOutputNumber(
                'ID_MAX_VALUE',
                self.tr('ID of Feature with max value')
            ))

        self.addOutput(
            QgsProcessingOutputNumber(
                'NUMBER_PROCESSED_FEATURES',
                self.tr('Number of features that have been processed.')
            ))   


        self.addOutput(
            QgsProcessingOutputNumber(
                'NUMBER_IGNORED_FEATURES',
                self.tr('Number of ignored features with NULL values.')
            ))   

        self.addOutput(
            QgsProcessingOutputNumber(
                'MIN_DIST',
                self.tr('Smallest distance.')
            ))  

        self.addOutput(
            QgsProcessingOutputNumber(
                'MAX_DIST',
                self.tr('Largest calculated distance.')
            ))  

        self.addOutput(
            QgsProcessingOutputNumber(
                'MEAN_DIST',
                self.tr('Mean of calculated distances.')
            ))  

        self.addOutput(
            QgsProcessingOutputNumber(
                'Q1_DIST',
                self.tr('First quartile of distances.')
            ))  

        self.addOutput(
            QgsProcessingOutputNumber(
                'Q2_DIST',
                self.tr('Second quartile (median) of distances.')
            ))  

        self.addOutput(
            QgsProcessingOutputNumber(
                'Q3_DIST',
                self.tr('Third quartile of distances.')
            ))  

            

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output Nearest Greater')
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.LINEOUTPUT,
                self.tr('Lines Nearest Greater')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsSource(parameters, self.INPUT, context)

        # Get the parameters
        compare_field = self.parameterAsString(
            parameters,
            self.COMPARE_FIELD,
            context)

        name_field = self.parameterAsString(
            parameters,
            self.NAME_FIELD,
            context)

        # dist_for_max is the index of the options, range 0 to 2
        dist_for_max = self.parameterAsEnum(
            parameters,
            self.DIST_FOR_MAX,
            context)
            
        keep = self.parameterAsBoolean(
            parameters,
            self.KEEP,
            context)

            
        # Define fields
        out_fields = source.fields()
        out_fields.append(QgsField('nearest_gt_dist', QVariant.Double))
        out_fields.append(QgsField('nearest_gt_name', QVariant.String))
        out_fields.append(QgsField('nearest_gt_count', QVariant.Int))

        # Get the sinks for output
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT,
                context, out_fields, source.wkbType(), source.sourceCrs())

        (linesink, line_dest_id) = self.parameterAsSink(parameters, self.LINEOUTPUT,
                context, out_fields, QgsWkbTypes.LineString, source.sourceCrs())

        if source.sourceCrs().isGeographic():
            feedback.pushWarning('WARNING: The input is in a geographic CRS. Consider using a projected CRS.')

        # Compute the number of steps to display within the progress bar 
        total = 100.0 / source.featureCount() if source.featureCount() else 0
        current = 0

        # Only compute features where our field is not NULL
        expr = QgsExpression('"{}" IS NOT NULL'.format(compare_field))
        features = source.getFeatures(QgsFeatureRequest(expr))

        # Create a list of (value, feature) tuples.
        # Since values might be stored in a string (e.g. in openstreetmap data)
        # I try to convert the values to float.
        try:
            sorted_features = [(float(f.attribute(compare_field)), f) for f in features]
        except ValueError:
            sorted_features = [(f.attribute(compare_field), f) for f in features]
            feedback.pushInfo('Converting the field to floating point value failed.')
            feedback.pushWarning('WARNING: The fields will be compared as type: '.format(
                type(sorted_features[0][0]).__name__))    
        
        # Sort the Features by the value of the field
        sorted_features.sort(key=lambda x: x[0])

        # Algorithm does not work with the last one (greatest value) 
        last_feature = sorted_features[-1][1]

        # A list of the calculated distances, to get some stats
        dist_list = []
        
        # A list of the ids of nearest features for the count
        nearest_id_list = []

        # Create a spatial index
        # The Features iterator works only once
        features = source.getFeatures(QgsFeatureRequest(expr))
        index = QgsSpatialIndex(features)

        # We need to access features using their id
        features = source.getFeatures(QgsFeatureRequest(expr))
        feat_by_id = {f.id():f for f in features}
        
        # Give feedback about null values etc.
        count_null = source.featureCount() - len(sorted_features)
        feedback.pushInfo('{} of {} features have NULL as value and are ignored.'.format(count_null, source.featureCount()))
        list_names = [f[name_field] for v, f in sorted_features]
        if len(list_names) > len(set(list_names)):
            feedback.pushWarning('WARNING: There are non unique names in the selected field, it might be better to use another field als ID.')
        if NULL in list_names:
            feedback.pushWarning('WARNING: There are NULL values in the selected field, it might be better to use another field als ID.')
        
            

        # The main loop      

        for value, f in sorted_features:
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break
            # Attributes for the greatest feature
            if f == last_feature:
                nearest_name = f[name_field]
                
                if dist_for_max == 1:
                    distance = 1000000.0
                elif dist_for_max == 2:
                    distance = max(dist_list) + 1
                else:
                    distance = NULL

            else:
                # Get the id of the nearest neighbor
                # Note: The returned list always includes f itself, 
                # we need the second "neighbor".
                nearest_id = index.nearestNeighbor(f.geometry().asPoint(), 2)[1]

                nearest_id_list.append(nearest_id)
                nearest_name = feat_by_id[nearest_id][name_field]
                nearest_geom = feat_by_id[nearest_id].geometry().asPoint()
                distance = f.geometry().asPoint().distance(nearest_geom)
                dist_list.append(distance)
                               

                # Now remove f from the index.
                # Since our features are sorted by value, this means that there are 
                # always only those features in the index with a larger value.
                index.deleteFeature(f)

            # In order to add our new fiels, we need to create a new point feature
            newfeat = QgsFeature()
            newfeat.setFields(out_fields)
            newfeat.setGeometry(f.geometry())
  
            new_attributes = f.attributes()
            new_attributes.append(distance) # Field 'nearest_gt_dist'
            new_attributes.append(nearest_name) # Field 'nearest_gt_name'
            new_attributes.append(nearest_id_list.count(f.id())) # Field 'nearest_gt_count'
            
            newfeat.setAttributes(new_attributes)          

            # Add the feature in the sink
            sink.addFeature(newfeat, QgsFeatureSink.FastInsert)
            
            # Create connecting lines in the line output layer

            linegeom = QgsGeometry.fromPolylineXY([f.geometry().asPoint(), nearest_geom])                
            linefeat = QgsFeature()
            linefeat.setFields(out_fields)
            linefeat.setGeometry(linegeom)
            linefeat.setAttributes(new_attributes)             
            linesink.addFeature(linefeat, QgsFeatureSink.FastInsert)

            # Update the progress bar
            feedback.setProgress(int(current * total))
            current = current + 1

        feedback.pushInfo('Processing finished.')

        # Optionally add NULL features to output
        if keep:
            feedback.pushInfo('Add features with null value.')
            expr = QgsExpression('"{}" IS NULL'.format(compare_field))
            features = source.getFeatures(QgsFeatureRequest(expr))

            # The loop is similar to the main loop
            for f in features:
                if feedback.isCanceled():
                    break
              
                newfeat = QgsFeature()
                newfeat.setFields(out_fields)
                newfeat.setGeometry(f.geometry())
  
                new_attributes = f.attributes()
                new_attributes.append(NULL) # Field 'nearest_gt_dist'
                new_attributes.append(NULL) # Field 'nearest_gt_name'
            
                newfeat.setAttributes(new_attributes)          
            
                sink.addFeature(newfeat, QgsFeatureSink.FastInsert)

                feedback.setProgress(int(current * total))
                current = current + 1

        # Calculate some statistics
        min_dist = min(dist_list)
        max_dist = max(dist_list)
        mean_dist = mean(dist_list)
        quantiles_dist = quantiles(dist_list)

        feedback.pushInfo('Distance Statistics:')
        feedback.pushInfo('MIN:    {}'.format(min_dist))        
        feedback.pushInfo('MAX:    {}'.format(max_dist))         
        feedback.pushInfo('MEAN:   {}'.format(mean_dist))       
        feedback.pushInfo('Q1:     {}'.format(quantiles_dist[0])) 
        feedback.pushInfo('MEDIAN: {}'.format(quantiles_dist[1])) 
        feedback.pushInfo('Q3:     {}'.format(quantiles_dist[2])) 

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        if feedback.isCanceled():
            return {}

        return {self.OUTPUT: dest_id, 
                self.LINEOUTPUT: line_dest_id,
                'ID_MAX_VALUE': last_feature.id(),
                'NUMBER_PROCESSED_FEATURES':len(sorted_features),
                'NUMBER_IGNORED_FEATURES':count_null,
                'MIN_DIST':min_dist,
                'MAX_DIST':max_dist,
                'MEAN_DIST':mean_dist,
                'Q1_DIST':quantiles_dist[0],
                'Q2_DIST':quantiles_dist[1],                
                'Q3_DIST':quantiles_dist[2],
                }


    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'nearestgreater'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('nearest with greater value')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())


    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return NearestGreaterAlgorithm()

