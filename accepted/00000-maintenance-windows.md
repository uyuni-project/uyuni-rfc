- Feature Name: Maintenance Windows
- Start Date: 2020-03-31
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

Define Maintenance Windows in Uyuni and assign them to systems

# Motivation
[motivation]: #motivation

Customers have company policies to perform changes on systems only at specific points in time.
This is typically called "Maintenance Window".

Uyuni should be able to define them and prevent executing of actions outside of such a window.

# Architecture
[architecture]: #architecture

A system is in "Maintenance Mode" or not.
When a system is not in "Maintenance Mode" no action can be executed.
Setting the Maintenance Mode "on" and "off" requires Organization Admin permissions.
A "Maintenance Window" does nothing else than turning Maintenance Mode "on" when the window starts
and "off" when it ends.

Defining Maintenance Windows requires Organization Admin permissions.

Maintenance Windows are defined on system level.
Every System can get 1 Schedule assigned.
A Schedule can be used for multiple systems.
Inside of the Schedule, multiple Maintenance Windows can be defined.
They can be defined as individual or as recurring events.

To assign a Schedule to multiple systems, SSM should be used.
An equivalent XMLRPC function should be implemented as well taking a list of system ids.


# Detailed design
[design]: #detailed-design

## First Iteration

In the first iteration we limit the implementation to load and update maintenance schedules
and scheduling actions inside of maintenance windows.

Enforcing Maintenance Windows on lower level is part of the future iterations and will be defined later
in updates of this RFC.


### Implement a Maintenance Mode

For now the Maintenance Mode is a method called on a system object which lookup the schedule and check
if we are currently inside of a defined maintenance window or not. There maybe some functionalities
which require this information.

Putting a system manual into maintenance mode is a feature of the second iteration.


### Maintenance Window

A Maintenance Window specify a time when changes on a system can be applied.
- It has a start date-time and an end date-time.
- It can be defined as recurring interval (RRULE).
- Exceptions should be supported (EXDATE)
- Events for a full day (anniversary) or multiple days must be considered.
- The Summary may define the schedule name (See also Maintenance Schedule).

For practical reasons the window describes when an action can be `started`.
As it is unpredictable to know how long an action will take, we cannot calculate,
if the action can also be `finished` inside of the Maintenance Window.

A started Action should always be finished to not risk a broken system.

#### Action Chains

Action Chains with reboots are split into multiple actions.
As the goal is, that everything what was started inside of a maintenance window should also be finished,
we need to finish whole action chains also after the window closed.

If we won't do it, we would end up with broken systems.


### Maintenance Schedule

