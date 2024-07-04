# Uyuni RFCs

Many changes, including bug fixes and documentation improvements, can be implemented and reviewed via the normal GitHub pull request workflow. Some changes though are "substantial" - those should be put through an appropriate design process and produce a consensus among the Uyuni core team.

The "RFC" (request for comments) process is intended to provide a consistent and controlled path for such substantial changes to enter the project. This process will be adjusted over time as more features are implemented and the community settles on specific approaches to feature development.

## TL;DR

* Make sure you have Git commit signing enabled. If you are not doing it already, check out the [GitHub documentation](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification).
* Fork https://github.com/uyuni-project/uyuni-rfc
* Copy `00000-template.md` to `accepted/00000-my-feature.md`
  - 'my-feature' should be as descriptive as possible.
  - please don't assign an RFC number yet.
* Write the content, based on the [RFC template](0000-template.md).
* Open a Pull Request and discuss it.
* When the discussion is finished and the PR ready to be merged, lookup the next free number in master and rename the file.

Once the PR is merged, [implementation can start](#first-principles).

The Uyuni core team will work towards reviewing the set of open RFC pull requests and provide feedback on a weekly basis. All community members are invited to discuss the open pull requests.

## When to follow this process

You should consider using this process if you intend to make "substantial" changes to Uyuni or its documentation. Some examples of what typically requires an RFC are:

   - A new feature that creates new API surface area.
   - Architectural changes or introduction of new conventions.
   - Any disruptive changes in the user experience.
   - The removal of features that were already shipped.

The RFC process encourages discussions about a proposed feature during its early stages, in order to incorporate important constraints into the design. It is a great opportunity to get more eyeballs on your proposal before it becomes a part of a released version of Uyuni. Quite often, even proposals that seem "obvious" can be significantly improved once a wider group of interested people have a chance to weigh in.

#### Changes that do **NOT** require an RFC

  - Bug fixes.
  - Rephrasing, reorganizing or refactoring.
  - Improvements in test coverage or documentation.
  - UI improvements on existing features.

## First principles

- A RFC is considered 'accepted' when it gets merged into the `uyuni-rfc` repository.
- Once an RFC becomes accepted, the feature can be implemented and submitted as a pull request to the Uyuni repository.
- This does not mean the feature will be merged - only that the core team has agreed to it in principle.
- The fact that a given RFC has been accepted implies nothing about its implementation priority.
- Modifications to accepted RFC's can be done in follow-up pull requests.
- We should strive to write each RFC in a way that reflects the final design of the feature; however, during implementation or afterwards things can change. The RFC only documents design decisions at the time it was merged.
- some unimplemented RFCs are published in the unimplemented/ subdirectory for historical/inspirational purposes.

### Implementation

Writing an RFC and implementing the feature are two distinct steps. The author of the RFC is not obligated to implement it. Of course, the RFC author (like any other developer) is welcome to contribute with an implementation after the RFC has been reviewed and merged.

If you are interested in implementing an 'accepted' RFC, but unable to determine if someone else is already working on it, please ask at uyuni-devel@opensuse.org.

The Uyuni team expects that all development work is tracked in GitHub issues. Please validate that a related issue exists (or create one otherwise) before starting to implement any accepted RFC.

- - -

This RFC process owes its inspiration to the [React RFC process], [Yarn RFC process], [Rust RFC process], and [Ember RFC process].

[React RFC process]: https://github.com/reactjs/rfcs
[Yarn RFC process]: https://github.com/yarnpkg/rfcs
[Rust RFC process]: https://github.com/rust-lang/rfcs
[Ember RFC process]: https://github.com/emberjs/rfcs
