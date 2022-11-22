import os
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
import base64
import requests


def encrypt(message):
    rsa_file = os.path.join(os.getcwd(), 'utils/publicKey.rsa')
    with open(rsa_file) as f:
        key = f.read()
        pub_key = RSA.importKey(str(key))
        cipher = PKCS1_cipher.new(pub_key)
        rsa_text = base64.b64encode(
            cipher.encrypt(bytes(message.encode("utf8"))))
        return rsa_text.decode('utf-8')


def login_by_my(username, password):
    r = requests.session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.39',
    }
    # proxies = {
    # "http": "http://192.168.3.193:8888",
    # "https": "http://192.168.3.193:8888"
    # }
    proxies = {
    "http": "socks5://127.0.0.1:1080",
    "https": "socks5://127.0.0.1:1080"
    }
    r.get('http://id.ouc.edu.cn:8071/sso/login?service=http%3A%2F%2Fmy.ouc.edu.cn%2Fuser%2FsimpleSSOLogin',
          headers=headers,proxies=proxies)
    data = {
        'username': username,
        'password': encrypt(password)
    }
    t = r.post('http://id.ouc.edu.cn:8071/sso/ssoLogin', data=data,proxies=proxies)
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
    r.post(url=url, data=data,proxies=proxies)
    # r.get(
    #     'http://id.ouc.edu.cn:8071/sso/login?service=https%3A%2F%2Fwlkc.ouc.edu.cn%2Fwebapps%2Fbb-sso-BBLEARN%2Findex.jsp')
    r.get('https://wlkc.ouc.edu.cn/webapps/bb-sso-BBLEARN/execute/authValidate/customLogin?returnUrl=https://wlkc.ouc.edu.cn/webapps/portal/execute/defaultTab&authProviderId=_104_1&uid=21020007057',proxies=proxies,verify=False)
    r.get('https://wlkc.ouc.edu.cn/webapps/bb-sso-BBLEARN/index.jsp', verify=False,proxies=proxies)
    s_session_id = r.cookies.get('s_session_id')
    # session_id = r.cookies.get('session_id')
    return f's_session_id={s_session_id};'
