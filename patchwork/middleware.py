class AccessControlAllowOriginMiddleware:
    """Allow all API GET (read-only) requests from any domain"""
    def process_response(self, request, response):
        if request.path.startswith('/api/') and request.method == 'GET':
            response['Access-Control-Allow-Origin'] = '*'
        return response
