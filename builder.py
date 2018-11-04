import os
import subprocess
import shutil 

from errors import *
import config
from settings import Settings
from logger import Logger
from utility import Utility
from helper import convertToPlatformPath
from system import System

class Builder:
  @classmethod
  def init(cls):
    """
      Initiates logger object.
    """
    cls.logger = Logger.getLogger('Build')

  @classmethod
  def run(cls, targetName, targets, platform, cpu, configuration, combineLibs = False, builderWorkingPath = None):
    """
      Start target building process.
      :param targetName: Name of the main target (ortc or webrtc)
      :param targets: List of the targets to build
      :param platform: Platform name
      :param cpu: Target CPU
      :param configuration: Configuration to build for
      :param combineLibs: Should all libs be merged into one library
      :param builderWorkingPath: Path where generated projects for specified target.
      :return: NO_ERROR if build was successfull. Otherwise returns error code
    """
    cls.logger.info('Running build for target: ' + targetName + '; platform: ' + platform + '; cpu: ' + cpu + '; configuration: ' + configuration)

    #If path with generated projects is not specified generate path from input arguments
    if builderWorkingPath == None:
      builderWorkingPath = os.path.join('out', targetName + '_' + platform + '_' + cpu + '_' + configuration)

    workingDir = os.path.join(Settings.preparationWorkingPath,builderWorkingPath)

    #If folder for specified target and platform doesn't exist, stop further execution
    if not os.path.exists(workingDir):
      cls.logger.error('Output folder at ' + workingDir + ' doesn\'t exist. It looks like prepare is not executed. Please run prepare action.')
      return ERROR_BUILD_OUTPUT_FOLDER_DEOESNT_EXIST
    
    #Change current working directory to one with generated projects
    Utility.pushd(workingDir)

    #Start building and merging libraries
    if not cls.buildTargets(targets, cpu):
      return ERROR_BUILD_FAILED
    
    #Merge libraries if it is required
    if combineLibs:
      cls.mergeLibs(cpu)

    destinationPath = convertToPlatformPath(config.BUILT_LIBS_DESTINATION_PATH.replace('[TARGET]',targetName).replace('[PLATFORM]',platform).replace('[CPU]',cpu).replace('[CONFIGURATION]',configuration))
    destinationPathLib = os.path.join(Settings.preparationWorkingPath, destinationPath)

    cls.copyLibsToOutput(targetName, platform, cpu, configuration, destinationPathLib)

    if Settings.libsBackupPath != '':
      backupPath = os.path.join(Settings.userWorkingPath,Settings.libsBackupPath)
      if os.path.exists(backupPath):
        shutil.rmtree(backupPath) 
      shutil.copytree(destinationPathLib,backupPath)
    #Switch to previously working directory
    Utility.popd()

    return NO_ERROR

  @classmethod
  def buildTargets(cls, targets, targetCPU):
    for target in targets:
      result = subprocess.call([
          Settings.localNinjaPath + '.exe',
          target,
        ])

      if result != 0:
          cls.logger.error('Building ' + target + ' target libraries has failed!')
          return False
      
      cls.logger.info('Successfully finished building libs for target ' + target)

    return True

  @classmethod
  def mergeLibs(cls, targetCPU):
    cls.libexePath = os.path.join(Settings.msvcToolsBinPath, targetCPU, 'lib.exe')
    
    #
    listOfObjesToCombine = Utility.getFilesWithExtensionsInFolder(config.COMBINE_LIB_FOLDERS, ('.obj','.o'))

    tempCombinePath = 'combine'
    Utility.createFolders([tempCombinePath])

    counter = 0
    libsToMerge = ''

    for objs in listOfObjesToCombine:
      output = 'webrtc' + str(counter) + '.lib'
      ret = cls.combineLibs(targetCPU, objs, tempCombinePath, output)
      if ret == NO_ERROR:
        libsToMerge += (os.path.join(tempCombinePath, output)) + ' '
        counter += 1
      else:
        System.stopExecution(ret)

    if len(libsToMerge) > 0:
      ret = cls.combineLibs(targetCPU, libsToMerge, '.', 'webrtc.lib')
      if ret != NO_ERROR:
        System.stopExecution(ret)
    else:
      cls.logger.warning('There is no libs to merge for target CPU ' + targetCPU)

    shutil.rmtree(tempCombinePath) 

  @classmethod
  def combineLibs(cls, targetCPU, inputFiles, outputFolder, outputFile):
    ret = NO_ERROR
    try:
      #Set the PATH and environment variables for command-line builds (e.g. vcvarsall.bat x64_x86)
      cmdVcVarsAll = '\"' +  Settings.vcvarsallPath + '\" ' + config.WINDOWS_COMPILER_OPTIONS[System.hostCPU][targetCPU]

      output = os.path.join(outputFolder, outputFile)

      #Call lib.exe to mergeobj files to webrtc[counter].lib files, which will be later merged to webrtc.lib
      cmdLibExe = '\"' +  cls.libexePath + '\" /IGNORE:' + ','.join(str(i) for i in config.WINDOWS_IGNORE_WARNINGS) +  ' /OUT:' + output + ' ' + inputFiles

      #Make cmdLibExe command dependent on cmdVcVarsAll
      commands = cmdVcVarsAll + ' && ' + cmdLibExe

      #cls.logger.debug('Command line to execute: ' + commands)
      FNULL = open(os.devnull, 'w')
      result = subprocess.call(commands,stdout=FNULL, stderr=subprocess.STDOUT)

      if result != 0:
        cls.logger.error(error_codes[ERROR_BUILD_MERGE_LIBS_FAILED])
        ret = ERROR_BUILD_MERGE_LIBS_FAILED

    except Exception as error:
      cls.logger.error(str(error))
      ret = ERROR_BUILD_MERGE_LIBS_FAILED

    return ret

  @classmethod
  def copyLibsToOutput(cls, target, platform, cpu, configuration, destinationPathLib):
    destinationPathPdb = os.path.join(destinationPathLib,'pdbs')

    if not os.path.exists(destinationPathLib):
      os.makedirs(destinationPathLib)

    if not os.path.exists(destinationPathPdb):
      os.makedirs(destinationPathPdb)

    listOfLibsToCopy = Utility.getFilesWithExtensionsInFolder(['.'],('.lib','.dll'),0)
    
    for lib in listOfLibsToCopy:
      shutil.copyfile(lib, os.path.join(destinationPathLib,os.path.basename(lib)))

    listOfPdbsToCopy = Utility.getFilesWithExtensionsInFolder(['.'],('.pdb'),0)
    
    for pdb in listOfPdbsToCopy:
      shutil.copyfile(pdb, os.path.join(destinationPathPdb,os.path.basename(pdb)))

  @classmethod
  def makeBackup(cls):
    pass

  @classmethod
  def getTargetGnPath(cls, target):
    targetsToBuild, combineLibs = config.TARGETS_TO_BUILD.get(target,(target,0))
    return targetsToBuild, combineLibs