import datetime
import os

from rest_framework_extensions.cache.decorators import cache_response
from django.core.cache import cache
from django.conf import settings

from utils.api_view import APIViewPlus, ViewSetPlus
from utils.get_data import *
from utils.login import check_session, classlist_key
from utils.mapping import get_mapping, post_mapping
from utils.response import Response
from utils.response_status import ResponseStatus
from utils.exception import ValidationException
from utils.get_data import get_class_list as class_list

from .models import *


class LoginView(APIViewPlus):
    url_pattern = 'login'

    @cache_response(timeout=60 * 5)
    def post(self, request, *args):
        params = request.data
        username = params.get('username', '')
        pwd = params.get('password', '')
        if not all([username, pwd]):
            raise ValidationException(ResponseStatus.VERIFICATION_ERROR)
        from utils.login import BBHelpLogin
        bbh_login = BBHelpLogin(username, pwd)
        return Response(ResponseStatus.OK, {'session': bbh_login.login()})


class GetDataView(ViewSetPlus):
    base_url_path = 'api'

    @cache_response(timeout=60 * 60 * 24 * 7, key_func=classlist_key)
    @get_mapping(value="classlist")
    @check_session
    def get_class_list(self, request, *args):
        params = request.GET
        session = params.get('session', '')
        return Response(ResponseStatus.OK, class_list(session))

    @cache_response(timeout=30)
    @get_mapping(value="classmenu")
    @check_session
    def get_class_menu(self, request, *args):
        params = request.GET
        course_id = params.get('id', '')
        session = params.get('session', '')
        return Response(ResponseStatus.OK, get_class_detail_by_id(course_id, session))

    @cache_response(timeout=30)
    @get_mapping(value="details")
    @check_session
    def get_details(self, request, *args):
        params = request.GET
        course_id = params.get('course_id', '')
        content_id = params.get('content_id', '')
        session = params.get('session', '')
        return Response(ResponseStatus.OK, get_content_by_id(course_id, content_id, session))

    @cache_response(timeout=30)
    @get_mapping(value="course_score")
    @check_session
    def get_score(self, request, *args):
        params = request.GET
        course_id = params.get('course_id', '')
        session = params.get('session', '')
        return Response(ResponseStatus.OK, get_class_score(course_id, session))

    @cache_response(timeout=30)
    @get_mapping(value="file_convert")
    def get_file_convert(self, request, *args):
        params = request.GET
        url = params.get('url', '')
        if url.startswith('https://wlkc.ouc.edu.cnhttp'):
            return Response(ResponseStatus.OK, {"url": url.replace('https://wlkc.ouc.edu.cn', ''), "name": None})
        new_url = requests.get(url, proxies=proxies, verify=False)
        new_url = new_url.url
        return Response(ResponseStatus.OK, {"url": new_url, "name": os.path.basename(new_url)})

    @get_mapping(value="announcements")
    @check_session
    def get_announcements_view(self, request, *args):
        params = request.GET
        session = params.get('session', '')
        course_id = params.get('course_id', '')
        return Response(ResponseStatus.OK, get_announcements(session, course_id))

    @post_mapping(value="homework1")
    @check_session
    def post_homework_view(self, request, *args):
        params = request.data
        session = params.get('session', '')
        course_id = params.get('course_id', '')
        content_id = params.get('content_id', '')
        resubmit = params.get('resubmit', '')
        if resubmit:
            url = f"https://wlkc.ouc.edu.cn/webapps/assignment/uploadAssignment?action=newAttempt&course_id={course_id}&content_id={content_id}"
        else:
            url = f"https://wlkc.ouc.edu.cn/webapps/assignment/uploadAssignment?content_id={content_id}&course_id={course_id}&group_id=&mode=view"
        files = request.FILES.getlist('files')[0].file.name
        name = params.get('name', '')
        content = params.get('content', '')
        rep = submit_homework1(session, url, course_id, content_id, files, content, name)
        if rep:
            return Response(ResponseStatus.OK, rep)
        else:
            return Response(ResponseStatus.OK, {'warning': '提交失败'})

    @cache_response(timeout=5)
    @get_mapping(value="check_homework")
    @check_session
    def get_check_homework(self, request, *args):
        _id = request.GET.get("id", "")
        session = request.GET.get("session", "")
        status = check_homework(_id, session)
        return Response(ResponseStatus.OK, status)


class AdminDataView(APIViewPlus):
    url_pattern = 'admin/data'

    def get(self, request, *args):

        # 获取用户数量，以及新增用户数量
        # 获取今日日期
        date = datetime.date.today()
        today = date.today()
        # 查询，同时获取总用户数量和今日新增用户数量
        # user_stats = User.objects.annotate(
        #     total_users=Count('id'),
        #     new_users_today=Count('id', filter=F('created_time') == today)
        # ).values('total_users', 'new_users_today').first()

        total_users = User.objects.count()
        new_users_today = User.objects.filter(created_time__date = today).count()

        # 获取接口访问数量
        visit_url_dict = cache.get('visit_url_dict', {})
        all_visit_count = cache.get('visit_url_count', 0)
        today_visit = visit_url_dict.get(datetime.date.today().strftime('%Y-%m-%d'), {})
        today_visit_count = sum(today_visit.values())
        head_10 = [{"url":item[0],"count":item[1]} for item in sorted(today_visit.items(), key=lambda x: -x[1])[:10]]

        # 获取作业提醒数量
        current_time = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        timestamp = int(current_time.timestamp())
        last_homework_count = Homework.objects.extra(where=[f'cast(`last_notice_time` as DECIMAL) >= {timestamp}']).count()
        all_homework_count = Homework.objects.filter(last_notice_time__isnull=False).count()

        # 获取获取作业数量
        all_fetch_homework_count = cache.get('fetch_homework_count_count', 0)
        fetch_homework_count = cache.get("fetch_homework_count", {'1': 0})
        last_fetch_homework_count = sorted(
            fetch_homework_count.items(), key=lambda x: x[0])[-1][1]

        # 获取日志内容
        lines = 20
        file_path = os.path.join(settings.BASE_DIR,'logs/notice.log')
        with open(file_path, 'r') as file:
            # 使用readlines()获取所有行
            all_lines = file.readlines()

            # 获取倒数lines行
            last_lines = all_lines[-lines:]

        logs = []

        for line in last_lines[::-1]:
            _, time, content = re.split(r'\[|\]', line)
            logs.append({"time":time,"content":content})

        data = {
            "total_users": total_users,
            "new_users_today": new_users_today,
            "all_visit_count": all_visit_count,
            "today_visit_count": today_visit_count,
            "head_10": head_10,
            "last_homework_count": last_homework_count,
            "all_homework_count": all_homework_count,
            "all_fetch_homework_count": all_fetch_homework_count,
            "last_fetch_homework_count": last_fetch_homework_count,
            "logs": logs
        }
        return Response(ResponseStatus.OK, data)
