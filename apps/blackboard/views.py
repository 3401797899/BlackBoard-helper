import os
from utils.api_view import APIViewPlus, ViewSetPlus
from utils.get_data import *
from utils.http_by_proxies import get_by_proxies, custom_key, headers, proxies
from utils.login import login_by_my, login_by_wlkc
from utils.mapping import get_mapping, post_mapping
from utils.response import Response
from utils.response_status import ResponseStatus
import base64
from binascii import Error as binasciiError
from blackboard.models import User
from utils.login import verify
from django.conf import settings

# 开启定时任务
if not settings.DEBUG:
    from blackboard import scheduler

status_cache = requests_cache.CachedSession('status_cache', key_fn=custom_key)


class LoginView(APIViewPlus):
    url_pattern = 'login'

    @staticmethod
    def get_user_from_database(username, password):
        user = User.objects.filter(username=username)
        if user.exists():
            user = user.first()
            if user.password == password and verify(user.session):
                return Response(ResponseStatus.OK, {'session': user.session})
            else:
                return user
        else:
            return None

    def post(self, request, *args):
        params = request.data
        username = params.get('username', '')
        pwd = params.get('password', '')
        if username:
            user = self.get_user_from_database(username, pwd)
        else:
            return Response(ResponseStatus.LOGIN_ERROR)
        if isinstance(user, Response):
            return user
        try:
            password = base64.b64decode(pwd.encode('utf-8')).decode('utf-8')
        except binasciiError:
            return Response(ResponseStatus.LOGIN_ERROR)
        t = login_by_wlkc(username, password)
        if t == 'login failed':
            return Response(ResponseStatus.LOGIN_ERROR)
        # 其他情况下，保存session
        if user and isinstance(user, User):
            user.session = t
            user.expire = time.time() + 15 * 60
            user.save()
        else:
            User.objects.create(username=username, session=t, expire=time.time() + 15 * 60,
                                status=False)
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
        if url.startswith('https://wlkc.ouc.edu.cnhttp'):
            return Response(ResponseStatus.OK, {"url": url.replace('https://wlkc.ouc.edu.cn', ''), "name": None})
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
        status_cache.cache.clear()
        if rep:
            return Response(ResponseStatus.OK, rep)
        else:
            return Response(ResponseStatus.OK, {'warning': '提交失败'})

    @get_mapping(value="check_homework")
    def get_check_homework(self, request, *args):
        _id = request.GET.get("id", "")
        session = request.GET.get("session", "")
        if not verify(session):
            return Response(ResponseStatus.VERIFICATION_ERROR)
        url = f'https://wlkc.ouc.edu.cn/webapps/calendar/launch/attempt/_blackboard.platform.gradebook2.GradableItem-{_id}'
        headers.update({'Cookie': session})
        r = status_cache.get(url, headers=headers, verify=False, expire_after=datetime.timedelta(minutes=10))
        u = r.url
        content_id = re.findall('content_id=(.*?)&', u)
        course_id = re.findall('course_id=(.*?)&', u)
        e = etree.HTML(r.text)
        if not all([content_id, course_id]):
            return Response(ResponseStatus.GET_HOMEWORK_STATUS_ERROR)
        data = {
            'finished': False,
            'submit': True,
            'content_id': content_id[0],
            'course_id': course_id[0]
        }
        if e.xpath("//input[@class='submit button-1' and @name='bottom_开始']"):
            return Response(ResponseStatus.OK, data)
        if e.xpath("//input[@class='submit button-1' and @name='bottom_提交']"):
            return Response(ResponseStatus.OK, data)
        else:
            if e.xpath("//input[@class='submit button-1' and @name='bottom_开始新的']"):
                data.update({'finished': True, 'submit': True})
            else:
                data.update({'finished': True, 'submit': False})
            return Response(ResponseStatus.OK, data)
