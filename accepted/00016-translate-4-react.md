- Feature Name: l10n approach for React.js pages
- Start Date: 2015-12-24
- RFC PR: 16

# Summary

This RFC specifies:

* how l10n is bypassed in React.js components for the time being
* how proper l10n could be added when a requirement for it emerges with minimal code changes

# Motivation

We do not manage l10n right now as we only ship SUSE Manager in English, but we want to be ready to do it if at any time a requirement emerges.

We already have a way to do that for Spark/Jade pages, since we are building new web pages (or part of them) with React.js, we need to design a "skeleton implementation" for this technology too.


# Detailed design

## Current proposal (bypass)

* we implement a custom global Javascript function `t(s, ...)` that currently returns `s` as-is
  * as an exception, `{n}` substrings will be expanded like in current [Jade](https://github.com/SUSE/spacewalk/blob/Manager/java/code/src/com/suse/manager/webui/Languages.java#L50) and [JSP](https://github.com/SUSE/spacewalk/blob/Manager/java/code/src/com/redhat/rhn/common/localization/XmlMessages.java#L269) implementations
  * as an exception `@@` macros will be expanded like in the current [JSP](https://github.com/SUSE/spacewalk/blob/Manager/java/code/src/com/redhat/rhn/common/localization/XmlMessages.java#L249) implementation
* when a requirement emerges, we can implement a new `t` function that looks up translated strings from XML files in the format we use elsewhere in Manager using English texts as keys

## Suggestions for a full implementation

* `t` should look up translations from a JSON-served dictionary retrieved from the server
* this dictionary might be unique and static for the whole application ([see later](#one-big-json) for details)
* optionally the dictionary might be filtered server-side by page or component to only include relevant strings
* we will need a new method to request and load this dictionary, called during page load

Note that in all of the above points the interface of `t` will not change, so adopting it now will not limit us in future.

## One Big JSON

If we don't filter the dictionary we'll have a big bunch of translated strings in a JSON file, and this might be a performance concern.

The only "critical" point will be the first page call, when the single full JSON file will be:
 * downloaded from the server to the client
 * parsed

After that, the browser will cache it and the file will be already on the client ready to be read with no download-time (parsing cost will still apply).

### The test

I took the whole [`StringResources_en_US.xml`](https://github.com/SUSE/spacewalk/blob/Manager/java/code/src/com/redhat/rhn/frontend/strings/jsp/StringResource_en_US.xml) file from SUMA3, which contains most of the translated text we have accumulated so far and I converted it to a single JSON file with a `key:value` list of strings like:

```
[{
...
"Architecture":"Architecture",
"Release":"Release",
"Base Channel":"Base Channel",
"Created":"Created",
"Schedule action for no sooner than:":"Schedule action for no sooner than:",
"We're sorry, but the user could not be found.":"We're sorry, but the user could not be found.",
"@@PRODUCT_NAME@@ Admin?":"@@PRODUCT_NAME@@ Admin?",
...
}]
```

The resulting file contains more than 4000 strings and it takes about 500kB in non compressed form, about 56kB compressed. **Download time will be totally negligible**.

Once that this file is downloaded by the browser, it is mapped in *javascript* as an **hashmap**. The load time that the browser takes to parse this JSON file is about 7ms on my laptop. **Load time will be totally negligible as well**.

A complete demo is available in the folder */text/attachments/translate-4-react-demo/*.

### Adding a translated language into the current structure

In case of adding a new language, we would need to implement the following steps:

**Old pages**:

* Translate the file `StringResource_en_US.xml` for the desired language.

**New React Pages**:
In the new pages developed by React all the texts are already wrapped by the function `t()`.

* Generate a JSON file for the wanted language `{"key": "translation"}`, where the key is the string in English. 90% of the keys could be automatically generated but in some places, they are being injected by the server, so these ones have to be added manually
* Review wrong usages of the function `t()`: for instance t(`Items ${itemsVar}`) should be refactored to t("Items {0}", itemsVar) , there are some occurences of this misuse format
* Review if there are places where wrapping texts with the function `t()` was forgotten. This could be achieved changing the function `t()` to: `function t() { return "translated" }` and review all pages.
* Add warnings or javascript lint rules to avoid missing translations in the future


# Drawbacks

* we have to implement `t` ourselves and maintain it
  * but it's trivial at the moment and will not be complex when we implement l10n fully
* we do not get [pluralization](#pluralization)
  * but we do not have it anywhere else in the Manager code base, so adding it here makes no sense unless we plan to add it to JSPs and Jade as well

**Note that correct pluralization is fundamentally incompatible with the bypass concept**. Here we are trading ease of use right now with having to implement pluralization properly later.

## Pluralization

*Languages vary in how they handle plurals of nouns or unit expressions ("hours", "meters", and so on). Some languages have two forms, like English; some languages have only a single form; and some languages have multiple forms. They also vary between cardinals (such as 1, 2, or 3) and cardinals (such as 1st, 2nd, or 3rd), and in ranges of cardinals (such as "1-2", used in expressions like "1-2 meters long").* (Language Plural Rules)[http://www.unicode.org/cldr/charts/25/supplemental/language_plural_rules.html]

e.g. Polish has the singular, the "not too many" plural (for 2-4 objects) and the "many" plural (more than 4 objects)

| English     | Polish         |
|-------------|----------------|
| one lion    | jeden **lew**  |
| two lions   | dwa **lwy**    |
| five lions  | pięć **lwów**  |


# Alternatives

## React-Translate-Component

A **general disappointing point**: implementing react components adds complexity because they are built to be used server-side on top of *Node.js* since it builds a stack of many `required` external *components and libraries*. To move this to **client-side** we have to use [browserify](http://browserify.org/). Roles of this library are:
* download all dependencies
* generate a *bundle.js* container for dependencies
* serve the whole bundle to the client

As an alternative, the analyzed component is [react-translate-component](https://github.com/martinandert/react-translate-component)

Pros:
* it manages pluralization
* it deeply integrated with the React.js technology
* it works on its own like an api
* it is mantained from external developers

Cons:
* it adds a layer of complexity
* the "bundle.js" file can grow pretty fast
* we need to pass the translation file in some way to the component
because it just manages switching locales from a given source
* implementing a "true bypass" would not be trivial at all


## Polyglot.js Javascript Library

An alternative from another level is to add an external standardized *Javascript* library instead of creating our own `t` function. The analyzed library is [Polyglot.js](http://airbnb.io/polyglot.js/)

Pros:
* it is standardized
* it is mantained from external developers
* it manages pluralization (alternatively to bypass, not both)

Cons:
* it uses `%{}` as a standard replacement format instead of our current custom JSP and Jade format `{}`, then a mixed pages with Jade and React could have a string replacement somewhere with `%{}` and somewhere else with `{}`
* only bypass or pluralization usage is possible, not both

**Note that mixed repalcement format exists for any external library in this layer.**


# Unresolved questions

* in case we do implement i10n fully, if and how to implement filtering


