from datetime import timedelta

from logger import Logger, ColoredFormatter
from errors import NO_ERROR
from helper import iterateDict

class Summary:

  action_results = dict()

  @classmethod
  def addSummary(cls, action, target, platform, cpu, configuration, result, time = 0):
    key = target + '___' + platform + '___' + cpu + '___' + configuration

    resultActionDict =  cls.action_results.get(action,dict())
    resultDict = resultActionDict.get(key,dict())
    resultDict['result'] = result
    resultDict['time'] = time 
    resultActionDict[key] = resultDict

    cls.action_results[action] = resultActionDict


  @classmethod
  def printSummary(cls, executionTime = 0):
    Logger.printColorMessage('\n========================================= SUMMARY ========================================= \n', ColoredFormatter.YELLOW)
    for key, value in iterateDict(cls.action_results):
      if key != 'cleanup':
        Logger.printColorMessage('ACTION: ' + key + '', ColoredFormatter.WHITE)
        for resultKey, resultValue in iterateDict(value):
          if resultValue['result'] == NO_ERROR:
            Logger.printColorMessage('     SUCCESSFUL: ' + resultKey.replace('___', '   ') + '      execution time: ' + str(timedelta(seconds=resultValue['time'])) + '', ColoredFormatter.GREEN)
          else:
            Logger.printColorMessage('         FAILED: ' + resultKey.replace('___', '   ') + '      execution time: ' + str(timedelta(seconds=resultValue['time'])) +  '', ColoredFormatter.RED)
      Logger.printColorMessage('\n------------------------------------------------------------------------------------------- ', ColoredFormatter.YELLOW)
    Logger.printColorMessage('Total execution time: ' + str(timedelta(seconds=executionTime)), ColoredFormatter.YELLOW)


  @classmethod
  def isPreparationFailed(cls, target, platform, cpu, configuration):
    ret = False
    prepareActionDict =  cls.action_results.get('prepare',None)
    if prepareActionDict != None:
      key = target + '___' + platform + '___' + cpu + '___' + configuration
      resultDict = prepareActionDict.get(key,None)
      if resultDict != None:
        if resultDict['result'] != NO_ERROR:
          ret = True

    return ret
