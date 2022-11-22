import datetime
from utils.api_view import APIViewPlus, ViewSetPlus
from utils.get_data import *
from utils.login import login_by_my
from utils.mapping import get_mapping, post_mapping
from utils.response_status import ResponseStatus
from utils.response import Response
import os
from utils.http_by_proxies import get_by_proxies, post_by_proxies, cache


def verify(session):
    return 'results' in get_by_proxies('https://wlkc.ouc.edu.cn/learn/api/public/v1/calendars?limit=1', session,
                                       expire_after=datetime.timedelta(minutes=1)).text


class LoginView(APIViewPlus):
    url_pattern = 'login'

    def post(self, request, *args):
        params = request.data
        t = login_by_my(params.get('username', ''), params.get('password', ''))
        if t == 'login failed':
            return Response(ResponseStatus.LOGIN_ERROR)
        return Response(ResponseStatus.OK, {"session": t})


class GetDataView(ViewSetPlus):
    base_url_path = 'api'

    @get_mapping(value="classlist")
    def get_class_list(self, request, *args):
        params = request.GET
        session = params.get('session', '')
        if not verify(session):
            return Response(ResponseStatus.VERIFICATION_ERROR)
        data_list = get_class_list(session)
        data = dict()
        for each in data_list:
            name = each['name'].split()[-1]
            year = each['name'][:5]
            if year not in data.keys():
                data[year] = list()
            data[year].append({'name': name, 'teacher': each['teacher'], 'id': each['id']})
        s = ['C', 'X', 'Q']
        l = sorted(data.items(), key=lambda x: x[0][:4] + str(s.index(x[0][-1])), reverse=True)
        d = {i[0]: i[1] for i in l}
        return Response(ResponseStatus.OK, d)

    @get_mapping(value="classmenu")
    def get_class_menu(self, request, *args):
        params = request.GET
        i_id = params.get('id', '')
        url = "https://wlkc.ouc.edu.cn/webapps/blackboard/execute/launcher?type=Course&id=" + i_id + "&url="
        session = params.get('session', '')
        if not verify(session):
            return Response(ResponseStatus.VERIFICATION_ERROR)
        data = get_class_detail_by_url(url, session)
        return Response(ResponseStatus.OK, data)

    @get_mapping(value="details")
    def get_details(self, request, *args):
        params = request.GET
        course_id = params.get('course_id', '')
        content_id = params.get('content_id', '')
        session = params.get('session', '')
        if not verify(session):
            return Response(ResponseStatus.VERIFICATION_ERROR)
        if course_id == '' or content_id == '':
            return Response(ResponseStatus.VALIDATION_ERROR)
        else:
            return Response(ResponseStatus.OK, get_content_by_id(course_id, content_id, session))

    @get_mapping(value="course_score")
    def get_score(self, request, *args):
        params = request.GET
        course_id = params.get('course_id', '')
        session = params.get('session', '')
        if not verify(session):
            return Response(ResponseStatus.VERIFICATION_ERROR)
        if not all([course_id, session]):
            return Response(ResponseStatus.VALIDATION_ERROR)
        else:
            return Response(ResponseStatus.OK, get_class_score(course_id, session))

    @get_mapping(value="file_convert")
    def get_file_convert(self, request, *args):
        params = request.GET
        url = params.get('url', '')
        new_url = get_by_proxies(url, expire_after=datetime.timedelta(days=7))
        new_url = new_url.url
        return Response(ResponseStatus.OK, {"url": new_url, "name": os.path.basename(new_url)})

    @get_mapping(value="announcements")
    def get_announcements_view(self, request, *args):
        params = request.GET
        session = params.get('session', '')
        course_id = params.get('course_id', '')
        if not verify(session):
            return Response(ResponseStatus.VERIFICATION_ERROR)
        return Response(ResponseStatus.OK, get_announcements(session, course_id))

    @post_mapping(value="homework1")
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

    @get_mapping(value="check_homework")
    def get_check_homework(self, request, *args):
        _id = request.GET.get("id", "")
        session = request.GET.get("session", "")
        url = f'https://wlkc.ouc.edu.cn/webapps/calendar/launch/attempt/_blackboard.platform.gradebook2.GradableItem-{_id}'
        r = get_by_proxies(url, session, expire_after=datetime.timedelta(seconds=0))
        u = r.url
        content_id = re.findall('content_id=(.*?)&', u)
        course_id = re.findall('course_id=(.*?)&', u)
        e = etree.HTML(r.text)
        data = {
            'finished': False,
            'submit': True,
            'content_id': content_id[0],
            'course_id': course_id[0]
        }
        if e.xpath("//input[@class='submit button-1' and @name='bottom_提交']"):
            return Response(ResponseStatus.OK, data)
        else:
            if e.xpath("//input[@class='submit button-1' and @name='bottom_开始新的']"):
                data.update({'finished': True, 'submit': True})
            else:
                data.update({'finished': True, 'submit': False})
            return Response(ResponseStatus.OK, data)
