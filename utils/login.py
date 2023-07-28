import base64
import datetime
import os
import re
import requests
import time

from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
from Crypto.PublicKey import RSA
from functools import wraps

from blackboard.models import User
from BlackBoard.settings import proxies
from utils.funcs import session_status_cache
from utils.response_status import ResponseStatus
from utils.exception import ValidationException


def check_session(func):
    @wraps(func)
    def wrapper(instance, *args, **kwargs):
        session = instance.request.GET.get('session', '')
        if BBLogin().session_expired(session):
            raise ValidationException(ResponseStatus.VERIFICATION_ERROR)
        return func(instance.request, *args, **kwargs)

    return wrapper


class BBLogin:

    def encrypt(self, message):
        rsa_file = os.path.join(os.getcwd(), 'utils/publicKey.rsa')
        with open(rsa_file) as f:
            key = f.read()
            pub_key = RSA.importKey(str(key))
            cipher = PKCS1_cipher.new(pub_key)
            rsa_text = base64.b64encode(cipher.encrypt(bytes(message.encode("utf8"))))
            return rsa_text.decode('utf-8')

    def check_password(self, username, password):
        data = {
            'username': username,
            'password': self.encrypt(password)
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.39',
        }
        t = requests.post('https://id-ouc-edu-cn-8071-p.otrust.ouc.edu.cn/sso/ssoLogin?sf_request_type=ajax', data=data,
                          headers=headers, proxies=proxies, verify=False)
        if not t.text == '{"state":true}':
            return False
        return True

    def get_session_id(self, username, password):
        r = requests.session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.39',
        }
        r.get(
            'https://id-ouc-edu-cn-8071-p.otrust.ouc.edu.cn/sso/login?service=https%3A%2F%2Fwlkc.ouc.edu.cn%2Fwebapps%2Fbb-sso-BBLEARN%2Findex.jsp',
            verify=False, headers=headers, proxies=proxies)
        data = {
            'username': username,
            'password': self.encrypt(password)
        }
        t = r.post('https://id-ouc-edu-cn-8071-p.otrust.ouc.edu.cn/sso/ssoLogin', data=data, headers=headers,
                   proxies=proxies, verify=False)
        if not t.text == '{"state":true}':
            return None
        url = 'https://id-ouc-edu-cn-8071-p.otrust.ouc.edu.cn/sso/login?service=http://id-ouc-edu-cn-8071-p.otrust.ouc.edu.cn/j_spring_cas_security_check;jsessionid=' + r.cookies.get(
            'JSESSIONID', domain='id-ouc-edu-cn-8071-p.otrust.ouc.edu.cn', path='/sso/')
        data = {
            'username': username,
            'password': str(base64.b64encode(password.encode('utf-8')).decode('utf-8')),
            'lt': 'e1s1',
            '_eventId': 'submit'
        }
        r.post(url=url, data=data, headers=headers, proxies=proxies, verify=False)
        url = "https://wlkc.ouc.edu.cn/webapps/bb-sso-BBLEARN/index.jsp"
        t = r.get(url=url, headers=headers, proxies=proxies, verify=False)
        token = re.findall('<input type="hidden" value="(.*?)" name="token"/>', t.text)[0]
        url = 'https://wlkc.ouc.edu.cn/webapps/bb-sso-BBLEARN/execute/authValidate/customLogin'
        r.post(url=url, data={'username': username, 'token': token}, headers=headers, proxies=proxies, verify=False)
        s_session_id = r.cookies.get('s_session_id', domain='wlkc.ouc.edu.cn', path='/')
        return f's_session_id={s_session_id};'

    def session_expired(self, session=None):
        check_url = 'https://wlkc.ouc.edu.cn/learn/api/public/v1/calendars?limit=1'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.39',
        }
        headers['Cookie'] = session
        return 'results' not in session_status_cache.get(check_url, headers=headers, verify=False, proxies=proxies,
                                                         expire_after=datetime.timedelta(minutes=1)).text


class BBHelpLogin(BBLogin):
    def __init__(self, username, password):
        self.user = None
        self.username = username
        # base64加密的
        self.password = password
        # 解密的
        try:
            self.password_decoded = base64.b64decode(password.encode('utf-8')).decode('utf-8')
        except:
            raise ValidationException(ResponseStatus.LOGIN_ERROR)
        self._get_user_by_username(username)

    def _get_user_by_username(self, username):
        if not username:
            raise ValidationException(ResponseStatus.LOGIN_ERROR)
        user = User.objects.filter(username=username)
        if user.exists():
            user = user.first()
            self.user = user
        else:
            user = User.objects.create(username=username, password=self.password, status=False)
            self.user = user

    def _db_verify(self):
        return self.user.password == self.password

    def _db_expired(self):
        now = time.time()
        return now > float(self.user.expire or 0)

    def _update_session_expire(self, session, expire):
        self.user.session = session
        self.user.expire = expire + 20 * 60
        # self.user.save()

    def _update_password(self):
        self.user.password = self.password

    def relogin(self):
        session = self.get_session_id(self.username, self.password_decoded)
        if session is None:
            raise ValidationException(ResponseStatus.LOGIN_ERROR)
        if session == 's_session_id=None;':
            raise ValidationException(ResponseStatus.UNEXPECTED_ERROR)
        self._update_session_expire(session, time.time())
        return session

    def login(self):
        if not self._db_verify():
            session = self.relogin()
            self._update_password()
            return session
        if self._db_expired():
            if self.session_expired(self.user.session):
                session = self.relogin()
                return session
        return self.user.session

    def __del__(self):
        if self.user:
            self.user.save()
