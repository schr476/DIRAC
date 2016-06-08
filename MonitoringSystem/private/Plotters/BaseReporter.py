import time, copy, types
from DIRAC import S_OK, S_ERROR, gLogger
#from DIRAC.AccountingSystem.private.DBUtils import DBUtils
from DIRAC.Core.Utilities.Plotting import gMonitoringDataCache
from DIRAC.Core.Utilities import Time
from DIRAC.MonitoringSystem.private.DBUtils import DBUtils
from DIRAC.Core.Utilities.Plotting.Plots import generateNoDataPlot, generateTimedStackedBarPlot, generateQualityPlot, generateCumulativePlot, generatePiePlot, generateStackedLinePlot

class BaseReporter( DBUtils ):

  _PARAM_CHECK_FOR_NONE = 'checkNone'
  _PARAM_CALCULATE_PROPORTIONAL_GAUGES = 'calculateProportionalGauges'
  _PARAM_CONVERT_TO_GRANULARITY = 'convertToGranularity'
  _VALID_PARAM_CONVERT_TO_GRANULARITY = ( 'sum', 'average' )
  _PARAM_CONSOLIDATION_FUNCTION = "consolidationFunction"

  _EA_THUMBNAIL = 'thumbnail'
  _EA_WIDTH = 'width'
  _EA_HEIGHT = 'height'
  _EA_THB_WIDTH = 'thbWidth'
  _EA_THB_HEIGHT = 'thbHeight'
  _EA_PADDING = 'figurePadding'
  _EA_TITLE = 'plotTitle'

  _RATE_UNITS = { 'time' : ( ( 'seconds / s', 1, 24 ), ( 'hours / s', 3600, 24 ), ( 'days / s', 86400, 15 ), ( 'weeks / s', 86400 * 7, 10 ), ( 'months / s', 86400 * 30, 12 ), ( 'years / s', 86400 * 365, 1 ) ),
                  'cpupower' : ( ( 'HS06', 1, 750 ), ( 'kHS06', 1000, 750 ), ( 'MHS06', 10 ** 6, 1 ) ),
                  'bytes' : ( ( 'MB / s', 10 ** 6, 1000 ), ( 'GB / s', 10 ** 9, 1000 ), ( 'TB / s', 10 ** 12, 1000 ), ( 'PB / s', 10 ** 15, 1 ) ),
                  'jobs' : ( ( 'jobs / hour', 1 / 3600.0, 1000 ), ( 'kjobs / hour', ( 10 ** 3 ) / 3600.0, 1000 ), ( 'Mjobs / hour', ( 10 ** 6 ) / 3600.0, 1 ) ),
                  'files' : ( ( 'files / hour', 1 / 3600.0, 1000 ), ( 'kfiles / hour', ( 10 ** 3 ) / 3600.0, 1000 ), ( 'Mfiles / hour', ( 10 ** 6 ) / 3600.0, 1 ) )
                }

  _UNITS = { 'time' : ( ( 'seconds', 1, 24 ), ( 'hours', 3600, 24 ), ( 'days', 86400, 15 ), ( 'weeks', 86400 * 7, 10 ), ( 'months', 86400 * 30, 12 ), ( 'years', 86400 * 365, 1 ) ),
             'cpupower' : ( ( 'HS06 hours', 3600, 24 ), ( 'HS06 days', 86400, 750 ), ( 'kHS06 days', 86400 * 1000, 750 ), ( 'MHS06 days', 86400 * 10**6, 1 ) ),
             'bytes' : ( ( 'MB', 10 ** 6, 1000 ), ( 'GB', 10 ** 9, 1000 ), ( 'TB', 10 ** 12, 1000 ), ( 'PB', 10 ** 15, 1 ) ),
             'jobs' : ( ( 'jobs', 1, 1000 ), ( 'kjobs', 10 ** 3, 1000 ), ( 'Mjobs', 10 ** 6, 1 ) ),
             'files' : ( ( 'files', 1, 1000 ), ( 'kfiles', 10 ** 3, 1000 ), ( 'Mfiles', 10 ** 6, 1 ) )
           }

  # To be defined in the derived classes
  _typeKeyFields = []
  _typeName = ''

  def __init__( self, db, setup, extraArgs = None ):
    DBUtils.__init__( self, db, setup )
    if type( extraArgs ) == types.DictType:
      self._extraArgs = extraArgs
    else:
      self._extraArgs = {}
    reportsRevMap = {}
    for attr in dir( self ):
      if attr.find( "_report" ) == 0:
        if attr.find( 'Name', len( attr ) - 4 ) == len( attr ) - 4:
          reportId = attr[ 7 :-4 ]
          reportName = getattr( self, attr )
          reportsRevMap[ reportId ] = reportName
        else:
          reportId = attr[ 7: ]
          if reportId not in reportsRevMap:
            reportsRevMap[ reportId ] = reportId
    self.__reportNameMapping = {}
    for rId in reportsRevMap:
      self.__reportNameMapping[ reportsRevMap[ rId ] ] = rId

  def _averageConsolidation( self, total, count ):
    if count == 0:
      return 0
    else:
      return float( total ) / float( count )

  def _efficiencyConsolidation( self, total, count ):
    if count == 0:
      return 0
    else:
      return ( float( total ) / float( count ) ) * 100.0

  def generate( self, reportRequest ):
    
    reportHash = reportRequest[ 'hash' ]
    reportName = reportRequest[ 'reportName' ]
    if reportName in self.__reportNameMapping:
      reportRequest[ 'reportName' ] = self.__reportNameMapping[ reportName ]
    gLogger.info( "Retrieving data for %s:%s" % ( reportRequest[ 'typeName' ], reportRequest[ 'reportName' ] ) )
    sT = time.time()
    retVal = self.__retrieveReportData( reportRequest, reportHash )
    reportGenerationTime = time.time() - sT
    if not retVal[ 'OK' ]:
      return retVal
    if not reportRequest[ 'generatePlot' ]:
      return retVal
    reportData = retVal[ 'Value' ]
    gLogger.info( "Plotting data for %s:%s" % ( reportRequest[ 'typeName' ], reportRequest[ 'reportName' ] ) )
    sT = time.time()
    retVal = self.__generatePlotForReport( reportRequest, reportHash, reportData )
    plotGenerationTime = time.time() - sT
    gLogger.info( "Time for %s:%s - Report %.2f Plot %.2f (%.2f%% r/p)" % ( reportRequest[ 'typeName' ],
                                                                            reportRequest[ 'reportName' ],
                                                                            reportGenerationTime,
                                                                            plotGenerationTime,
                                                                            ( ( reportGenerationTime * 100 / plotGenerationTime )  if plotGenerationTime else 0. ) ) )
    if not retVal[ 'OK' ]:
      return retVal
    plotDict = retVal[ 'Value' ]
    if 'retrieveReportData' in reportRequest[ 'extraArgs' ] and reportRequest[ 'extraArgs' ][ 'retrieveReportData' ]:
      plotDict[ 'reportData' ] = reportData
    return S_OK( plotDict )

  def plotsList( self ):
    return sorted( [ k for k in self.__reportNameMapping ] )

  def __retrieveReportData( self, reportRequest, reportHash ):
    
    funcName = "_report%s" % reportRequest[ 'reportName' ]
    try:
      funcObj = getattr( self, funcName )
    except:
      return S_ERROR( "Report %s is not defined" % reportRequest[ 'reportName' ] )
    return gMonitoringDataCache.getReportData( reportRequest, reportHash, funcObj )

  def __generatePlotForReport( self, reportRequest, reportHash, reportData ):
    funcName = "_plot%s" % reportRequest[ 'reportName' ]
    try:
      funcObj = getattr( self, funcName )
    except:
      return S_ERROR( "Plot function for report %s is not defined" % reportRequest[ 'reportName' ] )
    return gMonitoringDataCache.getReportPlot( reportRequest, reportHash, reportData, funcObj )

