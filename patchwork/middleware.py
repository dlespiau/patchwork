class AccessControlAllowOriginMiddleware:
    """Allow all API GET (read-only) requests from any domain"""
    def process_response(self, request, response):
        if request.path.startswith('/api/') and \
           (request.method == 'GET' or request.method == 'OPTIONS'):
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
