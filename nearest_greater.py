# -*- coding: utf-8 -*-

"""
/***************************************************************************
 NearestGreater
                                 A QGIS plugin
 Get name (or ID) of and distance to the nearest feature with greater value 
 in a certain field.
 
 Template by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
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

import os
import sys
import inspect

from qgis.core import QgsProcessingAlgorithm, QgsApplication
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from .nearest_greater_provider import NearestGreaterProvider

cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]

if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)


class NearestGreaterPlugin(object):

    def __init__(self):
        self.provider = None

        # initialize locale
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'nearest_greater_{}.qm'.format(locale))
        
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)


    def initProcessing(self):
        """Init Processing provider for QGIS >= 3.8."""
        self.provider = NearestGreaterProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
