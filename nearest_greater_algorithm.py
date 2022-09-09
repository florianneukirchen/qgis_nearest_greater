# -*- coding: utf-8 -*-

"""
/***************************************************************************
 NearestGreater
                                 A QGIS plugin
 Get id of and distance to the nearest feature with greater value in a certain field.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
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
                       QgsProcessingParameterNumber)

class NearestGreaterAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = 'OUTPUT'
    INPUT = 'INPUT'
    COMPARE_FIELD = 'COMPARE_FIELD'
    DIST_FOR_MAX = 'DIST_FOR_MAX'


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
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )


        # Select the field containing values to be compared
        self.addParameter(
            QgsProcessingParameterField(
                self.COMPARE_FIELD,
                'Field with values to compare',
                '',
                self.INPUT))


        # Choose a number for the distance used for the feature
        # with the greatest value. Can be NULL or any number.
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DIST_FOR_MAX, 
                'Distance value for the greatest feature',
                QgsProcessingParameterNumber.Double,
                1000000000))
                
                
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


        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output Nearest Greater')
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

        dist_for_max = self.parameterAsDouble(
            parameters,
            self.DIST_FOR_MAX,
            context)

            
        # Define fields
        out_fields = source.fields()
        out_fields.append(QgsField('nearest_gt_dist', QVariant.Double))
        out_fields.append(QgsField('nearest_gt_id', QVariant.Int))

        # Get the sink for output
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT,
                context, out_fields, source.wkbType(), source.sourceCrs())


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
            feedback.pushWarning('WARNING: The fields will be compared as type: {}'.format(
                type(sorted_features[0][0]).__name__))    
        
        # Sort the Features by the value of the field
        sorted_features.sort(key=lambda x: x[0])

        # Algorithm does not work with the last one (greatest value) 
        last_feature = sorted_features[-1][1]

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
      

        for value, f in sorted_features:
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break
            # Set some values for the greatest feature
            if f == last_feature:
                nearest = f.id()
                distance = dist_for_max
            else:
                # Get the id of the nearest neighbor
                # Note: The returned list always includes f itself, 
                # we need the second "neighbor".
                nearest_id = index.nearestNeighbor(f.geometry().asPoint(), 2)[1]
                nearest_geom = feat_by_id[nearest_id].geometry().asPoint()
                distance = f.geometry().asPoint().distance(nearest_geom)
                # Now remove f from the index.
                # Since our feaures are sorted by value, this means that there are 
                # always only those features in the index with a larger value.
                index.deleteFeature(f)


            newfeat = QgsFeature()
            newfeat.setFields(out_fields)
            newfeat.setGeometry(f.geometry())
  
            new_attributes = f.attributes()
            new_attributes.append(distance) # Field 'nearest_gt_dist'
            new_attributes.append(nearest_id) # Field 'nearest_gt_id'
            
            newfeat.setAttributes(new_attributes)          

            # Add the feature in the sink
            sink.addFeature(newfeat, QgsFeatureSink.FastInsert)

            # Update the progress bar
            feedback.setProgress(int(current * total))
            current = current + 1

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        if feedback.isCanceled():
            return {}

        return {self.OUTPUT: dest_id, 
                'ID_MAX_VALUE': last_feature.id(),
                'NUMBER_PROCESSED_FEATURES':len(sorted_features),
                'NUMBER_IGNORED_FEATURES':count_null
                }


    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Nearest with greater value'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

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
