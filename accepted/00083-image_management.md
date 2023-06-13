- Feature Name: image_management
- Start Date: 2021-08-26

# Summary
[summary]: #summary

Improve Image Management in SUMA

# Motivation
[motivation]: #motivation

Current Image management is broken and incomplete. The image files are not
referenced in the database so it is difficult to manage them.

For consistent handling of images, these features are needed:
- create / delete
- import / export
- consistent versioning

This RFC proposes changes mainly for OS images, however Docker images share
the code so they are affected too.

## Current state

This section describes details of current implementation with it's problems.

### Image versioning

In Kiwi, the image name and version is part of the source xml file. It can be
affected by Kiwi options (--profile) so it can't be reliably queried before
building.

SUMA stores the built images in `suseImageInfo table`. It currently ignores
the Kiwi name and uses SUMA profile name and `latest` version.

`revision` field is a number that increases each time given `name-version`
is built. It is not used in pillars.

### `build_id`

This is a string generated from Build Action Id  and is unique in each build. It is used
as build directory on Build Host and also appended to image and pillar file names on SUMA,
to prevent conflicts.

### Image Pillars

Image pillars provide information about built PXE images to branch servers
and terminals. They are generated for the end of Inspect action.
Pillars are organized by the Kiwi name and version.
When the same image version is built multiple times, it generates
multiple pillar files (different `build_id`). It is assumed that the result
of pillar merging is the newest build, but this can be buggy.
The names of pillar files are not stored in the database, so they are
never deleted.

`/srv/susemanager/pillar_data/images/org1/image-POS_Image_Graphical7.x86_64-7.0.0-build33.sls`
```

images:
    POS_Image_Graphical7:
        7.0.0:
            arch: x86_64
            basename: POS_Image_Graphical7.x86_64-7.0.0
            boot_image: POS_Image_Graphical7-7.0.0
    ...
            sync:
    ...
                bundle_url: https://server.tf.local/os-images/1//POS_Image_Graphical7.x86_64-7.0.0-build33.tar.xz

```

### Image files

Built Kiwi images are downloaded from Build host to SUMA server and moved to the public http
directory.
The file names are referenced in pillars (bundle_url) in the case of PXE images, they
are not stored in the database so they are never deleted.

### Delta images

Delta images are created by `retail_create_delta` tool. It gets source and target
image as a parameter and creates delta file and pillar. Delta file is stored
along with image files. Pillar is stored along with image pillars. Deltas are not
referenced in SUMA database, so they are invisible in UI or API.

### The update workflow

The current workflow assumes that the customer increases the image version
in Kiwi sources each time the image is build with new updates. This is
rather impractical, because this would be the only change in sources.
Package updates are handled in SUMA Channels.

### Build log files

In case of failed image build, the log files are left on the build host.
For successful builds the logs are deleted.
There is also Kiwi stdout availableas part of Salt result from build action,
but the formatting is lost so it is unreadable.


### Docker images

Built Docker images are uploaded to configured docker registry. Registry identifies
the image by name and version. When a Docker image is rebuilt in SUMA, it re-uses
the existing entry in suseImageInfo table and updates revision number.

For the older docker image revisions it stores repository digests
(suseImageHistory and suseImageRepoDigest tables).
This allows to identify older revisions which are still in use.

This implementation has the following problems:

- The results can be inconsistent if the building of the new revision fails - the info about the
last successfully built image is lost.

- Package lists and other information about older revisions are not stored.


# Detailed design
[design]: #detailed-design


## Proposed changes

1. Use the Kiwi name and version instead of profile name in `suseImageInfo`
   The Kiwi name is determined later in the build workflow, see Image building workflow
   below.
   During the build, a temporary name will be used. The final name will be set
   at the end of build action.
   If the build action fails, the temporary name stays.

2. `revision` will be incremented each time an image with the same
   name and version is built.
   The image will be identified by `name-version-revision` as in
   Build Service.
   Add the revision to image pillar and adjust saltboot and image-sync formulas
   to handle it.
   The actual image file will be created before `revision`,
   so the file name will still contain the build_id in order to make it unique.
   For details see the Image building workflow below.


```

images:
    POS_Image_Graphical7:  # <name>
        7.0.0-1:           # <version>-<revision>
            arch: x86_64
            basename: POS_Image_Graphical7.x86_64-7.0.0
            boot_image: POS_Image_Graphical7-7.0.0
    ...
            sync:
    ...
                bundle_url: https://server.tf.local/os-images/1//POS_Image_Graphical7.x86_64-7.0.0-build33.tar.xz

```


