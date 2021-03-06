#!/usr/bin/env python
""" update local cfg
"""

from DIRAC.Core.Base import Script

Script.setUsageMessage( '\n'.join( [ __doc__.split( '\n' )[1],
                                     'Usage:',
                                     '  %s [option|cfgFile] ' % Script.scriptName] ) )

Script.parseCommandLine()
args = Script.getPositionalArgs()

from DIRAC.ConfigurationSystem.Client.CSAPI import CSAPI
csAPI = CSAPI()


# Setup the DFC
#
# DataManagement
# {
#   Production
#   {
#     Services
#     {
#       FileCatalog
#       {
#         DirectoryManager = DirectoryClosure
#         FileManager = FileManagerPS
#         SecurityManager = FullSecurityManager
#       }
#     }
#     Databases
#     {
#       FileCatalogDB
#       {
#         DBName = FileCatalogDB
#       }
#     }
#   }
# }

for sct in ['Systems/DataManagement',
            'Systems/DataManagement/Production',
            'Systems/DataManagement/Production/Databases',
            'Systems/DataManagement/Production/Databases/FileCatalogDB' ]:
  res = csAPI.createSection( sct )
  if not res['OK']:
    print res['Message']
    exit( 1 )

csAPI.setOption( 'Systems/DataManagement/Production/Databases/FileCatalogDB/DBName', 'FileCatalogDB' )
csAPI.setOption( 'Systems/DataManagement/Production/Databases/FileCatalogDB/Host', 'db-50098.cern.ch' )
csAPI.setOption( 'Systems/DataManagement/Production/Databases/FileCatalogDB/Port', '5501' )

# Setup other DBs (this is for LHCb - innocuous!)
#
# Bookkeeping
# {
#   Production
#   {
#     Databases
#     {
#       BookkeepingDB
#       {
#         LHCbDIRACBookkeepingTNS =
#         LHCbDIRACBookkeepingUser =
#         LHCbDIRACBookkeepingPassword =
#         LHCbDIRACBookkeepingServer =
#       }
#     }
#   }
# }

for sct in ['Systems/Bookkeeping',
            'Systems/Bookkeeping/Production',
            'Systems/Bookkeeping/Production/Databases',
            'Systems/Bookkeeping/Production/Databases/BookkeepingDB' ]:
  res = csAPI.createSection( sct )
  if not res['OK']:
    print res['Message']
    exit( 1 )

csAPI.setOption( 'Systems/Bookkeeping/Production/Databases/BookkeepingDB/LHCbDIRACBookkeepingTNS', 'FILL_ME' )
csAPI.setOption( 'Systems/Bookkeeping/Production/Databases/BookkeepingDB/LHCbDIRACBookkeepingUser', 'FILL_ME' )
csAPI.setOption( 'Systems/Bookkeeping/Production/Databases/BookkeepingDB/LHCbDIRACBookkeepingPassword', 'FILL_ME' )
csAPI.setOption( 'Systems/Bookkeeping/Production/Databases/BookkeepingDB/LHCbDIRACBookkeepingServer', 'FILL_ME' )

# Commit

csAPI.commit()
