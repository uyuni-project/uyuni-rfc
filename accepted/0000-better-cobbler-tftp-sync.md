- Feature Name: Better Cobbler TFTP Sync
- Start Date: 2020-11-08
- RFC PR: (leave this empty)

# Summary
[summary]: #summary

More optimized TFTP syncing for Cobbler proxies. Switching from push to pull.

# Motivation
[motivation]: #motivation

For large scale installations Cobbler has proven to be a possible bottleneck. One of the problems is the Cobbler sync that, when using it in conjunction with proxies, also pushes the TFTP folder to the proxies. For installations with just one proxy and around 130 profiles the whole process can easily take up to 15 minutes. Not all of that is due to TFTP sync, but a good chunk of it and might force clients into a reboot, since information are not yet updated.

# Detailed design
[design]: #detailed-design

The solution of pushing the update files to proxies does not scale well. Especially with large installations and many proxies the time needed for a full sync grows linearly.

The idea is to skip this step completely and move the logic to the proxy. In order to do that, we would need a TFTP server that is capable of dynamically checking if requested files are up-to-date on the file system, or if files need to be fetched from Uyuni. Also certain files need to be modified on the fly, since some files include the hostname of the Uyuni server.

```
      +----------------+
      | Client Machine |
      +-------+--------+
              |
            TFTP-
           Request
              |
              v
         +----+------+
         |           |
         |   TFTP    |
         |           |
         +-+-------+-+
           |       |

     Check local disk cache
      for files. Otherwise
     pull from Uyuni server.
           |       |
           |       |
           v       v
+----------+-+   +-+------+
| Local Disk |   | Uyuni  |
| Cache      |   | Server |
+------------+   +--------+
```

The scenario would look like this. Once a client requests a file, the TFTP server would check if this file is in the local disk cache. If it's not, then it's immediately fetched via HTTP from Uyuni Server. If the file is present in the local disk cache, then the TFTP server would send a HEAD request to Uyuni server to get the current etag of the file. If the etags are matching, then the local file can be used. If not, then it needs to be fetched from Uyuni server and put into the local disk cache.
For some files the Uyuni hostname needs to be replaced; this would be done right before delivering it to the client since etags wouldn't match otherwise.

Ideally a proxy would be "warmed up" after a few client requests, since most of the files are then cached on disk. HEAD requests are releatively cheap and reasonably fast. So the first clients would encounter a slight delay, but all of the following requests for profiles with the same kernel and initrd would have nearly the same speed as the current implementation.

Dealing with the thundering herd problem. Since it would be possible to have 300 clients requesting the same not yet synced, or outdated kernel, there needs to be a lock of some sorts on file requests. If there is a request to Uyuni server already running for the same file, there is no additional request allowed. Instead we'd just wait for the initial request to finish.

One possible solution for the TFTP server would be [fbtftp](https://github.com/facebook/fbtftp) from Facebook. They ran into pretty much the same problem and created this dynamic TFTP server framework.


# Drawbacks

* This solution moves load and complexity to the proxy.
* Proxies need to have a permanent connection to the Uyuni server. If that cannot be guaranteed, then this solution won't work.
* Proxies are pulling files instead of getting files pushed and start slow due ot empty cache.

# Alternatives
[alternatives]: #alternatives

- Improve file transfers with rsync via HTTP. But there is no rsync2 Python wrapper. Not yet tested, but would have the same scaling characteristics as the current solution.
- Gzip for requests. Tested and only slighly faster with the same scaling characteristics as the current solution. Could be used in combination with rsync.

# Unresolved questions
[unresolved]: #unresolved-questions

- A note on _etags_. It would be nice to not have a database to track etag checksums of files. We need to check if etags can be calculated and calculated reasonably fast. Otherwise tracking etags in a sqlite database would be needed.

- There are multiple ways to solve the thundering herde problem, but I have not yet looked into a specific solution. A queue might be reasonable solution, but also adds some complexity.