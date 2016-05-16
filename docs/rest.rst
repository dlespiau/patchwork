REST API
========

Patchwork exposes a REST API to allow other systems and scripts to interact
with it. The basic service it offers is exposing a mailing-list used for
sending patches and review comments as high level objects: series, revisions
and patches.

**series**
    A collection of revisions. Series objects are created, along with an
    initial revision, when a set of patches are sent to a mailing-list,
    usually through |git send-email|. Series can evolve over time and gain new
    revisions as the work matures through reviews, testing and new iterations.

    More about series and revisions can be found in :ref:`submitting-patches`.

**revision**
    A collection of patches.

**patch**
    The usual collection of changes expressed as a diff_. With |git|, a patch
    also contains full commit metadata.

API Patterns
------------

All the API entry points share common patterns to offer a coherent whole and
limit surprises when using the API.

Lists
~~~~~

Various entry points expose lists of objects. They all follow the same
structure:

.. code-block:: json

    {
        "count": 25,
        "next": "http://patchwork.example.com/api/1.0/series/?page=2",
        "previous": null,
        "results": [
            {
                "object": 0
            },
            {
                "object": 1
            },
            {
            },
            {
                "object": 19
            },
        ]
    }

Lists are paginated with 20 elements per page by default. ``count`` is the
total number of objects while ``next`` and ``previous`` will hold URLs to the
next and previous pages. It's possible to change the number of elements per
page with the ``perpage`` GET parameter, with a limit of 100 elements per page.

API Reference
-------------

API Metadata
~~~~~~~~~~~~

.. http:get:: /api/1.0/

    Metadata about the API itself.

    .. sourcecode:: http

        GET /api/1.0/ HTTP/1.1
        Accept: application/json


    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: application/json

        {
            "revision": 0
        }

    :>json int revision: API revision. This can be used to ensure the server
                         supports a feature introduced from a specific revision.
                         The list of API revisions and the changes introduced
                         by each of them is documented in `API Revisions`_.


Projects
~~~~~~~~

A project is merely one of the projects defined for this patchwork instance.

.. http:get:: /api/1.0/projects/

    List of all projects.

    .. sourcecode:: http

        GET /api/1.0/projects/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept
        Allow: GET, HEAD, OPTIONS

        {
            "count": 2,
            "next": null,
            "previous": null,
            "results": [
                {
                    "id": 2,
                    "name": "beignet",
                    "linkname": "beignet",
                    "listemail": "beignet@lists.freedesktop.org",
                    "web_url": "http://www.freedesktop.org/wiki/Software/Beignet/",
                    "scm_url": "git://anongit.freedesktop.org/git/beignet",
                    "webscm_url": "http://cgit.freedesktop.org/beignet/"
                },
                {
                    "id": 1,
                    "name": "Cairo",
                    "linkname": "cairo",
                    "listemail": "cairo@cairographics.org",
                    "web_url": "http://www.cairographics.org/",
                    "scm_url": "git://anongit.freedesktop.org/git/cairo",
                    "webscm_url": "http://cgit.freedesktop.org/cairo/"
                }
            ]
        }

.. http:get:: /api/1.0/projects/(string: linkname)/
.. http:get:: /api/1.0/projects/(int: project_id)/

    .. sourcecode:: http

        GET /api/1.0/projects/intel-gfx/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept
        Allow: GET, HEAD, OPTIONS

        {
            "id": 1,
            "name": "intel-gfx",
            "linkname": "intel-gfx",
            "listemail": "intel-gfx@lists.freedesktop.org",
            "web_url": "",
            "scm_url": "",
            "webscm_url": ""
        }

.. _rest-events:

Events
~~~~~~

