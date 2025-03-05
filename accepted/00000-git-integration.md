- Feature Name: Git integration
- Start Date: 2024-04-23

# Summary
[summary]: #summary

This is a feature which will add a git integration to Uyuni without the need to use gitfs. It would be possible to sync formulas and playbooks and use them with an existent infrastructure.

# Motivation
[motivation]: #motivation

- Why are we doing this?
The git integration is not existent or it the depends from gitfs which is unstable

- What use cases does it support?
For all users which have a lot of self-written salt formulas and ansible-playbooks.
For all users that have multiple git repositories and branches which would like to deploy based on environment(env for ansible should be taken from the inventory file)

- What is the expected outcome?
Use salt formulas and ansible playbooks which are stored on git repositories
Use them against clients managed by Uyuni


# Detailed design
[design]: #detailed-design

It should be designed on four parts:

The first part would be done by a container that is responsible to sync the git repositories and sort it out per type of the provisioning tool.
 - If that is a ansible playbook it would be scanned(find $path for a role infrastructure)
 - If that is a salt formula it should be done by the states delivered by the repository
 - Path structure:
   - Ansible: $local/ansible/roles, $local/ansible/collections,  $local/ansible/inventory, $local/ansible/config
   - Salt: $local/salt/states
- All the data would be saved in a volume which would be shared with the suma container - e.g. $provisioning
- A customer could add multiple git repositories and multiple branches - it would make easier to deploy formulas / playbooks based in a environment, like LCM do with repositories and promotion

The second part it would be done for a md5/sha256sum check. If possible, also a scan that could be done for a container with e.g. clamav to check if there any viroses / trojans being imported into the clients being managed by Uyuni.

The third part will be dependent from the the first two parts. If everything runs right that would be processed either by the salt master from Uyuni or the ansible control node - so here will probably smart to get rid of the manual configuration from the ansible playbooks and inventories and parse the configuration which will be delivered by the shared volume.

The fourth part would be a normalization from this content from the user and commit it to a different repository that would be used by Uyuni. The motivation here is to have a standard path infrastructure that makes easy the onboarding on Uyuni.


# Drawbacks
[drawbacks]: #drawbacks

Why should we **not** do this?

  * obscure corner cases - Users which do not have any qualíty control on their provisioning tools, importing from malicious playbooks / states from a public git repository
  * will it impact performance? No, it will accelerate the adoption from Uyuni for users with and existent provisioning structure
  * what other parts of the product will be affected? Salt-Master
  * will the solution be hard to maintain in the future? No, it would not. It should be delivered as a module that anytime could be activated. If the customer does not have nothing in a git repository he will not activate this feature. It also not be possible to activate without git(github, gitlab....),git_repo, branch and auth_details. Public repositories on github will not be accepted as a security measure(to avoid malicious formulas / playbooks into Uyuni and the linux infrastructure).
      If a public repository will be accepted, it should appear a warning about it.

# Alternatives
[alternatives]: #alternatives

- What other designs/options have been considered? No.
- What is the impact of not doing this? In a modern approach on almost every playbook / salt state is in a git repository and the automation is needed to manage tons of linux clients

# Unresolved questions
[unresolved]: #unresolved-questions

- What are the unknowns?
- What can happen if Murphy's law holds true? Deactivate the module and fix it. 
