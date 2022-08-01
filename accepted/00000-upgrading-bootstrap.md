- Feature Name: Upgrading Bootstrap
- Start Date: 2022-07-27

# Summary
[summary]: #summary

Suma currently uses [Bootstrap 3](https://getbootstrap.com/docs/3.3/) as its core layout and design library. Bootstrap's styles are at the core of our theme, its components and layouts are used widely, and Bootstrap permeates every piece of UI in general. Bootstrap 3 [reached EOL in 2019](https://blog.getbootstrap.com/2019/07/24/lts-plan/) and no longer receives updates of any kind, including security updates. Bootstrap 3 has [known security vulnerabilities](https://snyk.io/test/npm/bootstrap/3.3.7) which we ship today. This RFC outlines a plan to upgrade to Bootstrap 5.  

# Motivation
[motivation]: #motivation

There are two main reasons to upgrade Bootstrap: ease of maintenance, and security issues.

Bootstrap 3 comes from an era where browser support was more complicated and it reflects in the stylesheets we have. The current bundled stylesheet for Suma is roughly 10k lines of CSS, which is hard to reason about and maintain to say the least. This problem isn't solely due to Bootstrap, but it is the primary source of the issue. The manner in which Suma has been styled over the years has been essentially add only: since the styles are tightly coupled yet globally shared, removing things has been hard while adding a single override for any given problem is fairly easy. This has resulted in our own themes becoming complex as well, on top of an already large Bootstrap base.  

As a separate issue, Bootstrap 3 has known security vulnerabilities, such as XSS injection, for which there won't be a patch. These security issues by themselves do not pose too serious of a threat due to the nature of the product, but they might be leveraged to create a chain of attacks. Given Suma is open source and has many moving parts, this is a very realsitic attack vector.  

The core proposition of this RFC can be summarized in two steps:  

 1. Simplify our existing stylesheets to reduce the use of custom overrides, and try and compose views and layouts using standard Bootstrap solutions. This step is beneficial even without the Bootstrap upgrade in mind, as currently our stylesheets are simply very convoluted and hard to reason about.  
 2. Upgrade Bootstrap. This includes many moving parts which will be outlined below.  

Coming out successfully from the other side, we would hope to have simpler stylesheets with less to maintain, and fewer security issues.  


# Detailed design
[design]: #detailed-design

## Theme & styles

Bootstrap 3 uses Less while Bootstrap 5 only offers Sass styles. This switch by itself is not very problematic, however there are additional issues that make the upgrade more difficult. Our current styles make heave use of numerous mixins from Bootstrap 3 which no longer exist in Bootstrap 5. Additionally, there are numerous breaking styling changes going from 3 to 4 and even more so moving from 4 to 5.  

Instead of trying to manually migrate our existing very large theme source, I propose we instead try to first reduce our existing theme footprint as much as possible. We already have component scoped styles working and in use, so we can try move component or view specific styles (e.g. table styles, setup wizard etc) into component scoped styles and remove them from the global stylesheet.  

This allows us to cut up the effort required and do at least some of the work gradually. I suspect the last core theme change will still be painful, though. It might be easier to rebuild the existing theme from the base Bootstrap style rather than migrating the existing one, but this is something we can consider after we've simplified the theme.  

## Component and class name changes

This is tied to the previous section, but worth discussing on its own. Numerous component, layout and utility classes have been dropped or changed in both upgrades, e.g. `input-group-addon` was changed in Bootstrap 4 and dropped in 5, so we need to use `input-group-text` and check if it renders correctly etc. The list is pretty long. As discussed in [this ticket](https://github.com/SUSE/spacewalk/issues/18346), it's unlikely that we'd find a tool that can handle all different ways we use Bootstrap (in JSP, JPSF, React, etc), however writing a migration script similar to the Typescript migration might be feasible. For this, we can assemble a list that covers all the breaking changes that affect us by going through the list of changes for 4 and 5, checking whether we use the affected classes, and if so, write down what the upgrade path is.  

## Scripts

There are some scripting changes, e.g. static method names have changed `_foo()` → `foo()`, data properties have changed `data-foo` → `data-bs-foo` etc. This mostly concerns old pages and I would expect most issues here to be straightforward to fix once we get to a state where we can run the test suite on it.

## Summary

In short, the suggested upgrade path can be summarized as follows:  

 - Simplify the existing styles, trying to use standard Bootstrap tooling wherever possible
 - Gather the list of breaking changes
 - Write a migration script and/or manually migrate the above list
 - Migrate existing styles from Less to Sass
 - Verify the results with Cucumber
 - Clean up any dangling ends

# Drawbacks
[drawbacks]: #drawbacks

Suma is huge and the UI likewise. Last time we touched the theme to match corporate styling for 4.3.0 we broke Many Things and the tail end of layout issues is long. Realistically I would expect this upgrade to require considerable time with QA and testing. In an ideal case, the upgrade would be merged as early in a new version cycle as possible, as to give everyone the maximum amount of time possible to ensure the end result is up to par. 


# Alternatives
[alternatives]: #alternatives

The easiest alternative is to do nothing. We've been shipping Bootstrap 3 along with its known issues for a long time and so far it hasn't blown up in our face. Likewise, our current themes are hard to maintain, but so long as corporate branding doesn't change, there isn't too much to change day-to-day. It is possible to go ahead with the stylesheet simplification etc by itself without upgrading Bootstrap.  

# Unresolved questions
[unresolved]: #unresolved-questions

TODO: Will be added as they surface.
