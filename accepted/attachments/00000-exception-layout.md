# Uyuni XMLRPC Exception Layout

## System Exceptions (1000-1019, 1060-1099)

`1000` UndefinedCustomFieldsException\
`1003` SystemsNotDeletedException\
`1004` SystemIdInstantiationException

`1060` ProfileNameTooShortException\
`1061` ProfileNameTooLongException\
`1062` InvalidAdvisoryTypeException\
`1063` ServerNotInGroupException\
`1064` InvalidAccessValueException\
`1065` ProfileNoBaseChannelException\
`1066` NotPermittedByOrgException\
`1067` FileListAlreadyExistsException\
`1068` FileListNotFoundException\
`1069` NoSuchSnapshotException\
`1070` InvalidAdvisoryReleaseException\
`1071` NoCrashesFoundException\
`1072` NoSuchCrashException\
`1072` NoSuchNetworkInterfaceException\
`1073` CrashFileDownloadException\
`1090` ActivationKeyAlreadyExistsException

## Proxy Exceptions (1040-1049)

`1043` ProxyAlreadyRegisteredException\
`1044` ProxyNotActivatedException\
`1045` ProxySystemIsSatelliteException\
`1046` InvalidProxyVersionException\
`1046` ProxyChannelNotFoundException\
`1047` ProxyMissingEntitlementException

## Channel Exceptions (1200-1229)

`1200` InvalidChannelNameException\
`1201` InvalidChannelLabelException\
`1202` InvalidParentChannelException\
`1203` MultipleBaseChannelException\
`1204` InvalidSystemException\
`1205` InvalidChannelArchException\
`1206` DuplicateChannelLabelException\
`1206` InvalidChannelAccessException\
`1207` InvalidGPGUrlException\
`1208` InvalidGPGKeyException\
`1209` InvalidChannelListException\
`1210` InvalidChecksumLabelException\
`1211` SnapshotTagAlreadyExistsException\
`1212` NoSuchSnapshotTagException\
`1212` SnapshotLookupException\
`1213` InvalidParameterException\
`1213` NoSuchContentSourceException\
`1215` DuplicateChannelNameException

## Satellite Exceptions (1230-1239)

`1230` ChannelSubscriptionException\
`1231` PamAuthNotConfiguredException\
`1233` InvalidOperationException

## Config Channel (1020-1029)

`1023` ConfigFileErrorException

## User Exceptions (2000-2099)

`2000` DeleteUserException\
`2010` UserNeverLoggedInException\
`2069` NotSupportedException

## Server Group Exceptions (2200-2299)

`2200` InvalidServerGroupException\
`2201` LookupServerGroupException\
`2202` ServerGroupAccessChangeException\
`2280` UnrecognizedCountryException

## Package Exceptions (2300-2399)

`2300` InvalidPackageException\
`2301` InvalidPackageArchException\
`2302` PackageDownloadException\
`2349` InvalidPackageProviderException\
`2350` InvalidPackageKeyTypeException

## Entitlement Exceptions (2400-2499)

`2400` MissingEntitlementException\
`2401` MissingCapabilityException

## Preferences Exceptions (2500-2599)

`2500` InvalidLocaleCodeException\
`2500` InvalidTimeZoneException

## Errata Exceptions (2600-2699)

`2600` InvalidErrataException\
`2601` DuplicateErrataException\
`2603` NoChannelsSelectedException\
`2609` MissingErrataAttributeException

## Action Exceptions (2700-2749)

`2700` NoSuchActionException\
`2701` InvalidActionTypeException\
`2710` NoSuchActionChainException

## Kickstart Exceptions (2750-2799)

`2751` InvalidVirtualizationTypeException\
`2752` NoSuchKickstartTreeException\
`2753` InvalidKickstartLabelException\
`2754` KickstartKeyAlreadyExistsException\
`2755` KickstartKeyDeleteException\
`2756` InvalidProfileLabelException\
`2756` NoSuchKickstartInstallTypeException\
`2757` InvalidKickstartTreeException\
`2760` InvalidScriptTypeException\
`2761` InvalidKickstartScriptException\
`2762` InvalidScriptNameException\
`2764` NoSuchKickstartException\
`2785` IpRangeConflictException\
`2787` InvalidIpAddressException