###
# Helper functions for reporters
###

  def _getTimedData( self, startTime, endTime, selectFields, preCondDict, metadataDict = None):
    condDict = {}
    #Check params
    
    grouping = preCondDict['grouping'][0]
    #Make safe selections
    for keyword in self._typeKeyFields:
      if keyword in preCondDict:
        condDict[ keyword ] = preCondDict[ keyword ]
        
    retVal = self._determineBucketSize(startTime, endTime)
    if not retVal['OK']:
      return retVal
    interval, granularity = retVal['Value']
       
    retVal = self._retrieveBucketedData( self._typeName,
                                          startTime,
                                          endTime,
                                          interval,
                                          selectFields,
                                          condDict,
                                          grouping,
                                          metadataDict)
    if not retVal[ 'OK' ]:
      return retVal
    dataDict = retVal[ 'Value' ] 
    
    return S_OK( ( dataDict, granularity ) )

  def _executeConsolidation( self, functor, dataDict ):
    for timeKey in dataDict:
      dataDict[ timeKey ] = [ functor( *dataDict[ timeKey ] ) ]
    return dataDict

  def _getSummaryData( self, startTime, endTime, selectFields, preCondDict, metadataDict = None):
    
    grouping = preCondDict['grouping'][0]
    condDict = {}
    #Make safe selections
    for keyword in self._typeKeyFields:
      if keyword in preCondDict:
        condDict[ keyword ] = preCondDict[ keyword ]
    
    retVal = self._determineBucketSize(startTime, endTime)
    if not retVal['OK']:
      return retVal
    interval, _ = retVal['Value']
    
    #Query!
    retVal = self._retrieveBucketedData( self._typeName,
                                          startTime,
                                          endTime,
                                          interval,
                                          selectFields,
                                          condDict,
                                          grouping,
                                          metadataDict)
    if not retVal[ 'OK' ]:
      return retVal
    dataDict = retVal[ 'Value' ]
    return S_OK( dataDict )

  def _getSelectStringForGrouping( self, groupingFields ):
    if len( groupingFields ) == 3:
      return groupingFields[2]
    if len( groupingFields[1] ) == 1:
      #If there's only one field, then we send the sql representation in pos 0
      return groupingFields[0]
    else:
      return "CONCAT( %s )" % ", ".join( [ "%s, '-'" % sqlRep for sqlRep in groupingFields[0] ] )

  def _findSuitableRateUnit( self, dataDict, maxValue, unit ):
    return self._findUnitMagic( dataDict, maxValue, unit, self._RATE_UNITS )

  def _findSuitableUnit( self, dataDict, maxValue, unit ):
    return self._findUnitMagic( dataDict, maxValue, unit, self._UNITS )

  def _findUnitMagic( self, reportDataDict, maxValue, unit, selectedUnits ):
    if unit not in selectedUnits:
      raise AttributeError( "%s is not a known rate unit" % unit )
    baseUnitData = selectedUnits[ unit ][ 0 ]
    if 'staticUnits' in self._extraArgs and self._extraArgs[ 'staticUnits' ]:
      unitData = selectedUnits[ unit ][ 0 ]
    else:
      unitList = selectedUnits[ unit ]
      unitIndex = -1
      for _, unitDivFactor, unitThreshold in unitList:
        unitIndex += 1
        if maxValue / unitDivFactor < unitThreshold:
          break
      unitData = selectedUnits[ unit ][ unitIndex ]
    #Apply divFactor to all units
    graphDataDict, maxValue = self._divideByFactor( copy.deepcopy( reportDataDict ), unitData[1] )
    if unitData == baseUnitData:
      reportDataDict = graphDataDict
    else:
      reportDataDict, dummyMaxValue = self._divideByFactor( reportDataDict, baseUnitData[1] )
    return reportDataDict, graphDataDict, maxValue, unitData[0]