.. http:get:: /api/1.0/projects/(string: linkname)/events/
.. http:get:: /api/1.0/projects/(int: project_id)/events/

    List of events for this project.

    .. sourcecode:: http

        GET /api/1.0/projects/intel-gfx/events/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept
        Allow: GET, HEAD, OPTIONS

        {
            "count": 23,
            "next": "http://patchwork.example.com/api/1.0/events/?page=2",
            "previous": null,
            "results": [
                {
                    "name": "series-new-revision",
                    "event_time": "2015-10-20T19:49:49.494183",
                    "series": 23,
                    "patch": null,
                    "user": null,
                    "parameters": {
                        "revision": 2
                    }
                },
                {
                },
                {
                    "name": "patch-state-change",
                    "event_time": "2016-02-18T09:30:33.853206",
                    "series": 285,
                    "patch": 685
                    "user": 1,
                    "parameters": {
                        "new_state": "Under Review",
                        "previous_state": "New"
                    }
                }
            ]
        }

    :query since: Retrieve only events newer than a specific time. Format is
                  the same as ``event_time`` in response, an ISO 8601 date. That
                  means that the ``event_time`` from the last seen event can
                  be used in the next query with a ``since`` parameter to only
                  retrieve events that haven't been seen yet.

    :query name: Filter the events by name. This field is a comma separated
                 list of events names.

    :query series: Filter the events by series id.

    :query patch: Filter the events by patch id.

Each event type has some ``parameters`` specific to that event. At the moment,
two events are possible:

- **series-new-revision**: This event corresponds to patchwork receiving a new
  revision of a series, should it be the initial submission or subsequent
  updates. The difference can be made by looking at the version of the series.

  This event only appears when patchwork has received the full set of mails
  belonging to the same series, so the revision object is guaranteed to
  contain all patches.

  **revision**: The version of the new revision that has been created.
  ``series`` and ``revision`` can be used to retrieve the corresponding
  patches.

- **patch-state-change**: This event corresponds to patchwork receiving a
  patch state change, either automatic or manually performed by an authorized
  user, who will be identified by its patchwork-user id.

Series
~~~~~~

A series object represents a lists of patches sent to the mailing-list through
|git send-email|. It also includes all subsequent patches that are sent to
address review comments, both single patch and full new series.

A series has then ``n`` revisions, ``n`` going from ``1`` to ``version``.

.. http:get:: /api/1.0/projects/(string: linkname)/series/
.. http:get:: /api/1.0/projects/(int: project_id)/series/

    List of all Series belonging to a specific project. The project can be
    specified using either its ``linkname`` or ``id``.

    .. sourcecode:: http

        GET /api/1.0/projects/intel-gfx/series/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept
        Allow: GET, HEAD, OPTIONS

        {
            "count": 59,
            "next": "http://patchwork.example.com/api/1.0/projects/intel-gfx/series/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 3,
                    "project": 1,
                    "name": "drm/i915: Unwind partial VMA rebinding after failure in set-cache-level",
                    "n_patches": 1,
                    "submitter": 77,
                    "submitted": "2015-10-09T11:51:38",
                    "last_updated": "2015-10-09T11:51:59.013345",
                    "version": 1,
                    "reviewer": null,
                    "test_state": null,
                    "state": "initial",
                    "state_summary": [
                        {
                            "count": 1,
                            "name": "New",
                            "final": false
                        }
                    ]
                },
                {
                    "id": 5,
                    "project": 1,
                    "name": "RFC drm/i915: Stop the machine whilst capturing the GPU crash dump",
                    "n_patches": 1,
                    "submitter": 77,
                    "submitted": "2015-10-09T12:21:45",
                    "last_updated": "2015-10-09T12:21:58.657976",
                    "version": 1,
                    "reviewer": null,
                    "test_state": null,
                    "state": "initial",
                    "state_summary": [
                        {
                            "count": 1,
                            "name": "New",
                            "final": false
                        }
                    ]
                }
            ]
        }

    :>json state: The state of the series. One of ``initial``,
                  ``in progress``, ``done`` or ``incomplete``.

    :>json state_summary: A summary of the patch status in the more recent
                          revision of the series. This a a list of objects
                          containing the number of patches (``count``) in a
                          given state (``name``). ``final`` is whether the
                          state is final or not, if a final decision (ie.
                          merged or rejected) has been made about a patch.

    :query project: Filter series by project ``id``.

    :query name: Filter series by name.

    :query submitter: Filter series by submitter ``id``. ``self`` can be used
                      as a special value meaning the current logged in user.

    :query reviewer: Filter series by reviewer ``id`` or ``null`` for no
                     reviewer assigned.

    :query submitted_since: Retrieve only submitted series newer than a
                            specified time. Format is the same as ``submitted``
                            in response, an ISO 8601 date.

    :query updated_since:   Retrieve only updated series newer than a
                            specified time. Format is the same as
                            ``last_updated`` in response, an ISO 8601 date.

    :query submitted_before: Retrieve only submitted series older than the
                             specified time. Format is the same as
                             ``submitted`` in response, an ISO 8601 date.

    :query updated_before:   Retrieve only updated series older than a
                             specified time. Format is the same as
                             ``last_updated`` in response, an ISO 8601 date.

    :query test_state: Filter series by test state. Possible values are
                       ``pending``, ``info``, ``success``, ``warning``,
                       ``failure`` or ``null`` series that don't have any test
                       result. It's also possible to give a comma separated
                       list of states.


