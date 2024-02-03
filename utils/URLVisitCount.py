import datetime

from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin


class URLVisitCountMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 获取当前访问的URL
        current_url = request.path
        pass_list = [
            '/',
            '/admin/data'
        ]
        if current_url not in pass_list:
            today = datetime.date.today().strftime('%Y-%m-%d')
            visit_url_dict = cache.get_or_set(
                'visit_url_dict', {}, timeout=None)
            visit_url_count = cache.get_or_set(
                'visit_url_count', 0, timeout=None)
            if today not in visit_url_dict:
                visit_url_dict = {}
                visit_url_dict[today] = {}

            if current_url not in visit_url_dict[today]:
                visit_url_dict[today][current_url] = 0

            visit_url_dict[today][current_url] += 1
            # 增加Redis中该URL的访问计数
            cache.set('visit_url_dict', visit_url_dict, timeout=None)
            cache.set('visit_url_count', visit_url_count + 1, timeout=None)
        # print(cache.get('visit_url_dict'))

    def process_response(self, request, response):
        if request.path == '/admin/data':
            response['Access-Control-Allow-Origin'] = '*'
        return response
