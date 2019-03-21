- Feature Name: SUSE Manager integration best practices
- Start Date: 2017-09-21
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This is a list of best practices for integration among SUSE products.

# Motivation
[motivation]: #motivation

This is needed in order to serve as a guide for other teams when it comes to integration among products, such as SES, CaaSP, SUSE Manager etc.

## General integration principles

All products for Salt Master are _equal_ under Salt "umbrella". That means, SUSE Manager or SES or CaaSP or anything else does not have a priority over another in the view of Salt Master. The reason is that every product is using its own isolated environment, and shares the information with the other products through the common ways of doing it (e.g. grains), having no priority over any other product.

### Communication between products

#### Salt Event Bus

The main communication channel would be the Salt Event Bus.
The products would listen for events on the bus and, if needed, they would post their own events there.
In order to react on events, reactors would be used (simple reactors or Thorium)

#### Grains

Another way of sharing data could be using grains.

### Salt Environments

Each porducts must provide its own configuration file in `/etc/salt/master.d`.
Read more in [Salt Configuration](#salt-configuration) section.

Each product must store its salt related files in its own folders and configure accordingly in the salt configuration file mentioned above.
Read topic specific the details in the following sections:

 - [File roots](#file-roots)
 - [Pillar roots](#pillar-roots)
 - [External pillar modules](#external-pillar-modules)
 - [Custom modules](#custom-modules)
 - [State files](#state-files)
 - [Custom state modules](#custom-state-modules)

## Salt configuration

Each products would have to deploy their own product specific salt configuration file in `/etc/salt/master.d`.
This custom configuration files should only be used for setting products specific parameters.
For example, SUSE Manager keeps the configuration in `/etc/salt/master.d/susemanager.conf`.
The common configuration parameters would be kept in `/etc/salt/master` or a special file in /etc/salt/master.d (eg `/etc/salt/master.d/common.conf`)

Products specific configuration parameters:
 - file_roots
 - pillar_roots
 - runner_dirs :x: [needs fix](#unresolved-questions)<br/>
 - reactor

#### File roots

Each product would add its own file_roots in its own configuration file.
They must not use `base` but something unique to them. This should be seen as a namespace.

SUSE Manager has the following file_roots at the time being:
- /usr/share/susemanager/salt
- /usr/share/susemanager/formulas/states
- /srv/susemanager/salt
- /srv/salt

#### Pillar roots

Each product would configure its own pillar_roots in the product specific configuration file.
The product specific pillar_roots should not use 'base', but a product specific salt environment.
Pillar can work with the multiple top files. However, the requirement is to select the environment, unless it is 'base'.
In order to add another product name "MyProduct" to integrate with:

1. Add its pillar root, e.g. `/srv/my_product/pillar`
> /etc/salt/master.d/myproduct.conf
```yaml
pillar_roots:
  myproduct_env:
    - /srv/my_product/pillar
```

2. Add a `top.sls` file there `/srv/my_product/pillar/top.sls` and make sure it is targeting specific environment, e.g. `myproduct_env`
> /srv/my_product/pillar/top.sls
```yaml
myproduct_env:
  '*':
    - my_pillar
```

3. Add pillar data in /srv/my_product/pillar/my_pillar.sls

#### External pillar modules

Products should add the external pillar modules in a `_pillar` subfolder in one of their `file_roots`.
The external pillar modules need to be enabled like this
    
```yaml
ext_pillar:
  - suma_minion: True
```

#### Custom modules

Custom modules would be dropped in one of the product specific file_roots.
Custom modules names need to be unique because salt environments for custom modules doesn't work.
Follow the steps to add custom modules:

1. Add the module in one of the file_roots defined in your product's configuration file. The module name should be unique (use a prefix e.g.: myprefix_mymodule.py)
2. Run `salt "<your minions expression>" saltutil.sync_modules`
3. Run the module using `salt "<your minions expression>" myprefix_mymodule.myfunction`

#### State files

State files should be dropped in one of the file_roots defined in your product specific configuration file.

> :question: [open question](#unresolved-questions)<br/>
We have to decide what top file strategy we addopt.

See [Top file merging strategy](https://docs.saltstack.com/en/latest/ref/configuration/minion.html#top-file-merging-strategy).

#### Custom State modules

Custom state modules should be dropped in one of the file_roots defined in your product specific configuration file.
In order to add your product specific state modules, follow these steps:

1. Create a subfolder `_states` in the one of the file_roots of your product. (eg /srv/salt/myproducts/_states)
2. Put your state module in the `_states` subfolder (eg /srv/salt/myproducts/_states/mystates.py)
3. Use your custom state module in an state file (eg /srv/salt/myproduct/mystate.sls)
4. Run `salt "<your minions>" saltutil.sync_all saltenv=myproduct`
5. To apply the states run: `salt "<your minions>" state.apply mystate saltenv=myproduct`

#### Custom runners

The paths to custom runners are set with `runner_dirs`.
Each product should define its runners in it's own `runner_dirs`.
SUSE Manager keeps the runners in `/usr/share/susemanager/modules/runners`

> :x: [needs fix](#unresolved-questions)<br/>
multiple `runner_dirs` in different configuration files does not work because `runner_dirs` from different configuration files are not merged.

#### Grains modules

The best way to set grain is to set them in each product own custom state files.

In order to add custom grains modules, follow the steps:
1. Create a `_grains` subfolder in one of your product`s `file_roots` (eg /srv/salt/myproducts/_grains)
2. Put your grains module in the `_grains` subfolder (eg /srv/salt/myproducts/_grains/mygrains.py)
3. Run `salt "<your minions>" saltutil.sync_all saltenv=myproduct`
4. To see the grains run: `salt "<your minions>" grains.items`

> SUSE Manager keeps its custom grains modules in `/usr/share/susemanager/salt/_grains/`
> In SUSE Manager you can manually set a grain to a specified activation key, then it will be read by the server.

#### Master tops

> :question: [open question](#unresolved-questions)<br/>
When are multiple master tops useful?

  - SUSE Manager allows multiple master top modules and merges them together.
    - Example: [SUSE Manager top module](https://github.com/SUSE/spacewalk/blob/Manager-3.1/susemanager-utils/susemanager-sls/modules/tops/mgr_master_tops.py)

  - In order to add a top file for your product:

    1. Create a `_tops` subfolder in one of your `file_roots`
    2. Write your top module and put it in `_tops` created at 1. [see customtop.py](https://docs.saltstack.com/en/latest/topics/master_tops/)
    3. Add it in your products specific configuration file (eg `/etc/salt/master.d/myproduct.conf`)

    ```yaml
    master_tops:
      mgr_master_tops: True
      customtop: True
    ```

    4. Restart salt-master: systemctl restart salt-master
    5. sync master tops: salt-run saltutil.sync_tops
    6. Show tops: salt \* state.show_top

#### Reactors

State files can be executed when an event is received.
Different products would register their state files with the events they are interested in like this:

reactor:
  - 'salt/job/*/ret/mdminsles12sp1.tf.local':
    - salt://react.sls?saltenv=ses  # specifying the saltenv works
    - salt://react.sls

Examples for reactor sls files can be found here: https://docs.saltstack.com/en/latest/topics/reactor/index.html

> :x: [needs fix](#unresolved-questions)<br/>
Idealy, each product would define the reactors in its own configuration file in `/etc/salt/master.d` but these are not merged. 

> :x: [needs fix](#unresolved-questions)<br/>
Unfortunatelly, mapping multiple reactors to same event pattern doesn't work, only the first one is picked.


#### Salt API

All the products should use salt-api to interact with salt.
In SUSE Manager environment, salt-api has the following characteristics:

  - Uses salt.auth.auto (no authentication)
  - Runs on 127.0.0.1:9080 (only be accessible from whithin the SUSE Manager machine)

> :question: [open question](#unresolved-questions)<br/>
Describe full API desired configuration.


#### Extra required configuration parameters

```yaml
worker_threads: 8  # minimum
timeout: 120
gather_job_timeout: 120
thin_extra_mods: certifi
rosters:
  - /srv/susemanager/tmp
file_recv: True
```

### Onboarding Minions
  - the repositories of the minion will be set on onboarding according to the activation key in SUSE Manager or according to detected products as long as they are available on the server

# Drawbacks
[drawbacks]: #drawbacks

This requires changing SUSE Manager salt integration.

# Alternatives
[alternatives]: #alternatives

Keeping SUSE Manager as is (owner of salt) and treat the other products as products that need to be integrated.
This could lead to undesired behaviour caused by the poor isolation between SUSE Manager and the other products.

Another option would be to have a separate salt-master for each product.

# Unresolved questions
[unresolved]: #unresolved-questions
- What is the preferred way to share information between products?
- RFC ['00005-salt-state-tree']('https://github.com/SUSE/susemanager-rfc/blob/master/text/00005-salt-state-tree.md') needs to be adapted not to use 'base' in file_roots
- Enable authentication for Salt API (CAASP team is already using PAM)
- Fix the `runner_dirs` merging bug to allow defining runner directories in multiple configuration filet (eg: each product would define its own)
- Allow merging the reactors
- Fix mapping multiple reactors to the same event pattern
- Establish full list of Salt product specific configuration parameters, parameters not present in this list should not be defined in the products specific config file
- Implement custom modules environments (see custom states)
- suma_minion.py should be moved to /usr/share/susemanager/salt/_pillar/ otherwise it will be removed by `salt-run saltutil.sync_pillar`
- Fix/implement reactors with salt environments
- Decide the state file merging. See [Top file merging strategy](https://docs.saltstack.com/en/latest/ref/configuration/minion.html#top-file-merging-strategy).
- Describe the desired API configuration for [Salt API](#salt-api)
- Describe when multiple master tops are useful
