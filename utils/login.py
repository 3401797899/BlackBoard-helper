import os
import datetime

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
import base64
import requests
from utils.http_by_proxies import proxies, get_by_proxies


def encrypt(message):
    rsa_file = os.path.join(os.getcwd(), 'utils/publicKey.rsa')
    with open(rsa_file) as f:
        key = f.read()
        pub_key = RSA.importKey(str(key))
        cipher = PKCS1_cipher.new(pub_key)
        rsa_text = base64.b64encode(
            cipher.encrypt(bytes(message.encode("utf8"))))
        return rsa_text.decode('utf-8')


def get_s_session_id(uid):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.39',
    }
    url = f'https://wlkc.ouc.edu.cn/webapps/bb-sso-BBLEARN/execute/authValidate/customLogin?returnUrl=https%3A%2F%2Fwlkc.ouc.edu.cn%2Fwebapps%2Fportal%2Fexecute%2FdefaultTab&authProviderId=_112_1&uid={uid}'
    r = requests.get(url=url, headers=headers, proxies=proxies, verify=False)
    s_session_id = r.cookies.get('s_session_id', domain='wlkc.ouc.edu.cn', path='/')
    if s_session_id is None:
        return None
    return f's_session_id={s_session_id};'


def verify_password(username, password):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.39',
    }
    data = {
        'username': username,
        'password': encrypt(password)
    }
    t = requests.post('http://id.ouc.edu.cn:8071/sso/ssoLogin', data=data, headers=headers, proxies=proxies,
                      verify=False)
    if not t.text == '{"state":true}':
        return False
    return True


def login_by_wlkc(username, password):
    session = get_s_session_id(username)
    if not verify_password(username, password) or session is None:
        return 'login failed'
    return session


def verify(session):
    return 'results' in get_by_proxies('https://wlkc.ouc.edu.cn/learn/api/public/v1/calendars?limit=1', session,
                                       expire_after=datetime.timedelta(minutes=10)).text


def login_by_my(username, password):
    r = requests.session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.39',
    }
    r.get(
        'http://id.ouc.edu.cn:8071/sso/login?service=https%3A%2F%2Fwlkc.ouc.edu.cn%2Fwebapps%2Fbb-sso-BBLEARN%2Findex.jsp',
        verify=False, headers=headers, proxies=proxies)
    data = {
        'username': username,
        'password': encrypt(password)
    }
    t = r.post('http://id.ouc.edu.cn:8071/sso/ssoLogin', data=data, headers=headers, proxies=proxies, verify=False)
    if not t.text == '{"state":true}':
        return 'login failed'
    url = 'http://id.ouc.edu.cn:8071/sso/login?service=http://id.ouc.edu.cn:8071/j_spring_cas_security_check;jsessionid=' + r.cookies.get(
        'JSESSIONID', domain='id.ouc.edu.cn', path='/sso/')
    data = {
        'username': username,
        'password': str(base64.b64encode(password.encode('utf-8')).decode('utf-8')),
        'lt': 'e1s1',
        '_eventId': 'submit'
    }
    r.post(url=url, data=data, headers=headers, proxies=proxies, verify=False)
    s_session_id = r.cookies.get('s_session_id', domain='wlkc.ouc.edu.cn', path='/')
    return f's_session_id={s_session_id};'
