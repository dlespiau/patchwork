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

API Authentication
------------------

APIToken
~~~~~~~~

To use APIToken authentication scheme you'll need to provide it
in Authorization request headers.
If authentication fails you will get a `401` response and the body
will contain the failure reason.

    .. sourcecode:: http

        GET /api/1.0/ HTTP/1.1
        Accept: application/json
        Authorization: APIToken 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

    .. sourcecode:: http

        HTTP/1.1 401 UNAUTHORIZED
        Vary: Accept
        Content-Type: application/json

        {
            "detail": "Invalid API token"
        }


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
                    "user": null,
                    "parameters": {
                        "revision": 2
                    }
                },
                {
                },
                {
                    "name": "series-new-revision",
                    "event_time": "2015-10-20T19:49:43.895382",
                    "series": 22,
                    "user": null,
                    "parameters": {
                        "revision": 1
                    }
                }
            ]
        }

    :query since: Retrieve only events newer than a specific time. Format is
                  the same as ``event_time`` in response, an ISO 8601 date. That
                  means that the ``event_time`` from the last seen event can
                  be used in the next query with a ``since`` parameter to only
                  retrieve events that haven't been seen yet.

Each event type has some ``parameters`` specific to that event. At the moment,
only one event is possible:

- **series-new-revision**: This event corresponds to patchwork receiving a new
  revision of a series, should it be the initial submission or subsequent
  updates. The difference can be made by looking at the version of the series.

  This event only appears when patchwork has received the full set of mails
  belonging to the same series, so the revision object is guaranteed to
  contain all patches.

  **revision**: The version of the new revision that has been created.
  ``series`` and ``revision`` can be used to retrieve the corresponding
  patches.


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
                    "reviewer": null
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
                }
            ]
        }

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
                       ``pending``, ``success``, ``warning``, ``failure`` or
                       ``null`` series that don't have any test result.


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
                    "reviewer": null
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
            "reviewer": null
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


Patches
~~~~~~~

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
                    "submitter": 1,
                    "state": 1,
                    "content": "<diff content>"
                },
                {
                    "id": 4,
                    "project": 1,
                    "name": "[RFC,2/4] drm/i915: Add a drm_panel over INTEL_SOC_PMIC",
                    "date": "2014-12-26T10:23:28",
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
                "submitter": 21,
                "state": 1,
                "content": "<diff content>"
            }

.. http:get:: /api/1.0/patches/(int: patch_id)/mbox/

    Retrieve an mbox file. This mbox file can be directly piped into ``git am``.

::

    $ curl -s http://patchwork.example.com/api/1.0/patches/42/mbox/ | git am -3

APIToken
~~~~~~~~

If any of these API fails, response body contain just one field
containing the failuare reason:

    .. sourcecode:: http

            POST /api/1.0/tokens/ HTTP/1.1
            Content-Type: application/json
            Accept: application/json

            {
                "name":"Foo"
            }

    .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json
            Vary: Accept
            Allow: GET, POST, HEAD, OPTIONS

            {
                "name": ["Name exists"]
            }

.. http:get:: /api/1.0/apitoken/

    List all APITokens.

    .. sourcecode:: http

            GET /api/1.0/tokens/ HTTP/1.1
            Accept: application/json

    .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json
            Vary: Accept
            Allow: GET, POST, HEAD, OPTIONS

            [
                {
                    "id": 1,
                    "name": "JenkinsKey",
                    "user": 1,
                    "state": "active",
                    "created": "2015-11-17T09:47:04.995296"
                },
                {
                    "id": 2,
                    "name": "Key2",
                    "user": 1,
                    "state": "active",
                    "created": "2015-11-17T09:51:17.414646"
                }
            ]

.. http:get:: /api/1.0/tokens/(int: apitoken_id)/

    Get specific APIToken.

    .. sourcecode:: http

            GET /api/1.0/tokens/2/ HTTP/1.1
            Accept: application/json

    .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json
            Vary: Accept
            Allow: GET, PUT, PATCH, DELETE, HEAD, OPTIONS

            {
                "id": 2,
                "name": "Key2",
                "user": 1,
                "state": "active",
                "created": "2015-11-17T09:51:17.414646"
            }

.. http:post:: /api/1.0/tokens/

    Create new APIToken.

    .. sourcecode:: http

            POST /api/1.0/tokens/ HTTP/1.1
            Content-Type: application/json
            Accept: application/json

            {
                "name":"Foo"
            }

    .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json
            Vary: Accept
            Allow: GET, POST, HEAD, OPTIONS

            {
                "id": 3,
                "name": "Foo",
                "user": 1,
                "state": "active",
                "created": "2015-11-17T10:03:36.961686",
                "apitoken": "0949c2ba0a8aac546ce9eb33778ea8a1f44a2e85"
            }

    **Note:** This contain the generated APIToken secret
    which is included ONLY in this POST response.
    You wont be able to retrieve this APIToken again.

.. http:delete:: /api/1.0/tokens/(int: apitoken_id)/

    Delete APIToken.

    .. sourcecode:: http

            DELETE /api/1.0/tokens/3/ HTTP/1.1
            Accept: application/json

    .. sourcecode:: http

            HTTP/1.1 204 NO CONTENT
            Content-Type: application/json
            Vary: Accept
            Allow: GET, PUT, PATCH, DELETE, HEAD, OPTIONS

.. http:patch:: /api/1.0/tokens/(int: apitoken_id)/

    Modify name and/or state.

    .. sourcecode:: http

            PATCH /api/1.0/tokens/2/ HTTP/1.1
            Content-Type: application/json
            Accept: application/json

            {
                "name":"Foo"
            }

    .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json
            Vary: Accept
            Allow: GET, PUT, PATCH, DELETE, HEAD, OPTIONS

            {
                "id": 2,
                "name": "Foo",
                "user": 1,
                "state": "Active",
                "created": "2015-11-17T09:51:17.414646"
            }

.. http:put:: /api/1.0/tokens/(int: apitoken_id)/

    Modify name and state.

    .. sourcecode:: http

            PUT /api/1.0/tokens/2/ HTTP/1.1
            Content-Type: application/json
            Accept: application/json

            {
                "name":"Foo",
                "state":"Inactive"
            }

    .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json
            Vary: Accept
            Allow: GET, PUT, PATCH, DELETE, HEAD, OPTIONS

            {
                "id": 2,
                "name": "Foo",
                "user": 1,
                "state": "Inactive",
                "created": "2015-11-17T09:51:17.414646"
            }
    **Note:** If state is ommited, default value will be used ("Active").

API Revisions
-------------

**Revision 3**

- Add test results entry points:

  - /series/${id}/revisions/${version}/test-results/

- Add the `submitter`, `reviewer`, `submitted_since`, `updated_since`,
  `submitted_before` and `updated_before` query parameters to the list of
  series entry points.

**Revision 2**

- Add mbox entry points for both patches and series:

  - /patches/${id}/mbox/
  - /series/${id}/revisions/${version}/mbox/

- Add a ``parameters`` field to events and include the revision number to the
  ``series-new-revision`` event.
- Change /series/${id}/revisions/ to follow the same list system as other
  entry points. This is technically an API change, but the impact is limited
  at this early point. Hopefully noone will ever find out.
- Document how lists of objects work.
- Make all DateTime field serialize to ISO 8061 format and not the ECMA 262
  subset.
- Add a ``since`` GET parameter to /projects/${id,linkname}/events/

**Revision 1**

- Add /projects/${linkname}/events/ entry point.

**Revision 0**

- Initial revision. Basic objects exposed: api root, projects, series,
  revisions and patches.

.. include:: symbols