3. Do not re-use `suseImageInfo` entries, create new entry for each build.

   Add yes_no column `obsolete` to `suseImageInfo`.

   Drop table `suseImageBuildHistory`.

   Change foreign key of `suseImageRepoDigest` table from `suseImageBuildHistory.id` to `suseImageInfo.id`.

   For Docker the store can hold only one `name-version` image. Pushing new revision
   to the store replaces the old one. So the old `suseImageInfo` entries can be set to `obsolete` when the
   new image is built successfully.
   On failed build the store still contains the previous revision and the corresponding entry
   in `suseImageInfo` stays unchanged.

   For details see the Image building workflow below.

   For Kiwi it is possible to have multiple revisions of the same `name-version`. So the entries
   can be deleted individually. Typically an old image can be deleted when the new image is
   synced to all Branch servers.

   To maintain previous functionality, add functions to 'delete all revisions'
   and 'delete all obsolete revisions' of an image.

   `suseImageBuildHistory` will need special attention during migration - it will be necessary
   to create new row in `suseImageInfo` for each row from `suseImageBuildHistory`

4. Add `pillar_id` to `suseImageInfo`.

   Add table `suseImageFile` with columns
   - `id`
   - `image_id`
   - `file`
   - `type`
   - `external`

   `pillar_id` points to pillar ID in `suseSaltPillar` table.

   Note: According to the RFC https://github.com/uyuni-project/uyuni-rfc/blob/master/accepted/00080-jsonb-pillar-db-storage.md
   there is a constraint `UNIQUE (org_id, category)` in `suseSaltPillar`.
   The `category` for image pillars will be set to `"image_" + suseImageInfo.id`

   `suseImageFiles` contains file or files related to an image.
   At the beginning there will be only one file of type `bundle`
   allowed. Later we can extend it to support multiple files per image
   with types `kernel`, `initrd`, etc.

   `file` is a local path for images in SUMA Store or URL for
   external images (determined by `external` flag).

   Pillars and local image files will be deleted when the image is deleted
   in UI or API.

   `file` will be used to show image URL in UI.

   Pillar entries will be deleted when the corresponding `suseImageInfo` entry is deleted.
   This will be implemented with an sql trigger.

5. Add `suseDeltaImageInfo` table with columns
   - `sourceImageID`
   - `targetImageID`
   - `pillar_id`
   - `file`

   Add API to create/delete entries, use it in `retail_create_delta`.

   Display deltas in Image details UI.

   Deleting source or target image would delete also the delta image.

   Delta file is a single file that contains all information to create
   target image from source image on Branch server. Currently it is
   supported only for Bundle images. It the future it can be extended
   to support kernel-initrd-system and other image types. In such case
   the file format is to be decided.

6. Store build logs in the database

   - add `log` TEXT column to `suseImageInfo` table
   - collect the logs at the end of build action, use Salt `cp.push` module
   - add UI to display it


7. External stores

   Make sure that API allows moving the image from SUMA to external store,
   with adjusting pillars etc.

   Implement a tool that moves the image from SUMA to external server or CDN.

8. API

   Add the new fields to Image.listImages and Image.getDetails.

   Add methods to get/set image pillars.

   Add a method to change `file` in SUMA store to external url.

   Add a method to upload image file to SUMA store.

   Add a method to import Kiwi image, all the needed info will be passed
   as parameters, image file must be uploaded in advance
   or it can be an URL to external store.

   Rename Image.importImage to Image.importDockerImage
   (with proper deprecating of the old function).

8. Pillars for non-PXE images (optional)

   It will be possible to add pillars for any image via API.
   We could add a flag to image profile to control pillar generation
   during build.

9. Pillar editor (optional)

   Add UI to edit image pillars.


## Image building workflow:

1. Start building
   - create new `suseImageInfo` entry
   - for Kiwi: use temporary values for `name`, `version`, `revision`
   - for Docker: set `name`, `version` according to profile, generate revision
   - schedule build action

2. After build
   - for Kiwi: update `name` and `version`, generate unique `revision`
   - download Kiwi image, set `file`
   - collect logs
   - schedule inspect

3. After inspect
   - generate pillar
   - collect package list
   - for Docker collect repo digests
   - for Docker mark the old `suseImageInfo` entries as `obsolete`

## Database schema

This is an overview of the updated DB tables with all changes included.