.. http:get:: /api/1.0/series/

    List of all Series known to patchwork.

    .. sourcecode:: http

        GET /api/1.0/series/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Vary: Accept
        Content-Type: application/json

        {
            "count": 344,
            "next": "http://patchwork.example.com/api/1.0/series/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 10,
                    "project": 1,
                    "name": "intel: New libdrm interface to create unbound wc user mappings for objects",
                    "n_patches": 1,
                    "submitter": 10,
                    "submitted": "2015-01-02T11:06:40",
                    "last_updated": "2015-10-09T07:55:18.608251",
                    "version": 1,
                    "reviewer": null,
                    "test_state": null,
                    "state": "initial",
                    "state_summary": [
                        {
                            "count": 1,
                            "name": "New",
                            "final": false
                        }
                    ]
                },
                {
                    "id": 1,
                    "project": 1,
                    "name": "PMIC based Panel and Backlight Control",
                    "n_patches": 4,
                    "submitter": 1,
                    "submitted": "2014-12-26T10:23:26",
                    "last_updated": "2015-10-09T07:55:01.558523",
                    "version": 1,
                    "reviewer": null,
                    "state": "initial",
                    "state_summary": [
                        {
                            "count": 4,
                            "name": "New",
                            "final": false
                        }
                    ]
                },
            ]
        }

.. http:get:: /api/1.0/series/(int: series_id)/

    A series (`series_id`). A Series object contains metadata about the series.

    .. sourcecode:: http

        GET /api/1.0/series/47/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept
        Allow: GET, PUT, PATCH, HEAD, OPTIONS

        {
            "id": 47,
            "name": "Series without cover letter",
            "n_patches": 2,
            "submitter": 21,
            "submitted": "2015-01-13T09:32:24",
            "last_updated": "2015-10-09T07:57:23.541373",
            "version": 1,
            "reviewer": null,
            "state": "initial",
            "state_summary": [
                {
                    "count": 2,
                    "name": "New",
                    "final": false
                }
            ]
        }

.. http:get:: /api/1.0/series/(int: series_id)/revisions/

    The list of revisions of the series `series_id`.

    .. sourcecode:: http

        GET /api/1.0/series/47/revisions/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept
        Allow: GET, HEAD, OPTIONS

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [
                {
                    "version": 1,
                    "cover_letter": null,
                    "patches": [
                        120,
                        121
                    ]
                }
            ]
        }

