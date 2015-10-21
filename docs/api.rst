APIs
===========

REST API
--------

API metadata
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
            "next": "http://127.0.0.1:8000/api/1.0/events/?page=2",
            "previous": null,
            "results": [
                {
                    "name": "series-new-revision",
                    "event_time": "2015-10-20T19:49:49.494",
                    "series": 23,
                    "user": null
                },
                {
                    "name": "series-new-revision",
                    "event_time": "2015-10-20T19:49:43.895",
                    "series": 22,
                    "user": null
                }
            ]
        }

At the moment, only one event is listed:

- **series-new-revision**: This event corresponds to patchwork receiving a
  full new revision of a series, should it be the initial submission of
  subsequent updates. The difference can be made by looking at the version of
  the series.

Series
~~~~~~

A series object represents a lists of patches sent to the mailing-list through
``git-send-email``. It also includes all subsequent patches that are sent to
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
            "next": "http://patchwork.freedesktop.org/api/1.0/projects/intel-gfx/series/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 3,
                    "project": 1,
                    "name": "drm/i915: Unwind partial VMA rebinding after failure in set-cache-level",
                    "n_patches": 1,
                    "submitter": 77,
                    "submitted": "2015-10-09T11:51:38",
                    "last_updated": "2015-10-09T11:51:59.013",
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
                    "last_updated": "2015-10-09T12:21:58.657",
                    "version": 1,
                    "reviewer": null,
                }
            ]
        }

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
            "next": "http://127.0.0.1:8000/api/1.0/series/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 10,
                    "project": 1,
                    "name": "intel: New libdrm interface to create unbound wc user mappings for objects",
                    "n_patches": 1,
                    "submitter": 10,
                    "submitted": "2015-01-02T11:06:40",
                    "last_updated": "2015-10-09T07:55:18.608",
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
                    "last_updated": "2015-10-09T07:55:01.558",
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
            "last_updated": "2015-10-09T07:57:23.541",
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

        [
            {
                "version": 1,
                "cover_letter": null,
                "patches": [
                    120,
                    121
                ]
            }
        ]

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
            "next": "http://127.0.0.1:8000/api/1.0/patches/?page=2",
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

API Revisions
~~~~~~~~~~~~~

**Revision 1**

- Add /projects/${linkname}/events/ entry point.

**Revision 0**

- Initial revision. Basic objects exposed: api root, projects, series,
  revisions and patches.
