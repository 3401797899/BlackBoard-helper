import os

from rest_framework_extensions.cache.decorators import cache_response

from utils.api_view import APIViewPlus, ViewSetPlus
from utils.get_data import *
from utils.login import check_session
from utils.mapping import get_mapping, post_mapping
from utils.response import Response
from utils.response_status import ResponseStatus


class LoginView(APIViewPlus):
    url_pattern = 'login'

    @cache_response(timeout=60 * 5)
    def post(self, request, *args):
        params = request.data
        username = params.get('username', '')
        pwd = params.get('password', '')

        from utils.login import BBHelpLogin
        bbh_login = BBHelpLogin(username, pwd)
        return Response(ResponseStatus.OK, {'session': bbh_login.login()})


class GetDataView(ViewSetPlus):
    base_url_path = 'api'

    @cache_response(timeout=60 * 60 * 24 * 7)
    @get_mapping(value="classlist")
    @check_session
    def get_class_list(self, request, *args):
        params = request.GET
        session = params.get('session', '')
        return Response(ResponseStatus.OK, get_class_list(session))

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
