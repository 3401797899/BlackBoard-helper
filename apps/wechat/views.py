import requests

from django.conf import settings

from utils.api_view import ViewSetPlus
from utils.mapping import get_mapping
from utils.response import Response
from utils.response_status import ResponseStatus
from utils.exception import ValidationException
from utils.login import BBHelpLogin
from utils.get_data import BBGetData
from blackboard.models import Notify, User


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
        type = params.get('type', 'homework')
        if type not in ['homework', 'score', 'notice']:
            raise ValidationException(ResponseStatus.VALIDATION_ERROR)

        # 获取openid
        code = params.get('code', '')
        open_id = self.get_openid(code)

        # 更新数据库，记录ics_id，open_id，并打开提醒
        bb_login = BBHelpLogin(username, pwd)
        user = bb_login.user
        user.password = pwd
        user.open_id = open_id
        if type == 'homework':
            user.ics_id = BBGetData.get_ics_id(bb_login.login())
        user.save()
        notice = Notify.objects.get_or_create(
            user=user,
            type=type,
            defaults={
                'user_id': user.id,
                'type': type,
            }
        )
        if not notice.open_status:
            notice.open_status = True
            notice.save()

        return Response(ResponseStatus.OK)

    @get_mapping(value="close")
    def close_notice(self, request, *args, **kwargs):
        params = request.query_params
        username = params.get('username', '')
        pwd = params.get('password', '')
        # 校验数据库
        user = User.objects.filter(username=username, password=pwd)
        if not user.exists():
            raise ValidationException(ResponseStatus.USER_NOT_EXIST)
        type = params.get('type', '')
        if type not in ['homework', 'score', 'notice']:
            raise ValidationException(ResponseStatus.VALIDATION_ERROR)
        notice = Notify.objects.filter(user__username=username, type=type, open_status=True)
        if not notice.exists():
            raise ValidationException(ResponseStatus.NOTICE_CLOSED_ERROR)
        notice = notice.first()
        notice.open_status = False
        notice.save()
        return Response(ResponseStatus.OK)

    @get_mapping(value="subcount")
    def add_subcount(self, request, *args, **kwargs):
        params = request.query_params
        username = params.get('username', '')
        type = params.get('type', 'homework')
        if type not in ['homework', 'score', 'notice']:
            raise ValidationException(ResponseStatus.VALIDATION_ERROR)
        notice = Notify.objects.filter(user__username=username, type=type, open_status=True)
        if not notice.exists():
            raise ValidationException(ResponseStatus.NOTICE_CLOSED_ERROR)
        notice = notice.first()
        notice.count += 1
        notice.save()
        return Response(ResponseStatus.OK)

    @get_mapping(value="getcount")
    def get_count(self, request, *args, **kwargs):
        params = request.query_params
        username = params.get('username', '')
        type = params.get('type', 'homework')
        if type not in ['homework', 'score', 'notice']:
            raise ValidationException(ResponseStatus.VALIDATION_ERROR)
        notice = Notify.objects.filter(user__username=username, type=type, open_status=True)
        if not notice.exists():
            raise ValidationException(ResponseStatus.NOTICE_CLOSED_ERROR)
        count = notice.first().count
        return Response(ResponseStatus.OK, {"count": count})