```
CREATE TABLE suseImageInfo
(
    id             NUMERIC NOT NULL
                     CONSTRAINT suse_imginfo_imgid_pk PRIMARY KEY,
    name           VARCHAR(128) NOT NULL,
    version        VARCHAR(128),
    image_type     VARCHAR(32) NOT NULL,
    checksum_id    NUMERIC
                     CONSTRAINT suse_imginfo_chsum_fk
                       REFERENCES rhnChecksum (id),
    image_arch_id  NUMERIC NOT NULL
                       CONSTRAINT suse_imginfo_said_fk
                           REFERENCES rhnServerArch (id),
    curr_revision_num   NUMERIC,
    org_id         NUMERIC NOT NULL
                     CONSTRAINT suse_imginfo_oid_fk
                       REFERENCES web_customer (id)
                       ON DELETE CASCADE,
    build_action_id     NUMERIC,
    inspect_action_id   NUMERIC,
    profile_id     NUMERIC
                     CONSTRAINT suse_imginfo_pid_fk
                       REFERENCES suseImageProfile (profile_id)
                       ON DELETE SET NULL,
    store_id       NUMERIC
                      CONSTRAINT suse_imginfo_sid_fk
                         REFERENCES suseImageStore (id)
                         ON DELETE SET NULL,
    build_server_id  NUMERIC
                      CONSTRAINT suse_imginfo_bsid_fk
                         REFERENCES suseMinionInfo (server_id)
                         ON DELETE SET NULL,
    external_image CHAR(1) DEFAULT ('N') NOT NULL,

    obsolete       CHAR(1) DEFAULT ('N') NOT NULL,

    pillar_id      NUMERIC
                     CONSTRAINT suse_imginfo_pillar_fk
                       REFERENCES suseSaltPillar (id)
                       ON DELETE SET NULL,
    log            TEXT,

    created        TIMESTAMPTZ
                     DEFAULT (current_timestamp) NOT NULL,
    modified       TIMESTAMPTZ
                     DEFAULT (current_timestamp) NOT NULL,
    CONSTRAINT suse_imginfo_bldaid_fk FOREIGN KEY (build_action_id)
        REFERENCES rhnAction (id) ON DELETE SET NULL,
    CONSTRAINT suse_imginfo_insaid_fk FOREIGN KEY (inspect_action_id)
        REFERENCES rhnAction (id) ON DELETE SET NULL
);

CREATE SEQUENCE suse_imginfo_imgid_seq;

CREATE TABLE suseImageRepoDigest
(
    id             NUMERIC NOT NULL
                     CONSTRAINT suse_rdigest_id_pk PRIMARY KEY,
    image_info_id    NUMERIC NOT NULL,
    repo_digest    VARCHAR(255) NOT NULL,
    created        TIMESTAMPTZ
                     DEFAULT (current_timestamp) NOT NULL,
    modified       TIMESTAMPTZ
                     DEFAULT (current_timestamp) NOT NULL,
    CONSTRAINT suse_rdigest_imginfo_fk FOREIGN KEY (image_info_id)
        REFERENCES suseImageInfo (id) ON DELETE CASCADE
);

CREATE SEQUENCE suse_img_repodigest_id_seq;

CREATE TABLE suseImageFile
(
    id             NUMERIC NOT NULL
                     CONSTRAINT suse_imgfile_fileid_pk PRIMARY KEY,
    image_info_id  NUMERIC NOT NULL,
    file           TEXT NOT NULL,
    type           VARCHAR(16) NOT NULL,
    external       CHAR(1) DEFAULT ('N') NOT NULL,
    created        TIMESTAMPTZ
                     DEFAULT (current_timestamp) NOT NULL,
    modified       TIMESTAMPTZ
                     DEFAULT (current_timestamp) NOT NULL,

    CONSTRAINT suse_imgfile_imginfo_fk FOREIGN KEY (image_info_id)
        REFERENCES suseImageInfo (id) ON DELETE CASCADE
);

CREATE SEQUENCE suse_img_file_id_seq;

CREATE TABLE suseDeltaImageInfo
(
    source_image_id NUMERIC NOT NULL
                     CONSTRAINT suse_deltaimg_source_fk
                     REFERENCES suseImageInfo (id) ON DELETE CASCADE,

    target_image_id NUMERIC NOT NULL
                     CONSTRAINT suse_deltaimg_target_fk
                     REFERENCES suseImageInfo (id) ON DELETE CASCADE,

    pillar_id       NUMERIC
                     CONSTRAINT suse_deltaimg_pillar_fk
                       REFERENCES suseSaltPillar (id)
                       ON DELETE SET NULL,

    file           TEXT NOT NULL,

    created        TIMESTAMPTZ
                     DEFAULT (current_timestamp) NOT NULL,
    modified       TIMESTAMPTZ
                     DEFAULT (current_timestamp) NOT NULL,

    CONSTRAINT suse_deltaimg_pk PRIMARY KEY (source_image_id, target_image_id)
);


```

# Drawbacks
[drawbacks]: #drawbacks

No known drawbacks.

# Alternatives
[alternatives]: #alternatives

### External stores

- Implement external image stores in java to fit particular CDN API

- Implement generic support in java, the actions needed for particular
  store will be handled by customizable salt states.

# Unresolved questions
[unresolved]: #unresolved-questions

- Which CDN's should we target?


