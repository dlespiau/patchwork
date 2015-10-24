User Manual
===========

Submitting patches
------------------

Initial Submission
~~~~~~~~~~~~~~~~~~

Patches are normally submitted with :command:`git send-email` to a mailing
list. For instance, if we branched from ``master``, have three patches to
submit, we can use:

::

    $ git send-email --to=<mailing-list> --cover-letter --annotate master

This command will produce the following email thread (providing you have
the ``chainreplyto`` configuration option set to ``false``):

::

    + [PATCH 0/3] Cover Letter Subject
    +--> [PATCH 1/3] Patch 1
    +--> [PATCH 2/3] Patch 2
    +--> [PATCH 3/3] Patch 3

Patchwork receives those mails and construct Series and Patches objects
to present a high level view of the mailing-list activity and a way to
track what happens to that submission.

It's a good idea to include a cover letter to introduce the work.
Patchwork will also pick up that cover letter and name the series with
the subject of that email.

When sending only one patch, it's a bit much to send a cover letter
along with it as the commit message should provide enough context. In
that case, Patchwork will use the subject of the patch as the series
title.

New Versions
~~~~~~~~~~~~

Sometimes, maybe even more often than hoped, one needs to resend a few
patches or even entire series to address review comments.

Patchwork supports:

  - Re-sending a single patch as a reply to the reviewer email. This is
    usually only used when a few patches have to be resent.

  - Re-sending a full series as a new thread.

A Series object in patchwork tracks all the changes on top of the
initial submission.

New Patch
.........

To send a v2 of a patch part of a bigger series, one would do something
similar to:

::

    $ git send-email --to=<mailing-list> --cc=<reviewer> \
                     --in-reply-to=<reviewer-mail-message-id> \
                     --reroll-count 2 -1 HEAD~2

And, continuing the previous example, this would result in the following
email thread:

::

    + [PATCH 0/3] Cover Letter Subject
    +--> [PATCH 1/3] Patch 1
    +--> [PATCH 2/3] Patch 2
    |  +--> Re: [PATCH 2/3] Patch 2               (reviewer comments)
    |     +--> [PATCH v2 2/3] Patch 2             (v2 of patch 2/3)
    +--> [PATCH 3/3] Patch 3

Patch work will create a new *revision* of the series, updating patch
#2 to the new version of that patch.

New Series
..........

When something is really wrong or when, to address the review, most
patches of a series need to be revised, re-sending individual emails can
be both annoying for the patch author but also hard to follow from the
reviewer side. It's then better to re-send a full new thread and forget
the previous one.

Patchwork will get that and create a new revision of the initial series
with all patches updated to the latest and greatest.

::

    + [PATCH 0/3] Cover Letter Subject
    +--> [PATCH 1/3] Patch 1
    +--> [PATCH 2/3] Patch 2
    +--> [PATCH 3/3] Patch 3

    + [PATCH v2 0/3] Cover Letter Subject
    +--> [PATCH v2 1/3] Patch 1                   (v2 of patch 1/3)
    +--> [PATCH v2 2/3] Patch 2                   (v2 of patch 2/3)
    +--> [PATCH v2 3/3] Patch 3                   (v2 of patch 3/3)

Patchwork uses the cover letter subject to detect that intent. So one
doesn't need to use the ``reroll-count`` like above, the following
would work as well:

::

    + [PATCH 0/3] Cover Letter Subject
    +--> [PATCH 1/3] Patch 1
    +--> [PATCH 2/3] Patch 2
    +--> [PATCH 3/3] Patch 3

    + [PATCH 0/3] Cover Letter Subject (v2)
    +--> [PATCH 1/3] Patch 1                     (v2 of patch 1/3)
    +--> [PATCH 2/3] Patch 2                     (v2 of patch 2/3)
    +--> [PATCH 3/3] Patch 3                     (v2 of patch 3/3)

Of course, we've now entered a dangerous territory. Trying to parse some
human-generated text. The regular expression used accepts several ways
of saying that the series is a new version of a previous one. If your
favourite way isn't among what's supported, consider contributing (like
filing an issue)!

Considering an initial series with ``Awesome feature`` as the cover
letter subject, Patchwork will considering series with the following
cover letter subjects as new revisions:

  +---------------------------------+----------------------------+
  |       Regular Expression        |        Cover Letter        |
  +---------------------------------+----------------------------+
  |                                 | - Awesome feature          |
  |                                 | - awesome feature          |
  +---------------------------------+----------------------------+
  | ``[, \(]*(v|take)[\) 0-9]+$')`` | - Awesome feature v2       |
  |                                 | - awesome feature V2       |
  |                                 | - Awesome feature, v3      |
  |                                 | - Awesome feature (v4)     |
  |                                 | - Awesome feature (take 5) |
  |                                 | - Awesome feature, take 6  |
  +---------------------------------+----------------------------+