##
# Plotting
##

  def __checkPlotMetadata( self, metadata ):
    if self._EA_WIDTH in self._extraArgs and self._extraArgs[ self._EA_WIDTH ]:
      try:
        metadata[ self._EA_WIDTH ] = min( 1600, max( 200, int( self._extraArgs[ self._EA_WIDTH ] ) ) )
      except:
        pass
    if self._EA_HEIGHT in self._extraArgs and self._extraArgs[ self._EA_HEIGHT ]:
      try:
        metadata[ self._EA_HEIGHT ] = min( 1600, max( 200, int( self._extraArgs[ self._EA_HEIGHT ] ) ) )
      except:
        pass
    if self._EA_TITLE in self._extraArgs and self._extraArgs[ self._EA_TITLE ]:
      metadata[ 'title' ] = self._extraArgs[ self._EA_TITLE ]

  def __checkThumbnailMetadata( self, metadata ):
    if self._EA_THUMBNAIL in self._extraArgs and self._extraArgs[ self._EA_THUMBNAIL ]:
      thbMD = dict( metadata )
      thbMD[ 'legend' ] = False
      if self._EA_THB_HEIGHT in self._extraArgs:
        thbMD[ self._EA_HEIGHT ] = self._extraArgs[ self._EA_THB_HEIGHT ]
      else:
        thbMD[ self._EA_HEIGHT ] = 125
      if self._EA_THB_WIDTH in self._extraArgs:
        thbMD[ self._EA_WIDTH ] = self._extraArgs[ self._EA_THB_WIDTH ]
      else:
        thbMD[ self._EA_WIDTH ] = 200
      thbMD[ self._EA_PADDING ] = 20
      for key in ( 'title', 'ylabel', 'xlabel' ):
        if key in thbMD:
          del( thbMD[ key ] )
      return thbMD
    return False

  def __plotData( self, filename, dataDict, metadata, funcToPlot ):
    self.__checkPlotMetadata( metadata )
    if not dataDict:
      funcToPlot = generateNoDataPlot
    plotFileName = "%s.png" % filename
    finalResult = funcToPlot( plotFileName, dataDict, metadata )
    if not finalResult[ 'OK' ]:
      return finalResult
    thbMD = self.__checkThumbnailMetadata( metadata )
    if not thbMD:
      return S_OK( { 'plot' : True, 'thumbnail' : False } )
    thbFilename = "%s.thb.png" % filename
    retVal = funcToPlot( thbFilename, dataDict, thbMD )
    if not retVal[ 'OK' ]:
      return retVal
    return S_OK( { 'plot' : True, 'thumbnail' : True } )

  def _generateTimedStackedBarPlot( self, filename, dataDict, metadata ):
    return self.__plotData( filename, dataDict, metadata, generateTimedStackedBarPlot )

  def _generateQualityPlot( self, filename, dataDict, metadata ):
    return self.__plotData( filename, dataDict, metadata, generateQualityPlot )

  def _generateCumulativePlot( self, filename, dataDict, metadata ):
    return self.__plotData( filename, dataDict, metadata, generateCumulativePlot )

  def _generatePiePlot( self, filename, dataDict, metadata ):
    return self.__plotData( filename, dataDict, metadata, generatePiePlot )

  def _generateStackedLinePlot( self, filename, dataDict, metadata ):
    return self.__plotData( filename, dataDict, metadata, generateStackedLinePlot )
  
  def _fillWithZero( self, granularity, startEpoch, endEpoch, dataDict ):
    """
    Fill with zeros missing buckets
      - dataDict = { 'key' : { time1 : value,  time2 : value... }, 'key2'.. }
    """
    startBucketEpoch = startEpoch - startEpoch % granularity
    for key in dataDict:
      currentDict = dataDict[ key ]
      for timeEpoch in range( int( startBucketEpoch ), int( endEpoch ), granularity ):
        if timeEpoch not in currentDict:
          currentDict[ timeEpoch ] = 0
    return dataDict
