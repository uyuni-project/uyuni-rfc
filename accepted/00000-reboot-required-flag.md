## Feature Name: Reboot Required Flag for non-SUSE Distros
**Start Date:** 23/11/2023

### Summary
Expand reboot required indication in Uyuni’s WebUI to systems running non-SUSE operating systems.

### Motivation
The feature of showing in the Web UI when a system managed by Uyuni requires a reboot is currently exclusive to SUSE products, it is not supported for systems running non-SUSE operating systems. The feature proposed here will bring a more comprehensive reboot notification capacity encompassing Ubuntu, RHEL, Rocky, Alma, Oracle Linux, and other non-SUSE distributions, enhancing the support for these distros within Uyuni.

### Detailed Design

#### Current Approach Used for SUSE Distros
Currently, except for transactional systems (i.e. SLE Micro), Uyuni lacks a system attribute to indicate directly whether a given system requires a reboot at a given moment, the information is derived from other attributes: the time of the last boot and the packages installed in the system. If a package has the “reboot suggested/needed/required” characteristic, and it is installed in a system after its last boot, Uyuni then shows in the WebUI that a reboot is required for this system. It is interesting to note that Uyuni is sensitive only to package installations. If a package removal or any other change causes a reboot to be required, this will not be detected by Uyuni. The “reboot suggested/needed/required” characteristic of a package is also derived from other data that is only available for SUSE Distros.

  
#### Proposed Solution
The proposed solution is to introduce an execution module that reads directly from the system whether a reboot is required, following specific approaches according to the OS family and version. This execution module will run together with package profile update and the result will be persisted in the database using the `reboot_needed` column at `suseminioninfo` table. During a minion startup event the flag will be set to `false` assuming that the reboot should not be necessary anymore as the system is starting.

Although there are other possible reasons why a reboot may be necessary (a kernel parameter change, for instance), our current approach for SUSE distros is based only on packages/patch installation and seems to be enough for covering the most relevant use cases. Considering that a package profile update already runs after any package/patch change - even if it runs directly on the system - running the module together with package profile update should be enough for capturing when the reboot is required.

The suitable way for checking if a reboot is required in a Linux system varies according to its family and version. The execution module will use the following approach:
- Debian/Ubuntu: check if `/var/run/reboot-required` file exists
- Suse:
  - Major release >= 12: check if the exit code of running `zypper ps -s` command is 102.
  - Major release <12: check if `/boot/do_purge_kernels` file exists.
- RedHat:
  - Major release >=8: check if the exit code of running `dnf -q needs-restarting -r` command is 1.
  - Major release < 8: check if the exit code of running `needs-restarting -r` command is 1.

As it is possible to handle the reboot required information using the proposed execution module, this approach will be used for all distributions, except transactional systems. This implies changing the current approach for SUSE systems to not query package metadata for this purpose. Thereby, there will be a standardized implementation for the feature. Furthermore, in large installations, the query to list systems requiring reboot will have better performance.

  
### Drawbacks
- Once a reboot is required in a system and it is detected by the server, the proposed strategy for removing the flag is to consider that the reboot is no longer necessary when a startup event is received. However, the flag might be inappropriately removed when the salt minion process is restarted, without an actual system restart.
- As the proposed module will run together with package profile update, we can now detect a reboot requirement caused by a package removal, which is an improvement. However, the server will keep relying on package changes to check for reboot required, ignoring other factors might lead to missed reboot requirements.
- Maintaining and updating the execution module to accommodate future OS updates or changes becomes crucial. Additionally, handling new distributions or versions might require continuous modifications to the module.

### Alternatives

#### Salt Beacon
For transactional systems (i.e. SLE Micro), our current approach for detecting and showing the reboot required indication is based on a Salt Beacon that runs each 10 seconds directly in the client system and notifies the server whenever the need for reboot changes. This strategy will remain for transactional systems, but it would also be possible to extend it for other Linux distributions.

The main advantages of this strategy are:
 - Instantly detect the need for a reboot, regardless of what caused it.
 - Have a standardized way of checking for reboot required.

On the other hand, the main reason for not using this alternative is the risk of overloading the server with beacon events, especially for large installations. For example, applying a patch that makes a reboot to be required in multiple systems will prompt these client systems to transmit the beacon event in addition to package profile update, resulting in a doubling of the events that the server must process. Likewise, upon the client system reboot, the beacon will send the reboot required events just after the startup event.



#### Hybrid (Salt Beacon + execution module)
It's feasible to introduce a configuration property that determines the activation or deactivation of the reboot information beacon. Subsequently, the server would detect and display the 'reboot required' indication based on this property. If the beacon is active, the execution module's outcomes are ignored, and the flag isn't removed during the processing of startup event results. Conversely, when the beacon is inactive, we resort to employing the execution module strategy. Moreover, an automatic disabling of the beacon could be implemented if the server surpasses a certain threshold of registered minions, considering that performance issues would likely arise primarily in large installations.

However, the principal drawback of this approach lies in its inherent complexity, posing challenges in its implementation, comprehension, and maintenance in the future.


### Unresolved Questions
- Should the strategy for identifying reboot required for SUSE distros be replaced for the sake of performance and standardization with other distros? Or is it a better idea to don’t change it considering that it is running for a long time and therefore it is stable?
- Is checking reboot information at the times of package changes (package profile update) sufficient to cover the most relevant use cases? While this strategy is currently employed for SUSE distros, should we be concerned with addressing other potential causes for reboots?
