- Feature Name: New Channel Auth
- Start Date: 2015-10-22
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

This RFC describes a simple way to give 3rd parties access to the repositories (or any other content available via HTTP).

This can be used for:

* Implementing repository access without a RHN stack (eg. Salt)
* Using SUSE Manager as a generic repository server
* The ability to serve content statically

# Motivation
[motivation]: #motivation

Right now SUSE Manager repositories are protected by a complicated not-invented-here mechanism that relies on the rhn client stack. (See the [wiki page](https://github.com/SUSE/spacewalk/wiki/How-Client-Authentication-works) for more information).

This requires login via the XML-RPC API (exposed in the python API) and then add the returned headers to every request. The headers are basically claims plus another header that signs the claims.

Using headers is problematic because you need to modify clients in order to pass them. That is the reason zypper needs zypp-plugin-spacewalk.

This proposal would have the following outcome:

* Any client would be able to get repository data by having only:
  * The url of the server
  * The name of the channel/repo
  * A valid token
* The client would need only to build a url from this components.
* An API can be user to generate tokens
* A web-page can be added to create tokens
* Tokens can have grained authentication (claims) and expiration
* Packages can be served statically

# Detailed design
[design]: #detailed-design

## Inspiration

* The design is inspired partially on how SCC works right now.
* If you have a channel sles-12-x86_64 and a token abcdefghi then you can access the repository at http://server.example.com/rhn/channels/sles-12-x86_64?abcdefghi

## Token generation

* For the token, we will use [JWT](http://jwt.io/) ([RFC](https://tools.ietf.org/html/rfc7519)).

* The server will generate a JWT token as described in [the website](http://jwt.io/) using *server.secret_key* in /etc/rhn/rhn.conf as the secret used to derive the key.
* The payload include the following claims:
  * `org` claim gives access to all channels for that organization id
  * `onlyChannels` restrict the access to the listed channels in the organization
  * a token can just specify the org, or the org plus the channel whitelist
  * expiration date of the token

The generation of tokens could be done:

* Programatically from Java code (eg, for the channel management to inject into URLs)
* From an API (XML-RPC)
* From a webpage

# Tracking and Refreshing

All tokens (except for temporary ones created with the listChannels xmlrpc call)
are tracked there until they expire. This gives us the potential in the future
to blacklist tokens before they expire even if they are not linked to a
particular minion anymore.

This information includes:

 - the token
 - channels accessible with the token
 - the minion that is currently using this token
 - the expiration date of the token

## Token Lifecycle

- A new token get created and linked to a minion whenever the minion needs a
  token for a channel and there is no token for this channel linked to the
minion yet. (previously unlinked tokens will not be reused for security
reasons.)
- When tokens are close to expiring they will be unlinked from the minion and a
  fresh token will be generated.
- When tokens are expired they will be cleaned up from the database.
- When a token linked to a minion gives access to more channels then the minion
  needs it will be unlinked and a new token with only the needed channels will
be created.

Implementation note: The current implementation can handle tokens with multiple
channels but will create only tokens with one channel in it. This is to work
around tokens with a lot of channels getting to long for the database to store.

## Token validation (dynamic)

Currently, auth is performed in the [apacheAuth.py controller](https://github.com/SUSE/spacewalk/blob/Manager/backend/server/apacheAuth.py).

The auth function would need to be enhanced, however the amount of legacy code here is remarkable.

So the proposal is to create a new endpoint on the Java side.

Very similar to the old endpoint:
* http://suma.com/XMLRPC/GET-REQ/$channel/$file

For example:
* http://suma.com/rhn/manager/download/$channel/$file?token

The endpoint will use the [jose4j](https://bitbucket.org/b_c/jose4j) library to:

* validate the token against the server.key secret
* retrieve the payload and:
  * check the expiration date
  * If `onlyChannels` is specified, check the channel is included in the whitelist

And then:

* Look in the database for the filename and resolve the hashed directory path
* Return the file

## Token validation (static)

The main reason serving statically is difficult, is that the pckages are deduplicated and the relationship between channels, packages and orgs need to be resolved in order to verify the token.

Packages are right now in `MOUNT_POINT/packages/$org/$checksum_prefix/$name/$version/$arch/$checksum/$file`.

The proposal is to add a second directory under MOUNT_POINT (/var/spacewalk) called `channels` and modify RpmRepositoryWriter.java to link the packages at repodata generation time (see Appendix).

When repodata is generated `MOUNT_POINT/channels/$org/$channel/getPackage/$file` is symlinked to the file in `MOUNT_POINT/packages/$org/$checksum_prefix/$name/$version/$arch/$checksum/$file`.

`MOUNT_POINT/channels` can now be served statically and it is compatible with the existing repodata.

> Apache has to be configured to serve from `/var/spacewalk/channels` with the `FollowSymLinks` option.

Because it contains the full path including the org and channel, it can be authenticathed using a helper program that compares the url accessed with the claims in the token and validates the token:

We will call this standalone program `tokenchecker` hereinafter. Such program can be written in Java with [jose4j](https://bitbucket.org/b_c/jose4j) or in Python with [pyjwt](https://github.com/jpadilla/pyjwt).

That can be accomplished by using `mod_rewrite`, which can be configured to use `tokenchecker` with rules similar to the following:

```
# define an external rewriting program named tokenchecker
RewriteMap tokenchecker "prg:/usr/bin/tokenchecker"

# route requests from the new endpoint to the tokenchecker
RewriteRule ^/rhn/manager/download/.*?/packages/.*$ "${tokenchecker:%{REQUEST_URI}?%{QUERY_STRING}}"

# disallow direct access to /packages/path/file.rpm
RewriteCond %{QUERY_STRING} !^tokencheck=passed$
RewriteRule ^/packages - [F,L]
```

The url can then be mapped to a path into /var/spacewalk/channels without the need of database access, as the org and channel content is already resolved at metadata generation time. The channel only contains symlink to the packages it contains, so if the token checker gave access to one channel, only those packages can be accessed.

> The subdirectory getPackage is not needed is the url rewrite takes care of mapping it correctly.

## Limitations

* If hardlinks are used, only 64k channels can point to the same file
* Number of symlinks in the same directory [should not be a problem](http://stackoverflow.com/questions/466521/how-many-files-can-i-put-in-a-directory)

# Drawbacks
[drawbacks]: #drawbacks

* Generation of symlinks adds some overhead at repodata generation time but can make serving completely static

# Alternatives
[alternatives]: #alternatives


# Unresolved questions
[unresolved]: #unresolved-questions


# Current Implementation Notes
[impl]: #impl
* Repository end-point at /rhn/manager/download/$channellabel?$token

This means any system could access a SUSE Manager channel (eg. a cloned channel) even without being registered to SUSE Manager.

```
zypper ar https://mysusemanager.server.com/rhn/manager/download/sles-12-x86_64-clone?25ac09acf1697c70f sles-12-x86_64-clone
```

* org and channel claims are checked (in addition to the jwt validity)

# Appendix

## RpmMetadataWriter patch to symlink packages

```diff
diff --git a/java/buildconf/manager-test-includes b/java/buildconf/manager-test-includes
index 371cbfb..90f5694 100644
--- a/java/buildconf/manager-test-includes
+++ b/java/buildconf/manager-test-includes
@@ -1 +1,2 @@
-**/test/*Test.class
+#**/test/*TokenUtilsTest.class
+**/com/suse/manager/webui/controllers/test/*Test.class
diff --git a/java/code/src/com/redhat/rhn/taskomatic/task/repomd/RpmRepositoryWriter.java b/java/code/src/com/redhat/rhn/taskomatic/task/repomd/RpmRepositoryWriter.java
index 56799c3..4935f13 100644
--- a/java/code/src/com/redhat/rhn/taskomatic/task/repomd/RpmRepositoryWriter.java
+++ b/java/code/src/com/redhat/rhn/taskomatic/task/repomd/RpmRepositoryWriter.java
@@ -26,6 +26,7 @@ import com.redhat.rhn.frontend.dto.PackageDto;
 import com.redhat.rhn.manager.channel.ChannelManager;
 import com.redhat.rhn.manager.rhnpackage.PackageManager;
 import com.redhat.rhn.manager.task.TaskManager;
+import org.apache.commons.io.FileUtils;
 
 import java.io.BufferedWriter;
 import java.io.File;
@@ -35,6 +36,9 @@ import java.io.FileOutputStream;
 import java.io.FileWriter;
 import java.io.IOException;
 import java.io.OutputStreamWriter;
+import java.nio.file.Files;
+import java.nio.file.Path;
+import java.nio.file.Paths;
 import java.security.DigestInputStream;
 import java.security.DigestOutputStream;
 import java.security.MessageDigest;
@@ -108,6 +112,20 @@ public class RpmRepositoryWriter extends RepositoryWriter {
         String prefix = mountPoint + File.separator + pathPrefix +
                 File.separator + channel.getLabel() + File.separator;
 
+        // prepare the directory where we will symlink the rpms
+        Path repoPrefixPath = Paths.get(
+                Config.get().getString(ConfigDefaults.MOUNT_POINT),
+                "channels", channel.getOrg().getId().toString(),
+                channel.getLabel());
+        try {
+            FileUtils.deleteDirectory(repoPrefixPath.toFile());
+            repoPrefixPath.toFile().mkdirs();
+        }
+        catch (IOException e) {
+            throw new RepomdRuntimeException("Unable to remove directory: " +
+                    repoPrefixPath);
+        }
+
         // we closed the session, so we need to reload the object
         channel = (Channel) HibernateFactory.getSession().get(channel.getClass(),
                 channel.getId());
@@ -215,6 +233,8 @@ public class RpmRepositoryWriter extends RepositoryWriter {
                     filelistsFile.flush();
                     otherFile.flush();
                     susedataFile.flush();
+
+                    linkPackageToChannel(repoPrefixPath, channel, pkgDto);
                 }
                 catch (IOException e) {
                     throw new RepomdRuntimeException(e);
@@ -306,6 +326,29 @@ public class RpmRepositoryWriter extends RepositoryWriter {
     }
 
     /**
+     * Links the package in a per channel directory that can be used as a static
+     * server for package with the same metadata
+     */
+    private void linkPackageToChannel(Path repoPrefix, Channel channel, PackageDto pkgDto) {
+        Path link = Paths.get(repoPrefix.toAbsolutePath().toString(),
+                "getPackage", pkgDto.getFile());
+        Path target = Paths.get(Config.get().getString(ConfigDefaults.MOUNT_POINT),
+                pkgDto.getPath());
+        try {
+            log.info(String.format("link package %s to %s",
+                    link.toString(), target.toString()));
+            link.getParent().toFile().mkdirs();
+            Files.createSymbolicLink(link, target);
+        }
+        catch (IOException e) {
+            throw new RepomdRuntimeException(
+                    String.format("Can't link package %s to %s",
+                            link.toString(), target.toString())
+            );
+        }
+    }
+
+    /**
      * Deletes existing repo and generates file stating that no repo was generated
      * @param channel the channel to do this for
      * @param prefix the directory prefix
      * 
```

## Skeleton implementation of `tokenchecker`

```java
public class TokenChecker {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

        Pattern p = Pattern.compile("/rhn/manager/(.*?)/(.*?)/getPackage/(.*?)\\?path=(.*)?(.*)");
        while (true) {
            String output;

            try {
                String input = sc.nextLine();
                Matcher m = p.matcher(input);
                m.matches();

                String org = m.group(1);
                String channel = m.group(2);
                String path = URLEncoder.decode(m.group(4));
                String token = m.group(5);
                output = path + "?tokencheck=passed";

                //validateToken(token, org, channel, path);
            }
            catch (IllegalStateException | TokenValidationException) {
                output = "NULL";
            }

            System.out.println(output);
            System.out.flush();
        }
    }
}
```

