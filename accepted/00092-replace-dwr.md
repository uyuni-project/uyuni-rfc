- Feature Name: Remove DWR
- Start Date: 2022-07-10

# Summary

Remove the DWR framework from SUMA.

# Motivation

## Why are we doing this?
DWR project has not an active community and does not appear to be under active development:
- its last version was released 5 years ago;
- the last change on its codebase was applied more than a year ago;
- [its official website and documentation](https://directwebremoting.org/) is not functional.

Additionally:
- As described [here](https://github.com/SUSE/spacewalk/issues/5967) there is a suspicion that the javascript files related to DWR could potentially unburden tomcat on situations of high overload; and
- The attributes of the `DWRSESSIONID` cookie, part of DWR library, are causing the following warning to appear in the browser logs (see [this issue](https://github.com/SUSE/spacewalk/issues/13995)):
```
Cookie “DWRSESSIONID” will be soon rejected because it has the “SameSite” attribute set to “None” or an invalid value, without the “secure” attribute. To know more about the “SameSite“ attribute, read https://developer.mozilla.org/docs/Web/HTTP/Headers/Set-Cookie/SameSite
```

## What use cases does it support?
DWR is a library that hide the details of request/response handling during AJAX interactions, it allows JavaScript code to use Java methods running on the backend just as if they were pure JavaScript code. Currently, it supports some features in Suma and the points where it is used are mapped as follows.

* `engine.js` is the core js file from DWR, it is imported in [`layout_head.jsp`](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/decorators/layout_head.jsp#L67) and referenced in [`template.js`](https://github.com/uyuni-project/uyuni/blob/master/web/html/src/styleguide/template.js#L31), so loaded in all pages.
* `util.js` is a js library that comes with DWR and contains utility functions that can be used to update HTML using js data. It is imported in [`layout_head.jsp`](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/decorators/layout_head.jsp#L68) and referenced in [`template.js`](https://github.com/uyuni-project/uyuni/blob/master/web/html/src/styleguide/template.js#L32), so also loaded in all pages. Its functions seem to be used only [here](https://github.com/uyuni-project/uyuni/blob/master/web/html/javascript/spacewalk-checkall.js#L193) and [here](https://github.com/uyuni-project/uyuni/blob/master/web/html/src/manager/audit/cveaudit/cveaudit.tsx#L119).
* **Dynamically generated JS files** - the following js files are generated dynamically by DWR, exposing some methods of Java classes as pure js functions that call the real code using Ajax requests. The classes and methods are defined in [`dwr.xml`](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/dwr.xml) file: 
  * `DWRItemSelector`: exposes the method [`select`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/taglibs/DWRItemSelector.java#L52) of the DWRItemSelector java class. It is loaded in [`layout_head.jsp`](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/decorators/layout_head.jsp#L69) and referenced in [template.js](https://github.com/uyuni-project/uyuni/blob/master/web/html/src/styleguide/template.js#L33), so loaded in all pages. The function is currently used in all the pages using the `rl:selectablecolumn` custom tag defined [here](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/taglibs/rhn-list.tld#L242), including SSM. **This seems to be the most risky component, since it is used across several pages**.
  * `ProxySettingsRenderer`: exposes [some methods](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/dwr.xml#L69-L71) of the [`ProxySettingsRenderer`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/renderers/setupwizard/ProxySettingsRenderer.java) class. It is loaded only in the [`proxy-settings.jsp`](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/admin/setup/proxy-settings.jsp#L5) file and used in the [`susemanager-setup-wizard-proxy-settings.js`](https://github.com/uyuni-project/uyuni/blob/master/web/html/javascript/susemanager-setup-wizard-proxy-settings.js) file. **There is a [closed (not implemented) issue](https://github.com/SUSE/spacewalk/issues/3340) to migrate the HttpProxy SetupWizard to ReactJS**.
  * `MirrorCredentialsRenderer`: exposes [some methods](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/dwr.xml#L58-L63) of the [`MirrorCredentialsRenderer`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/renderers/setupwizard/MirrorCredentialsRenderer.java) class. It is loaded only in the [`mirror-credentials.jsp`](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/admin/setup/mirror-credentials.jsp) file and the functions are used in the[`susemanager-setup-wizard-mirror-credentials.js`](https://github.com/uyuni-project/uyuni/blob/master/web/html/javascript/susemanager-setup-wizard-mirror-credentials.js) file. **There is a [closed (not implemented) issue](https://github.com/SUSE/spacewalk/issues/3341) to migrate the OrganizationCredentials SetupWizard to ReactJS**.
  * `ActionChainEntriesRenderer`: exposes the `renderAsync` method of the [`ActionChainEntryRenderer`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/renderers/ActionChainEntryRenderer.java) class. It is loaded only in the [`actionchain.jsp`](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/schedule/actionchain.jsp#L11) file and the function is used in the [actionchain.js](https://github.com/uyuni-project/uyuni/blob/master/web/html/javascript/actionchain.js#L26) file.
  * `ActionChainSaveAction`: exposes the `renderAsync` method of the [`ActionChainSaveAction`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/schedule/ActionChainSaveAction.java) class. It is loaded only in the [actionchain.jsp](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/schedule/actionchain.jsp#L12) file and the functions are used in the[actionchain.js](https://github.com/uyuni-project/uyuni/blob/master/web/html/javascript/actionchain.js#L132) file.
  * <sup>*</sup> `CriticalSystemsRenderer`: exposes the `renderAsync` method of the [`CriticalSystemsRenderer`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/renderers/CriticalSystemsRenderer.java) class. It is [loaded](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L24) and [used](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L64) only in the `yourrhn.jsp` file.
  * <sup>*</sup> `InactiveSystemsRenderer`: exposes the `renderAsync` method of the [`InactiveSystemsRenderer`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/renderers/InactiveSystemsRenderer.java) class. It is [loaded](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L12) and [used](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L55) only in the `yourrhn.jsp` file.
  * <sup>*</sup> `LatestErrataRenderer`: exposes the `renderAsync` method of the [`LatestErrataRenderer`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/renderers/LatestErrataRenderer.java) class. It is [loaded](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L21) and [used](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L78) only in the `yourrhn.jsp` file.
  * <sup>*</sup> `PendingActionsRenderer`: exposes the `renderAsync` method of the [`PendingActionsRenderer`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/renderers/PendingActionsRenderer.java) class. It is [loaded](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L27) and [used](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L71) only in the `yourrhn.jsp` file.
  * <sup>*</sup> `RecentSystemsRenderer`: exposes the `renderAsync` method of the [`RecentSystemsRenderer`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/renderers/RecentSystemsRenderer.java) class. It is [loaded](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L18) and [used](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L92) only in the `yourrhn.jsp` file.
  * <sup>*</sup> `SystemGroupsRenderer`: exposes the `renderAsync` method of the [`SystemGroupsRenderer`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/renderers/SystemGroupsRenderer.java) class. It is [loaded](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L30) and [used](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L85) only in the `yourrhn.jsp` file.
  * <sup>*</sup> `TasksRenderer`: exposes the `renderAsync` method of the [`TasksRenderer`](https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/action/renderers/TasksRenderer.java) class. It is [loaded](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L15) and [used](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp#L48) only in the `yourrhn.jsp` file.

  <sup>*</sup> All of these are only used in the [Your RHN](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/pages/yourrhn.jsp) page.

## What is the expected outcome?
SUMA working normally with the same AJAX requests being made and handled without any use of the DWR library.


# Detailed design

Although the solution could be a little risky, since it involves changes in a number of stable features, it is not so complex. The idea is to have a raw Servlet incorporated in SUMA working as backend for all the AJAX requests currently handled by the [DwrServlet](https://github.com/uyuni-project/uyuni/blob/master/java/code/webapp/WEB-INF/web.xml#L260). This servlet will be based on the URLs of the requests to determine which Java class to instantiate and which method to call on it.

For the frontend side, the capabilities provided by DWR (both the utility functions from `util.js` file and the ajax calls) are replaceable using jQuery.

Using a raw Servlet as backend will work as a first step making it possible to quickly remove the DWR library itself, without having to rewrite several pages and components using React.

The next step after removing the DWR library will be to remove the Ajax requests at all, concentrating all the communication between frontend and backend in the HTTP API. For that, it will be necessary to do the following:
 - Rewrite the Your RHN page using React, initially only with the intention of removing ajax calls, this strategy will provide a quick migration of that page.
 - Rewrite Setup Wizard (http proxy and organizational credentials configuration features) using React.
 - Rewrite action chain list and edit pages using React.
 - Replace all the tables using item selector in JSP pages to a React component. **This will also provide performance improvements on these pages**. The jsp pages using the `rl:selectablecolumn` custom tag are listed in the end of this document.
 

# Drawbacks

Why should we **not** do this?

Except for the [browser warning regarding DWRSESSIONID cookie](https://github.com/SUSE/spacewalk/issues/13995) that seems to be urgent, as it's likely that the requests are going to be rejected in some future version updates, there is no clear evidence of major problems using DWR and, in fact, it has been used for a long time in SUMA and seems to be stable.

# Alternatives

The first alternative is to just keep using DWR and try to solve the warning mentioned above, maybe trying to create a Pull Request on the DWR repository or even opening an issue on it.

The second alternative is to gradually replace the pages using DWR to use React. The main drawbacks of this alternative are: (1) some issues to migrate pages using DWR were aborted in the past, probably due to non technical decisions; and (2) the `rl:selectablecolumn` custom tag mentioned before is used in several JSP pages, it would be necessary to find an alternative to this component in order to avoid the need to migrate so many pages.

A hybrid approach could also be used, migrating some pages (specially the `Your RHN`) to React and applying the suggested solution (or even the first alternative) only in the remaining cases, reducing the risks.

# Unresolved questions

As mentioned, the changes are in stable features. Although we can test the features manually and use the testsuit to reduce the risks, the chances of breaking some stable feature still exist.


# Appendix:

 - Pages Using selectable column:

    |    |                  JSP Page                              |
    |----|--------------------------------------------------------|
    | 1  | activationkeys/list.jsp                                |
    | 2  | activationkeys/configuration/list.jsp                  |
    | 3  | activationkeys/configuration/subscribe.jsp             |
    | 4  | channel/subscribedsystems.jsp                          |
    | 5  | channel/targetsystems.jsp                              |
    | 6  | channel/manage/addpackages.jsp                         |
    | 7  | channel/manage/channelrepos.jsp                        |
    | 8  | channel/manage/comparepackagesmerge.jsp                |
    | 9  | channel/manage/erratapackagesync.jsp                   |
    | 10 | channel/manage/listremovepackages.jsp                  |
    | 11 | channel/manage/package/listremovecustompackages.jsp    |
    | 12 | common/fragments/activationkeys/groups.jspf            |
    | 13 | common/fragments/audit/scap-list.jspf                  |
    | 14 | common/fragments/configuration/copy2channels.jspf      |
    | 15 | common/fragments/configuration/copy2channels.jspf      |
    | 16 | common/fragments/errata/ownedlistdisplay.jspf          |
    | 17 | common/fragments/errata/selectableerratalist.jspf      |
    | 18 | common/fragments/manage/managers.jspf                  |
    | 19 | common/fragments/manage/subscribers.jspf               |
    | 20 | common/fragments/scheduledactions/listdisplay-new.jspf |
    | 21 | common/fragments/systems/group_listdisplay.jspf        |
    | 22 | common/fragments/systems/groups.jspf                   |
    | 23 | common/fragments/systems/system_listdisplay.jspf       |
    | 24 | configuration/channel/copy2systems.jsp                 |
    | 25 | configuration/sdc/viewfilescentral.jsp                 |
    | 26 | configuration/sdc/viewmodifyfilescentral.jsp           |
    | 27 | configuration/sdc/viewmodifyfileslocal.jsp             |
    | 28 | configuration/sdc/viewmodifyfilessandbox.jsp           |
    | 29 | errata/affectedsystems.jsp                             |
    | 30 | errata/cloneerrata.jsp                                 |
    | 31 | errata/packages/add.jsp                                |
    | 32 | errata/packages/list.jsp                               |
    | 33 | groups/adminlist.jsp                                   |
    | 34 | multiorg/channels/orglist.jsp                          |
    | 35 | schedule/completedsystems.jsp                          |
    | 36 | schedule/failedsystems.jsp                             |
    | 37 | ssm/packagelist.jsp                                    |
    | 38 | ssm/packageremove.jsp                                  |
    | 39 | ssm/packageupgrade.jsp                                 |
    | 40 | ssm/packageverify.jsp                                  |
    | 41 | ssm/systems/errata-list-fragment.jspf                  |
    | 42 | ssm/systems/misc/lock-unlock-system.jsp                |
    | 43 | systems/bootstrapsystemlist.jsp                        |
    | 44 | systems/errata.jsp                                     |
    | 45 | systems/registeredlist.jsp                             |
    | 46 | systems/systemsearch.jsp                               |
    | 47 | systems/details/packages/extra-packages-list.jsp       |
    | 48 | systems/details/packages/lockpkgs.jsp                  |
    | 49 | systems/details/packages/packagelist.jsp               |
    | 50 | systems/details/packages/packagelist.jspf              |
    | 51 | systems/details/packages/upgradable.jsp                |
    | 52 | systems/details/packages/profiles/compareprofiles.jsp  |
    | 53 | systems/details/packages/profiles/comparesystems.jsp   |
    | 54 | systems/duplicate/duplicatesystems.jsp                 |
    | 55 | systems/duplicate/duplicatesystemscompare.jsp          |
    | 56 | systems/sdc/pending_events.jsp                         |
    | 57 | systems/sdc/history/snapshots/tags.jsp                 |
