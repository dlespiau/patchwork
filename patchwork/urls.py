# Patchwork - automated patch tracking system
# Copyright (C) 2008 Jeremy Kerr <jk@ozlabs.org>
#
# This file is part of the Patchwork package.
#
# Patchwork is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Patchwork is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchwork; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from rest_framework_nested import routers
from patchwork.views.series import SeriesListView, SeriesView
import patchwork.views.api as api
import patchwork.views
import patchwork.views.bundle
import patchwork.views.project
import patchwork.views.patch
import patchwork.views.user
import patchwork.views.mail
import patchwork.views.base
import patchwork.views.xmlrpc

# API

# /projects/$project/
project_router = routers.SimpleRouter()
project_router.register('projects', api.ProjectViewSet)
# /projects/$project/patches/
patches_list_router = routers.NestedSimpleRouter(project_router, 'projects',
                                                 lookup='project')
patches_list_router.register(r'patches', api.PatchListViewSet)
# /projects/$project/series/
series_list_router = routers.NestedSimpleRouter(project_router, 'projects',
                                                lookup='project')
series_list_router.register(r'series', api.SeriesListViewSet)
# /projects/$project/events/
event_router = routers.NestedSimpleRouter(project_router, 'projects',
                                          lookup='project')
event_router.register(r'events', api.EventLogViewSet)
# /series/$id/
series_router = routers.SimpleRouter()
series_router.register(r'series', api.SeriesViewSet)
# /series/$id/revisions/$rev
revisions_router = routers.NestedSimpleRouter(series_router, 'series',
                                              lookup='series')
revisions_router.register(r'revisions', api.RevisionViewSet)
# /series/$id/revisions/$rev/test-results/
revision_results_router = routers.NestedSimpleRouter(revisions_router,
                                                     'revisions',
                                                     lookup='version')
revision_results_router.register(r'test-results', api.RevisionResultViewSet,
                                 base_name='revision-results')
# /patches/$id/
patches_router = routers.SimpleRouter()
patches_router.register(r'patches', api.PatchViewSet)
# /patches/$id/test-restults/
patch_results_router = routers.NestedSimpleRouter(patches_router, 'patches',
                                                  lookup='patch')
patch_results_router.register(r'test-results', api.PatchResultViewSet,
                              base_name='patch-results')


admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),

    # API
    url(r'^api/1.0/$', api.API.as_view(), name='api-root'),
    url(r'^api/1.0/', include(project_router.urls)),
    url(r'^api/1.0/', include(patches_list_router.urls)),
    url(r'^api/1.0/', include(series_list_router.urls)),
    url(r'^api/1.0/', include(series_router.urls)),
    url(r'^api/1.0/', include(revisions_router.urls)),
    url(r'^api/1.0/', include(revision_results_router.urls)),
    url(r'^api/1.0/', include(patches_router.urls)),
    url(r'^api/1.0/', include(patch_results_router.urls)),
    url(r'^api/1.0/', include(event_router.urls)),

    # project views:
    url(r'^$', patchwork.views.base.projects,
        name='root'),
    url(r'^project/(?P<project_id>[^/]+)/list/$', patchwork.views.patch.list,
        name='patch_list'),
    url(r'^project/(?P<project_id>[^/]+)/patches/$',
        patchwork.views.patch.list,
        name='patches_list'),
    url(r'^project/(?P<project_id>[^/]+)/$', patchwork.views.project.project,
        name='project'),

    # series views
    url(r'^project/(?P<project>[^/]+)/series/$', SeriesListView.as_view(),
        name='series_list'),
    url(r'^series/(?P<series>\d+)/$', SeriesView.as_view(),
        name='series'),

    # patch views
    url(r'^patch/(?P<patch_id>\d+)/$', patchwork.views.patch.patch,
        name='patch'),
    url(r'^patch/(?P<patch_id>\d+)/raw/$', patchwork.views.patch.content,
        name='patch_content'),
    url(r'^patch/(?P<patch_id>\d+)/mbox/$', patchwork.views.patch.mbox,
        name='patch_mbox'),
    url(r'^patch/msgid/(?P<msgid>[^/]+)/$', patchwork.views.patch.msgid,
        name='patch_msgid'),

    # project bundles
    url(r'^project/(?P<project_id>[^/]+)/bundles/$',
        patchwork.views.bundle.bundles,
        name='bundle_list'),

    # logged-in user stuff
    url(r'^user/$', patchwork.views.user.profile,
        name='user'),
    url(r'^user/todo/$', patchwork.views.user.todo_lists,
        name='todo_list'),
    url(r'^user/todo/(?P<project_id>[^/]+)/$', patchwork.views.user.todo_list),

    url(r'^user/bundles/$', patchwork.views.bundle.bundles,
        name='bundle_list'),

    url(r'^user/link/$', patchwork.views.user.link,
        name='user_link'),
    url(r'^user/unlink/(?P<person_id>[^/]+)/$', patchwork.views.user.unlink,
        name='user_unlink'),

    # password change
    url(r'^user/password-change/$', auth_views.password_change,
        name='password_change'),
    url(r'^user/password-change/done/$', auth_views.password_change_done,
        name='password_change_done'),
    url(r'^user/password-reset/$', auth_views.password_reset,
        name='password_reset'),
    url(r'^user/password-reset/mail-sent/$', auth_views.password_reset_done,
        name='password_reset_done'),
    url(r'^user/password-reset/(?P<uidb64>[0-9A-Za-z_\-]+)/'
        r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm,
        name='password_reset_confirm'),
    url(r'^user/password-reset/complete/$',
        auth_views.password_reset_complete,
        name='password_reset_complete'),

    # login/logout
    url(r'^user/login/$', auth_views.login,
        {'template_name': 'patchwork/login.html'},
        name='auth_login'),
    url(r'^user/logout/$', auth_views.logout,
        {'next_page': '/'},
        name='auth_logout'),

    # registration
    url(r'^register/', patchwork.views.user.register,
        name='register'),

    # public view for bundles
    url(r'^bundle/(?P<username>[^/]*)/(?P<bundlename>[^/]*)/$',
     patchwork.views.bundle.bundle, name='bundle'),
    url(r'^bundle/(?P<username>[^/]*)/(?P<bundlename>[^/]*)/mbox/$',
     patchwork.views.bundle.mbox, name='bundle_mbox'),

    url(r'^confirm/(?P<key>[0-9a-f]+)/$', patchwork.views.base.confirm,
        name='confirm'),

    # submitter autocomplete
    url(r'^submitter/$', patchwork.views.submitter_complete),
    # user autocomplete
    url(r'^complete_user/$', patchwork.views.user_complete),

    # email setup
    url(r'^mail/$', patchwork.views.mail.settings,
        name='mail_settings'),
    url(r'^mail/optout/$', patchwork.views.mail.optout,
        name='mail_optout'),
    url(r'^mail/optin/$', patchwork.views.mail.optin,
        name='mail_optin'),

    # help!
    url(r'^help/(?P<path>.*)$', patchwork.views.base.help,
        name='help'),
]

if 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

if settings.ENABLE_XMLRPC:
    urlpatterns += [
                   url(r'xmlrpc/$', patchwork.views.xmlrpc.xmlrpc,
                       name='xmlrpc'),
                   url(r'^pwclient/$', patchwork.views.pwclient,
                       name='pwclient'),
                   url(r'^project/(?P<project_id>[^/]+)/pwclientrc/$',
                       patchwork.views.pwclientrc,
                       name='pwclientrc'),
                   ]

# redirect from old urls
if settings.COMPAT_REDIR:
    urlpatterns += [
                   url(r'^user/bundle/(?P<bundle_id>[^/]+)/$',
                    patchwork.views.bundle.bundle_redir),
                   url(r'^user/bundle/(?P<bundle_id>[^/]+)/mbox/$',
                   patchwork.views.bundle.mbox_redir),
                   ]
