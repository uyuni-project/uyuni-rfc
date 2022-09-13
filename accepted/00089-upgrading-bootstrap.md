- Feature Name: Upgrading Bootstrap
- Start Date: 2022-07-27

# Summary
[summary]: #summary

Suma currently uses [Bootstrap 3](https://getbootstrap.com/docs/3.3/) as its core layout and design library. Bootstrap's styles are at the core of our theme, its components and layouts are used widely, and Bootstrap permeates every piece of UI in general. Bootstrap 3 [reached EOL in 2019](https://blog.getbootstrap.com/2019/07/24/lts-plan/) and no longer receives updates of any kind, including security updates. Bootstrap 3 has [known security vulnerabilities](https://snyk.io/test/npm/bootstrap/3.3.7) which we ship today. This RFC outlines a plan to upgrade to Bootstrap 5.  

# Motivation
[motivation]: #motivation

There are two main reasons to upgrade Bootstrap: ease of maintenance, and security issues.

Bootstrap 3 comes from an era where browser support was more complicated and it reflects in the stylesheets we have. The current bundled stylesheet for Suma is roughly 10k lines of CSS, which is hard to reason about and maintain to say the least. This problem isn't solely due to Bootstrap, but it is the primary source of the issue. The manner in which Suma has been styled over the years has been essentially add only: since the styles are tightly coupled yet globally shared, removing things has been hard while adding a single override for any given problem is fairly easy. This has resulted in our own themes becoming complex as well, on top of an already large Bootstrap base.  

As a separate issue, Bootstrap 3 has known security vulnerabilities, such as XSS injection, for which there won't be a patch. These security issues by themselves do not pose too serious of a threat due to the nature of the product, but they might be leveraged to create a chain of attacks. Given Suma is open source and has many moving parts, this is a very realistic attack vector.  

# Detailed design
[design]: #detailed-design

## Security issues

There are a few minor versions of Bootstrap 3 that we can upgrade which solve some of the issues we currently have. Following that, we can use the security advisories and previous patches to monkeypatch the remaining issues until we complete the migration.  

## Isolating stylesheets per page

The first revision of this RFC proposed simplifying exisrting stylesheets and then migrating them to Bootstrap 5. After testing this idea on a few isolated pages, this turned out to be prohibitively hard. Due to the stacked and fragmented nature of existing stylesheets, all changes need to be tracked through multiple layers in both the Uyuni and Suma theme, often across multiple places in the same file. While it is possible, it is very time consuming with very slow returns.  

What we can do instead is to first create tooling that allows developers to set different stylesheets for different pages, and then migrate existing styles over page by page, only keeping relevant styles for each page. Essentially this is a reversed version of the previous approach, where intead of moving bottom up, we move top down. This has the added benefit that there's less moving parts to handle during any one partial migration.

Adding the capability to use different stylesheets on different pages will allow us to keep using the old theme on all existing pages until they're migrated while working with new stylesheets on pages that we have confirmed to work correctly. For this we need to add some additional tooling around stylesheet loading and navigation.  

There are two main cases to handle: first navigation onto a page, and navigating between pages where some pages may be SPA pages, some legacy pages etc. Given a configuration file e.g. `list_of_updated_pages.conf` such as:

```
/rhn/foo-1
/rhn/foo-2
...
```

For initial navigation, `layout_head.jsp` can determine which stylesheet to use, in pseudocode:  

```
<c:choose>
  <c:when test="${currentPage exists in list_of_updated_pages.conf}">
    <link rel="stylesheet" href="/css/new/${webTheme}.css" />
  </c:when>    
  <c:otherwise>
    <link rel="stylesheet" href="/css/old/${webTheme}.css" />
  </c:otherwise>
</c:choose>
```

For the SPA navigation case, we need to hook into `window.pageRenderers.spaengine.navigate` to ensure the stylesheet can be swapped out depending on the target page. This means the configuration needs to be available for both JSP and JS pages.  

## Theme & styles

Bootstrap 3 uses Less while Bootstrap 5 only offers Sass styles. The two are sufficiently similar that when manually migrating styles there's a fairly small set of changes which need to be applied. Automatic translation tools exist as well, but current stylesheets make heavy use of Bootstrap 3 mixins which no longer exist in any shape or form in Bootstrap 5, so some manual effort is still required. This coupled with the numerous breaking styling changes going from 3 to 5 makes it more feasible to mostly manually migrate styles chunk by chunk.  

We already have component scoped styles working and in use, for those an additional mechanism will need to be added to allow those styles to be toggled based on the current page as well. This will allow us to apply scoped styles on components we have migrated and confirmed to work while keeping their old styles in use in pages that still need them. This should be a fairly isolated use case, but may have some small edge cases to cover.  

## Component and class name changes

This is tied to the previous section, but worth discussing on its own. Numerous component, layout and utility classes have been dropped or changed in both upgrades, e.g. `input-group-addon` was changed in Bootstrap 4 and dropped in 5, so we need to use `input-group-text` and check if it renders correctly etc. The list is pretty long. As discussed in [this ticket](https://github.com/SUSE/spacewalk/issues/18346), it's unlikely that we'd find a tool that can handle all different ways we use Bootstrap (in JSP, JPSF, React, etc), however writing a migration script similar to the Typescript migration might be feasible. For this, we can assemble a list that covers all the breaking changes that affect us by going through the list of changes for 4 and 5, checking whether we use the affected classes, and if so, write down what the upgrade path is.  

Following the partial migration plan outlined above, this would mean we need to stack class names for corresponding versions and clean them up once the migration is done. For example, for existing Bootstrap 3 code we might have `<div class="input-group-addon">`, then during the migration we might have `<div class="input-group-addon input-group-text">`, and after the migration is done, we can reduce back to `<div class="input-group-text">`. During the migration, only the class that exists in the given version of Bootstrap would match, meaning the other is a no-op.  

## Scripts

There are some scripting changes, e.g. static method names have changed `_foo()` → `foo()`, data properties have changed `data-foo` → `data-bs-foo` etc. This mostly concerns old pages and I would expect most issues here to be straightforward to fix once we get to a state where we can run the test suite on it.

## Summary

In short, the suggested upgrade path can be summarized as follows:  

 - Upgrade Bootstrap 3 to its latest minor version.  
 - Monkeypatch the remaining security issues based on prior work.  
 - Create tooling to use different stylesheets on different pages, including JSP, JS and CSS module logic.  
 - Gather the list of breaking changes to create an initial upgrade cookbook.  
 - Migrate pages and components one by one, updating the cookbook with any peculiarities we find. Shared components keep legacy classes where needed.  
 - Verify the results with Cucumber.  
 - Clean up legacy classes and update Cucumber tests accordingly.  
 - Clean up any dangling ends.  

# Drawbacks
[drawbacks]: #drawbacks

Suma is huge and the UI likewise. Last time we touched the theme to match corporate styling for 4.3.0 we broke Many Things and the tail end of layout issues is long. Realistically I would expect this upgrade to require considerable time with QA and testing. In an ideal case, the upgrade would be merged as early in a new version cycle as possible, as to give everyone the maximum amount of time possible to ensure the end result is up to par. 


# Alternatives
[alternatives]: #alternatives

The easiest alternative is to do nothing. We've been shipping Bootstrap 3 along with its known issues for a long time and so far it hasn't blown up in our face. Likewise, our current themes are hard to maintain, but so long as corporate branding doesn't change, there isn't too much to change day-to-day.