.. http:get:: /api/1.0/series/(int: series_id)/revisions/(int: version)/

    The specific ``version`` of the series `series_id`.

    .. sourcecode:: http

        GET /api/1.0/series/47/revisions/1/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept
        Allow: GET, HEAD, OPTIONS

        {
            "version": 1,
            "cover_letter": null,
            "patches": [
                120,
                121
            ]
        }

.. http:get:: /api/1.0/series/(int: series_id)/revisions/(int: version)/mbox/

    Retrieve an mbox file that will contain all patches of this revision, in
    order in which to apply them. This mbox file can be directly piped into
    ``git am``.

    :query link: Add an HTTP link to the Patchwork patch page in each commit
                 message. This link is preceded by a tag which name is given
                 as argument of this parameter, eg. ``?link=Patchwork``.

::

    $ curl -s http://patchwork.example.com/api/1.0/series/42/revisions/2/mbox/ | git am -3


.. http:post:: /api/1.0/series/(int: series_id)/revisions/(int: version)/test-results/

     Post test results for this revision.

    .. sourcecode:: http

        POST /api/1.0/series/47/revisions/1/test-results/ HTTP/1.1

        {
            "test_name": "checkpatch.pl",
            "state": "success",
            "url": "http://jenkins.example.com/logs/47/checkpatch.log",
            "summary": "total: 0 errors, 0 warnings, 10 lines checked"
        }

    :<json test_name: Required. The name of the test we're reporting results
                      for. This uniquely identifies the test. Any subsequent
                      data sent through this entry point with the same
                      ``test_name`` will be conflated into the same object.
                      It's thus possible to create a test result with a
                      ``pending`` state when a CI system picks up patches to
                      indicate testing has started and then update the result
                      with the final (``state``, ``url``, ``summary``) when
                      finished.
    :<json state: Required. State of the test results. One of ``pending``,
                  ``success``, ``warning`` or ``failure``
    :<json url: Optional. A URL where to find the detailed logs of the test
                run.
    :<json summary: Optional. A summary with some details about the results.
                    If set, this will be displayed along with the test result
                    to provide some detailed about the failure. It's suggested
                    to use ``summary`` for something short while ``url`` can
                    be used for full logs, which can be rather large.


.. http:post /api/1.0/series/(int: series_id)/revisions/(int: version)/newrevision/

    Create a new ``series-new-revision`` event for this revision. This can be
    used to re-trigger testing on the series as CI systems listen for those
    events.


Patches
~~~~~~~

.. http:get:: /api/1.0/projects/(string: linkname)/patches/
.. http:get:: /api/1.0/projects/(int: project_id)/patches/

    List of all patches belonging to a specific project. The project can be
    specified using either its ``linkname`` or ``id``.

    .. sourcecode:: http

        GET /api/1.0/projects/intel-gfx/patches/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept
        Allow: GET, HEAD, OPTIONS

        {
            "count": 1392,
            "next": "http://patchwork.example.com/api/1.0/projects/intel-gfx/patches/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "project": 1,
                    "name": "[RFC,1/4] drm/i915: Define a common data structure for Panel Info",
                    "date": "2014-12-26T10:23:27",
                    "last_updated": "2014-12-26T10:23:27",
                    "submitter": 1,
                    "state": 1,
                    "content": "<diff content>"
                },
                {
                    "id": 4,
                    "project": 1,
                    "name": "[RFC,2/4] drm/i915: Add a drm_panel over INTEL_SOC_PMIC",
                    "date": "2014-12-26T10:23:28",
                    "last_updated": "2014-12-26T10:23:28",
                    "submitter": 1,
                    "state": 1,
                    "content": "<diff content>"
                }
            ]
        }

    :query project: Filter patches by project ``id``.

    :query name: Filter patches by name.

    :query submitter: Filter patches by submitter ``id``. ``self`` can be used
                      as a special value meaning the current logged in user.

    :query submitted_since: Retrieve only submitted patches newer than a
                            specified time. Format is the same as ``date``
                            in response, an ISO 8601 date.

    :query updated_since:   Retrieve only updated patches newer than a
                            specified time. Format is the same as
                            ``last_updated`` in response, an ISO 8601 date.

    :query submitted_before: Retrieve only submitted patches older than the
                             specified time. Format is the same as
                             ``date`` in response, an ISO 8601 date.

    :query updated_before:   Retrieve only updated patches older than a
                             specified time. Format is the same as
                             ``last_updated`` in response, an ISO 8601 date.

