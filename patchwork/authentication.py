# Patchwork - automated patch tracking system
# Copyright (C) 2015 Intel Corporation
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

from rest_framework.authentication import BaseAuthentication, \
    get_authorization_header
from rest_framework import exceptions
from patchwork.models import APIToken


class APITokenAuthentication(BaseAuthentication):
    """
    Simple api token based authentication.

    Clients should authenticate by passing the api token key in the
    "Authorization" HTTP header, prepended with the string "APIToken ".
    For example:

        Authorization: APIToken 401f7ac837da42b97f613d789819ff93537bee6a
    """

    model = APIToken

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != b'apitoken':
            return None

        if len(auth) == 1:
            msg = 'Invalid API token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid API token header. API token string should ' \
                  'not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(auth[1])

    def authenticate_credentials(self, apitoken):
        apitoken = self.model.authenticate(apitoken)

        if apitoken is None:
            msg = 'Invalid API token'
            raise exceptions.AuthenticationFailed(msg)

        is_active, state = apitoken.get_state()

        if not is_active:
            msg = 'Inactive APIToken: {}'.format(state)
            raise exceptions.AuthenticationFailed(msg)

        if not apitoken.user.is_active:
            msg = 'User inactive or deleted'
            raise exceptions.AuthenticationFailed(msg)

        return (apitoken.user, apitoken)

    def authenticate_header(self, request):
        return 'APIToken'