A Maintenance Schedule is a set of Maintenance Windows. A Maintenance Schedule has a name/label.
The data should be stored as ICalendar data (https://tools.ietf.org/html/rfc5545).
In the first iteration importing the data created by an external tool is required.
Uyuni will not provide a User interface for generating or manipulating Maintenance Windows.

This is a task for future iterations.

To parse the windows we need a library for ICalendar files. E.g. ical4j(https://github.com/ical4j/ical4j).

There could be two types of Schedules for the first iteration

1. One ICalendar file represent one schedule

Every `VEVENT` describe a maintenance window.

2. One ICalendar file contains multiple schedules

Every `VEVENT` must have a `SUMMARY`. All events with the same "summary" belong to the same schedule.
The summary must match the schedule name in the Uyuni Database.

#### Timezone

The ICalendar entry defines the timezone. Uyuni must of cause respect it. When showing the Maintenance Windows
in the User Interface, they should be converted into the timezone set in the user preferences.


### Adding a new Maintenance Schedule

In the left sidebar a new page should be added below `Schedule`.
In this page you can see a list of existing schedules. You can edit them, when you select an existing schedule.
There should be a "Create Maintenance Schedule" link in the upper left corner which open a new page where the following values can be specified:

- Schedule Name
- Schedule Type (Single, Multi, ....)
- Data (ICalendar content) with file upload option

A "Create" button will create the new schedule. The ICalendar data are stored in the database.

Adding a Maintenance Schedule via XMLRPC API must be possible as well.


### Updating/Removing a Maintenance Schedule

A Maintenance Schedule will change over the time. A Maintenance Window will be moved or removed on short notice,
or a new Maintenance Window slot will be created.

This happens while updating the ICalendar data of a maintenance schedule.

While adding a new slot is a non-issue, the movement or removal of a window needs to be handled properly.

As it is nearly impossible to identify a change of a special event we need to follow a different strategy.
When we refresh or upload a changed ICalendar file, we need to re-evaluate all scheduled actions of systems using the
new schedule.
We also need to provide a resolve strategy. This can happen while implementing modules to move actions
to a different time. Possible modules could be:

- Nearest: Use the nearest maintenance window
- Previous: Use the maintenance window before the scheduled date
- Next: Use the maintenance window after the scheduled date
- Cancel: Cancel the Action
- Fail: do not import the new schedule at all and keep the existing one

The customer can configure the order:

  resolveStrategy=Nearest,Previous,Next,Fail

The resolve strategy is also needed when updating the Maintenance Schedule via XMLRPC API.

Removing a maintenance schedule from a system can happen at any point in time as all scheduled actions remain valid.


### Actions and Maintenance Windows

Some Actions can be executed at any time, others should be executed only inside of Maintenance Windows.
Every Action in Uyuni has an entry in the Database which already defines if it can be executed on "Locked" Systems.
We define a second flag which say, if that action can be executed on systems not in maintenance mode.

 id  |                      label                      |                                                name                                                | maintenance_mode_only 
-----|-------------------------------------------------|----------------------------------------------------------------------------------------------------|----------------------
   1 | packages.refresh_list                           | Package List Refresh                                                                               | N
   2 | hardware.refresh_list                           | Hardware List Refresh                                                                              | N
   3 | packages.update                                 | Package Install                                                                                    | Y
   4 | packages.remove                                 | Package Removal                                                                                    | Y
   5 | errata.update                                   | Patch Update                                                                                       | Y
   6 | up2date_config.get                              | Get server up2date config                                                                          | Y
   7 | up2date_config.update                           | Update server up2date config                                                                       | Y
   8 | packages.delta                                  | Package installation and removal in one RPM transaction                                            | Y
   9 | reboot.reboot                                   | System reboot                                                                                      | Y
  10 | rollback.config                                 | Enable or Disable RPM Transaction Rollback                                                         | Y
  11 | rollback.listTransactions                       | Refresh server-side transaction list                                                               | N
  12 | rollback.rollback                               | RPM Transaction Rollback                                                                           | Y
  13 | packages.autoupdate                             | Automatic package installation                                                                     | Y
  14 | packages.runTransaction                         | Package Synchronization                                                                            | Y
  15 | configfiles.upload                              | Upload config file data to server                                                                  | N
  16 | configfiles.deploy                              | Deploy config files to system                                                                      | Y
  17 | configfiles.verify                              | Verify deployed config files                                                                       | N
  18 | configfiles.diff                                | Show differences between profiled config files and deployed config files                           | N
  19 | kickstart.initiate                              | Initiate an auto installation                                                                      | Y
  20 | kickstart.schedule_sync                         | Schedule a package sync for auto installations                                                     | N
  21 | activation.schedule_pkg_install                 | Schedule a package install for activation key                                                      | N
  22 | activation.schedule_deploy                      | Schedule a config deploy for activation key                                                        | N
  23 | configfiles.mtime_upload                        | Upload config file data based upon mtime to server                                                 | N
  24 | solarispkgs.install                             | Solaris Package Install                                                                            | Y
  25 | solarispkgs.remove                              | Solaris Package Removal                                                                            | Y
  26 | solarispkgs.patchInstall                        | Solaris Patch Install                                                                              | Y
  27 | solarispkgs.patchRemove                         | Solaris Patch Removal                                                                              | Y
  28 | solarispkgs.patchClusterInstall                 | Solaris Patch Cluster Install                                                                      | Y
  29 | solarispkgs.patchClusterRemove                  | Solaris Patch Cluster Removal                                                                      | Y
  30 | script.run                                      | Run an arbitrary script                                                                            | Y
  31 | solarispkgs.refresh_list                        | Solaris Package List Refresh                                                                       | Y
  32 | rhnsd.configure                                 | SUSE Manager Network Daemon Configuration                                                          | N
  33 | packages.verify                                 | Verify deployed packages                                                                           | N
  34 | rhn_applet.use_satellite                        | Allows for rhn-applet use with an Spacewalk                                                        | N
  35 | kickstart_guest.initiate                        | Initiate an auto installation for a virtual guest.                                                 | Y
  36 | virt.shutdown                                   | Shuts down a virtual domain.                                                                       | Y
  37 | virt.start                                      | Starts up a virtual domain.                                                                        | Y
  38 | virt.suspend                                    | Suspends a virtual domain.                                                                         | Y
  39 | virt.resume                                     | Resumes a virtual domain.                                                                          | Y
  40 | virt.reboot                                     | Reboots a virtual domain.                                                                          | Y
  41 | virt.destroy                                    | Destroys a virtual domain.                                                                         | Y
  42 | virt.setMemory                                  | Sets the maximum memory usage for a virtual domain.                                                | Y
  43 | virt.schedulePoller                             | Sets when the poller should run.                                                                   | Y
  44 | kickstart_host.schedule_virt_host_pkg_install   | Schedule a package install of host specific functionality.                                         | N
  45 | kickstart_guest.schedule_virt_guest_pkg_install | Schedule a package install of guest specific functionality.                                        | N
  46 | kickstart_host.add_tools_channel                | Subscribes a server to the Spacewalk Tools channel associated with its base channel.               | N
  47 | kickstart_guest.add_tools_channel               | Subscribes a virtualization guest to the Spacewalk Tools channel associated with its base channel. | N
  48 | virt.setVCPUs                                   | Sets the Vcpu usage for a virtual domain.                                                          | Y
  49 | proxy.deactivate                                | Deactivate Proxy                                                                                   | N
  50 | scap.xccdf_eval                                 | OpenSCAP xccdf scanning                                                                            | N
  51 | clientcert.update_client_cert                   | Update Client Certificate                                                                          | Y
 500 | image.deploy                                    | Deploy an image to a virtual host.                                                                 | N
 501 | distupgrade.upgrade                             | Service Pack Migration                                                                             | Y
 502 | packages.setLocks                               | Lock packages                                                                                      | N
 503 | states.apply                                    | Apply states                                                                                       | Y
 504 | image.build                                     | Build an Image Profile                                                                             | N
 505 | image.inspect                                   | Inspect an Image                                                                                   | N
 506 | channels.subscribe                              | Subscribe to channels                                                                              | N

(That list is currently the full action list. Not all actions are still in use)


### Schedule an Action

When a system is assigned to a maintenance schedule, actions which are flagged as `maintenance_mode_only` should be executed only within a maintenance window.
In the User Interface we should show in these cases not the datepicker, but a simple Combo box with the Date and Time of the next 20 Maintenance Windows.
By default all actions will be scheduled at the begin of the Maintenance Window.

If possible add another selector for the time to delay the start of the action to a later point inside of the maintenance window.
This could also be implemented in the 2nd iteration.

When using SSM it is possible that systems have different maintenance windows. The combination systems belong
to one maintenance schedule and systems without maintenance schedule is not critical. The action would be scheduled
at a time which is inside of a maintenance window of the systems which belong to the schedule.

Systems in different schedules needs special handling. We could implement 2 options:

1. divide systems by maintenance schedules and display a combo box with the names. Let the user choose for which set he want to schedule it. He need to repeat it for the rest.
2. As an alternative we provide via a Radio Button the Option "Next available Maintenance Window". This would apply for all systems in SSM.

Scheduling an Action via XMLRPC outside of a maintenance window will result into an error.
XMLRPC API called to list windows or get the next window can help to make the API usable.


### Assign a Maintenance Schedule to a System

There could be multiple ways to assign systems to maintenance schedules.

- In the systems details page we need to show the selected schedule with a view and a change option.
- It should be possible to change the maintenance schedule for multiple systems using SSM
- In the details of the Maintenance Schedule we could have a systems page where add/remove is possible.

When a system is assigned to a new Maintenance Schedule, all future actions for this system should be canceled.
The list of canceled actions should be shown.

The information if a Maintenance Schedule is assigned to a system and which Schedule, should be visible in the systems details page.
Implementation of XMLRPC functions for getting and setting the current maintenance schedule must be implemented.
For setting a schedule should be possible for multiple systems using an array of system ids.

## System in Maintenance Mode

The current status of the system should be reflected in the User Interface and API.

If a system is in Maintenance Mode, the User Interface could show a special icon.
Suggestion: https://www.iconfinder.com/icons/2639855/maintenance_icon

In the XMLRPC API a flag could be added to `system.getDetails()`.
A special function `system.listSystemsInMaintenanceMode()` should be added as well.


## Recurring Actions

Recurring Actions are scheduled using a cron like syntax. It may not be aligned to a
Maintenance Schedule defined via ICalendar.

When it happens that an Recurring Action is executed outside of a maintenance window, it should be skipped.
A warning should be logged and maybe a Notification raised.

The customer need to take care to align the two schedules.

Define recurring Maintenance Windows and align them with Recurring Actions.
When a Maintenance Window in such a series was excluded and an alternative window added, a one time highstate action must be scheduled by the admin.

Randomly appearing Maintenance Windows cannot be handled.


### Traditional Clients

We will not implement something special for traditional clients. For the first iteration we take care
that actions are scheduled only inside of maintenance windows. This would apply also for traditional clients.

As long as the traditional client uses osad, or `rhn_check` is executed inside of the maintenance window
the feature would work for them as well.

We will document in the manual, that for traditional clients actions are also executed outside of Maintenance Windows
if `rhn_check` is executed only at a later point in time.

## What 3rd party tools to create schedules

We require customers to use 3rd party tools to create the ICalendar files.
We need to test the most common used tools to generate them.

- office 365 / outlook
- google calendar
- confluence ?

For Uyuni users Linux tools might be interesting
- korganizer
- Lightning (Thunderbird Extension)
- evolution


## Notifications

When a system is assigned to a maintenance schedule, every finished action should check, if the system is still in maintenance mode.
If this is not the case it means, the action was started inside of the maintenance window, but was not able to finish in time.
This Maintenance Window overflow should be show with a notification.
Ideally we should have only one notification per maintenance window, not per client which cause the overflow.
It is not an `error`, but it show the admin that the window might needs to get increased for the next runs.

## Cluster

Cluster defined in Uyuni needs to be handled in a special way. All nodes of the cluster are readonly and changes
are applied only via a dedicated Cluster Manager.

For Maintenance Windows we can define a `None Schedule` which defines no Maintenance Window and assign this schedule to
all nodes of a cluster. This prevent to schedule any action on the cluster nodes.

The Cluster Provider Manager may not be a system object and therefor need a special assignment of a maintenance schedule.
More details will follow when we know more about the cluster implementation.


## Second Iteration

### Implement a Maintenance Mode override

Put a system manually into "Maintenance Mode". This is useful in emergency situations where a system is down
and needs to be fixed quickly.
An API call should be implemented to do it. The required permissions needs to be discussed.
Either a normal admin of the system could get the permissions to do this, or it still required organization admin permissions.
This requires further discussion.

Some companies might require to follow a workflow to put a machine into maintenance mode.
To make this feature also usable for them, it should be possible to disable manual setting of the maintenance mode.

Bringing a server back to production mode earlier than the maintenance window close is another feature which
could be implemented in the second iteration.

All this would require a trigger mechanism which execute changes on the system to reflect the maintenance mode.


#### Emergency Maintenance Mode

When a system is put into Maintenance Mode manually, it mostly happen because of an emergency case.
It should allow to perform the necessary steps to fix the issue and bring the system or application
back online.

When a system is currently in Maintenance Mode, it should be possible to schedule actions "now" and for the next minute.


#### Enforcing the Maintenance Mode on the client side

With the proposal of the first iteration, we do not enforce the maintenance mode on system level.
As long as nobody uses the salt bus directly, this is a non-issue.

There needs to be discussions around how to implement such an enforcement.
Using the current existing blackout mode for salt minions is too broad to differentiate between
allowed and disallowed actions.

The following actions needs be be considered:

- Image Building (Container and Kiwi Images)
- Create of new machines and Virtual Machines
- Salt Boot

All use `state.apply` but might be wanted to run outside of Maintenance Mode.

As a solution we could enhance the minion blackout mode to check for metadata provided with the call.
This would prevent "accidents", but would not really enforce the maintenance mode as everybody
who has direct access to salt could set the required headers execute things when the system is not
in Maintenance Mode.


### Manage Maintenance Schedules

It should be possible to add a URL to an iCalendar file and maybe implement CalDav support.


### Assign a Maintenance Schedule to a System

- adding a system to a Maintenance Schedule via activation key at onboarding time. This requires changes on the activation key.


# Drawbacks
[drawbacks]: #drawbacks


# Alternatives
[alternatives]: #alternatives

# Unresolved questions
[unresolved]: #unresolved-questions


# Info

## List of ICalendar fields we need

- SUMMARY
- RRULE
- EXDATE
- RDATE
- DTSTART
- DTEND