.. http:get:: /api/1.0/patches/

    List of all patches.

    .. sourcecode:: http

        GET /api/1.0/patches/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept
        Allow: GET, HEAD, OPTIONS

        {
            "count": 1392,
            "next": "http://patchwork.example.com/api/1.0/patches/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "project": 1,
                    "name": "[RFC,1/4] drm/i915: Define a common data structure for Panel Info",
                    "date": "2014-12-26T10:23:27",
                    "last_updated": "2014-12-26T10:23:27",
                    "submitter": 1,
                    "state": 1,
                    "content": "<diff content>"
                },
                {
                    "id": 4,
                    "project": 1,
                    "name": "[RFC,2/4] drm/i915: Add a drm_panel over INTEL_SOC_PMIC",
                    "date": "2014-12-26T10:23:28",
                    "last_updated": "2014-12-26T10:23:28",
                    "submitter": 1,
                    "state": 1,
                    "content": "<diff content>"
                }
            ]
        }

.. http:get:: /api/1.0/patches/(int: patch_id)/

    A specific patch.

    .. sourcecode:: http

        GET /api/1.0/patches/120/ HTTP/1.1
        Accept: application/json

    .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json
            Vary: Accept
            Allow: GET, HEAD, OPTIONS

            {
                "id": 120,
                "name": "[1/2] drm/i915: Balance context pinning on reset cleanup",
                "date": "2015-01-13T09:32:24",
                "last_updated": "2015-01-13T09:32:24",
                "submitter": 21,
                "state": 1,
                "content": "<diff content>"
            }

.. http:get:: /api/1.0/patches/(int: patch_id)/mbox/

    Retrieve an mbox file. This mbox file can be directly piped into ``git am``.

    :query link: Add an HTTP link to the Patchwork patch page in the commit
                 message. This link is preceded by a tag which name is given
                 as argument of this parameter, eg. ``?link=Patchwork``.

::

    $ curl -s http://patchwork.example.com/api/1.0/patches/42/mbox/ | git am -3

API Revisions
-------------

**Revision 3**

- Add test results entry points:

  - /series/${id}/revisions/${version}/test-results/
  - /series/${id}/revisions/${version}/newrevision/

- Add the `project`, `name`, `submitter`, `reviewer`, `submitted_since`,
  `updated_since`, `submitted_before`, `updated_before` and `test_state` query
  parameters to the list of series entry points.

- Add the `test_state`, `state` and `test_summary` series fields.

- Add the patch-state-change event.

- Add the `name` query parameter to the /events/ entry point.

**Revision 2**

- Add mbox entry points for both patches and series:

  - /patches/${id}/mbox/
  - /series/${id}/revisions/${version}/mbox/

- Add a ``parameters`` field to events and include the revision number to the
  ``series-new-revision`` event.
- Change /series/${id}/revisions/ to follow the same list system as other
  entry points. This is technically an API change, but the impact is limited
  at this early point. Hopefully no one will ever find out.
- Document how lists of objects work.
- Make all DateTime field serialize to ISO 8061 format and not the ECMA 262
  subset.
- Add ``since``, ``name``, ``series`` and ``patch`` GET parameters to
  /projects/${id,linkname}/events/

**Revision 1**

- Add /projects/${linkname}/events/ entry point.

**Revision 0**

- Initial revision. Basic objects exposed: api root, projects, series,
  revisions and patches.

.. include:: symbols
