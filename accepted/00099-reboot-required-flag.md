## Feature Name: Reboot Required Flag for non-SUSE Distros
**Start Date:** 23/11/2023

### Summary
Expand reboot required indication in Uyuni’s WebUI to systems running non-SUSE operating systems.

### Motivation
The feature of showing in the Web UI when a system managed by Uyuni requires a reboot is currently exclusive to SUSE products, it is not supported for systems running non-SUSE operating systems. The feature proposed here will bring a more comprehensive reboot notification capacity encompassing Ubuntu, RHEL, Rocky, Alma, Oracle Linux, and other non-SUSE distributions, enhancing the support for these distros within Uyuni.

### Detailed Design

#### Current Approach Used for SUSE distributions
Currently, except for transactional systems (i.e. SUSE Linux Enterprise Micro), Uyuni lacks a system attribute to indicate directly whether a given system requires a reboot at a given moment. The information is derived from other attributes: the time of the last boot and the packages installed in the system. If a package has the “reboot suggested/needed/required” characteristic, and it was installed in a system after its last boot, Uyuni then shows in the WebUI that a reboot is required for this system. It is interesting to note that Uyuni is sensitive only to package installations. If a package removal or any other change causes a reboot to be required, this will not be detected by Uyuni. The “reboot suggested/needed/required” characteristic of a package is also derived from other data that is only available for SUSE distributions.


#### Proposed Solution

The proposed solution entails extracting information directly from the system to determine if a reboot is necessary. This data will be promptly integrated into the database, simplifying the process of identifying when a reboot is required. Thus, it eliminates the complexity associated with deriving this information from other database attributes. Additionally, it makes it possible to trigger a reboot requirement indication not just by package installations, as it currently stands, but also by other types of system modifications.

##### Reading from the systems that a reboot is required

The suitable way for checking if a reboot is required in a Linux system varies according to its family and version. Here, the following approach will be used:

- Debian/Ubuntu: check if `/var/run/reboot-required` file exists
- SUSE: check if `/boot/do_purge_kernels` or `/run/reboot-needed` file exists.
- Red Hat:
  - Major release >=8: check if the exit code of running `dnf -q needs-restarting -r` command is 1.
  - Major release < 8: check if the exit code of running `needs-restarting -r` command is 1.

##### Sending reboot information from system to master

The reboot required information will be collected in the system using a Salt beacon that will send a beacon event to the master only when it detects that a reboot is required. The beacon will keep in memory (using __context__ variable) that the reboot information was already sent and will not send it again, so that only one event will be fired, avoiding to overload the server with beacon events. As the __context__ variable resets after a system reboot, subsequent required reboots will be accurately detected and fired.

The `reboot_info` beacon, initially designed for transactional systems, will undergo enhancements to expand its functionality across diverse system families. This beacon is currently configured to run every 10 seconds by default and to fire an event always it detects a change in the reboot required status,  whether transitioning from required to not required or vice versa. The modifications in the beacon will include refining its behavior to prevent triggering events when a reboot isn't required. This adaptation aims to optimize the beacon's effectiveness across various system types while concurrently reducing the volume of events necessitating handling by the master.

Additionally, a boolean indicating whether a reboot is required or not will be included in package profile update in order to be possible updating the information in case of master losing the beacon event for any reason.

##### Storing reboot information

As the `reboot_info` beacon will be adapted to not fire events indicating that the reboot is not required, it is necessary to adapt the logic of the reboot required flag in server side. Currently there is a boolean database column `reboot_needed` at `suseMinionInfo` table for this purpose. This column will be modified to be a timestamp `reboot_required_after` and the server will need to compare this timestamp with the `uptime` of the system to determine if a reboot is required or not in a given moment.

##### Changing SUSE distributions approach

As it is possible to handle the reboot required information using the proposed approach, it will be used for all distributions. This implies changing the current approach for SUSE systems to not query package/patch metadata for this purpose. Thereby, there will be a standardized implementation for the feature. Furthermore, in large installations, the query to list systems requiring reboot will have a better performance.


### Drawbacks
- Maintaining and updating the code to accommodate future OS updates or changes becomes crucial. Additionally, handling new distributions or versions might require continuous modifications to it.
- In transactional systems, it is possible to manually remove a pending transaction causing a transition in reboot required status from required to not required. In the current proposal this kind of transition will not be sent to the master. In that case the user can run a package profile update to remove the reboot required flag. It seems to be a corner case, the risk will be accepted for now.

### Alternatives

#### Only collect the status in package profile update
Although there are other possible reasons why a reboot may be necessary (a kernel parameter change, for instance), the current approach for Suse distros is based only on packages/patch installation and seems to be enough for covering the most relevant use cases. Considering that a package profile update already runs after relevant package/patch changes, running an execution module to gather reboot required information together with package profile update will be enough to capture a big portion of the moments when reboot is required.

This alternative was considered because of the risk of overloading the server with beacon events, especially for large installations. However, the proposal includes a redesign of the `reboot_info` beacon to reduce the number of events it will send to master. However, opting to collect information solely on package profile updates, as opposed to the beacon approach, does have the drawback of potentially missing non-package related events that might cause a reboot to be required.


### Unresolved Questions
- ~~Should the strategy for identifying reboot required for SUSE distros be replaced for the sake of performance and standardization with other distros? Or is it a better idea to don’t change it considering that it is running for a long time and therefore it is stable?~~ Yes.
- ~~Is checking reboot information at the times of package changes (package profile update) sufficient to cover the most relevant use cases? While this strategy is currently employed for SUSE distros, should we be concerned with addressing other potential causes for reboots?~~ No it isn’t. The beacon approach will deal with other possible sources for reboot indication.

