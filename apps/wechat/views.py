import requests

from django.conf import settings

from utils.api_view import ViewSetPlus
from utils.mapping import get_mapping
from utils.response import Response
from utils.response_status import ResponseStatus
from utils.exception import ValidationException
from utils.login import BBHelpLogin
from utils.get_data import BBGetData
from blackboard.models import User


# Create your views here.
class WechatView(ViewSetPlus):
    base_url_path = 'api/wechat'

    def get_openid(self, code):
        url = f"https://api.weixin.qq.com/sns/jscode2session?appid={settings.APP_ID}&secret={settings.APP_SECRET}&js_code={code}&grant_type=authorization_code"
        r = requests.get(url).json()
        if 'openid' not in r:
            raise ValidationException(ResponseStatus.OPENID_ERROR)
        return r['openid']

    @get_mapping(value="notice")
    def open_notice(self, request, *args, **kwargs):
        params = request.query_params
        username = params.get('username', '')
        pwd = params.get('password', '')

        # 获取openid
        code = params.get('code', '')
        open_id = self.get_openid(code)

        # 更新数据库，记录ics_id，open_id，并打开提醒
        bb_login = BBHelpLogin(username, pwd)
        user = bb_login.user
        user.password = pwd
        user.status = True
        user.open_id = open_id
        user.ics_id = BBGetData.get_ics_id(bb_login.login())
        user.save()
        return Response(ResponseStatus.OK)

    def _get_user_by_username(self, username):
        if not username:
            raise ValidationException(ResponseStatus.USER_NOT_EXIST)
        user = User.objects.filter(username=username)
        if user.exists():
            return user.first()
        else:
            raise ValidationException(ResponseStatus.USER_NOT_EXIST)

    @get_mapping(value="subcount")
    def add_subcount(self, request, *args, **kwargs):
        params = request.query_params
        username = params.get('username', '')
        user = self._get_user_by_username(username)
        user.subCount += 1
        user.save()
        return Response(ResponseStatus.OK)

    @get_mapping(value="getcount")
    def get_count(self, request, *args, **kwargs):
        params = request.query_params
        username = params.get('username', '')
        count = self._get_user_by_username(username).subCount
        return Response(ResponseStatus.OK, {"count": count})