## Misc Exceptions (2800-2849)

`2800` ValidationException\
`2801` InvalidArgsException\
`2802` TaskomaticApiException

## Org Exceptions (2850-2899)

`2850` NoSuchOrgException\
`2851` SatelliteOrgException\
`2853` MigrationToSameOrgException\
`2854` OrgNotInTrustException\
`2856` NoSuchExternalGroupToRoleMapException\
`2880` MonitoringException

## SearchServer Exceptions (2900-2949)

`2901` SearchServerCommException\
`2902` SearchServerQueryException\
`2903` SearchServerIndexException

## Authentication Exceptions (2950-2999)

`2950` UserLoginException

## ISS Exceptions (3000-3049)

`3000` IssDuplicateMasterException\
`3000` UnknownCVEIdentifierFaultException\
`3001` IssDuplicateSlaveException\
`3028` NoPushClientException

## SUSE Exceptions (10000-19999)

`10000` TokenCreationException\
`10001` NoSuchActivationKeyException\
`10002` AuthenticationException\
`10003` UnsupportedOperationException\
`10004` NoActionInScheduleException\
`10010` NoSuchImageStoreException\
`10011` NoSuchImageProfileException\
`10012` NoSuchImageException\
`10013` PowerManagementOperationFailedException\
`10100` EntityExistsFaultException\
`10101` EntityNotExistsFaultException\
`10102` ContentManagementFaultException\
`10103` ContentValidationFaultException

## Uncategorized

`-60001` NoSuchClusterException\
`-2005` NoSuchRoleException\
`-1029` NoSuchConfigFilePathException\
`-1028` NoSuchConfigRevisionException\
`-500` UserNotUpdatedException\
`-215` NoSuchDistChannelMapException\
`-214` NoSuchCobblerSystemRecordException\
`-213` NoSuchUserException\
`-212` InvalidEntitlementException\
`-211` InvalidChannelException\
`-210` NoSuchChannelException\
`-209` NoSuchPackageException\
`-208` NoSuchSystemException\
`-23` PermissionCheckFailureException\
`-12` MethodInvalidParamException\
`-1` BootstrapException\
`1` InvalidRepoUrlException\
`1` InvalidRepoUrlInputException\
`1` InvalidUserNameException\
`2` InvalidRepoLabelException\
`2` InvalidRepoTypeException\
`1100` SystemsExistFaultException\
`2107` ModulesNotAllowedException\
`3500` NoSuchGathererModuleException\
`3601` IOFaultException\
`4856` InvalidRoleException\
`6134` InvalidUpdateTypeAndKickstartTreeException\
`6134` InvalidUpdateTypeAndNoBaseTreeException\
`6134` InvalidUpdateTypeException\
`6845` NoSuchExternalGroupToServerGroupMapException\
`9514` ExternalGroupAlreadyExistsException

## Conflicting

`1072` NoSuchCrashException\
`1072` NoSuchNetworkInterfaceException

`1046` InvalidProxyVersionException\
`1046` ProxyChannelNotFoundException

`1206` DuplicateChannelLabelException\
`1206` InvalidChannelAccessException

`1212` NoSuchSnapshotTagException\
`1212` SnapshotLookupException

`1213` InvalidParameterException\
`1213` NoSuchContentSourceException

`2500` InvalidLocaleCodeException\
`2500` InvalidTimeZoneException

`2756` InvalidProfileLabelException\
`2756` NoSuchKickstartInstallTypeException

`3000` IssDuplicateMasterException\
`3000` UnknownCVEIdentifierFaultException

`1` InvalidRepoUrlException\
`1` InvalidRepoUrlInputException\
`1` InvalidUserNameException

`2` InvalidRepoLabelException\
`2` InvalidRepoTypeException

`6134` InvalidUpdateTypeAndKickstartTreeException\
`6134` InvalidUpdateTypeAndNoBaseTreeException\
`6134` InvalidUpdateTypeException
