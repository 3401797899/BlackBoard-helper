import time

from django.shortcuts import render
from utils.api_view import APIViewPlus, ViewSetPlus
from utils.mapping import post_mapping, get_mapping
import requests
from utils.login import login_by_my
import base64
from blackboard.models import User
from utils.response import Response
from utils.response_status import ResponseStatus
from django.conf import settings


# Create your views here.
class WechatView(ViewSetPlus):
    base_url_path = 'api/wechat'

    def get_openid(self, code):
        url = f"https://api.weixin.qq.com/sns/jscode2session?appid={settings.APP_ID}&secret={settings.APP_SECRET}&js_code={code}&grant_type=authorization_code"
        r = requests.get(url).json()
        try:
            return r['openid']
        except:
            return None

    @get_mapping(value="notice")
    def open_notice(self, request, *args, **kwargs):
        params = request.query_params
        username = params.get('username', '')
        pwd = params.get('password', '')
        code = params.get('code', '')
        open_id = self.get_openid(code)
        if open_id is None:
            return Response(ResponseStatus.OPENID_ERROR)
        password = base64.b64decode(pwd.encode('utf-8')).decode('utf-8')
        login = login_by_my(username, password)
        if login == 'login failed':
            return Response(ResponseStatus.LOGIN_ERROR)
        user = User.objects.get(username=username)
        user.password = pwd
        user.status = True
        user.session = login
        user.expire = time.time() + 15 * 60
        user.open_id = open_id
        user.save()
        return Response(ResponseStatus.OK)

    @get_mapping(value="subcount")
    def add_subcount(self, request, *args, **kwargs):
        params = request.query_params
        user = User.objects.get(username=params.get('username', ''))
        user.subCount += 1
        user.save()
        return Response(ResponseStatus.OK)
