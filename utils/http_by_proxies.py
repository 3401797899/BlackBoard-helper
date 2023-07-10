import requests
import requests_cache, datetime
from requests import PreparedRequest
import hashlib

proxies = {
    # "http": "socks5://127.0.0.1:1080",
    # "https": "socks5://127.0.0.1:1080"
}
headers = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
    "Connection": "close"
}


def custom_key(request: PreparedRequest, **kwargs) -> str:
    return hashlib.md5((request.url + request.headers.get('Cookie', '')).encode(encoding='utf-8')).hexdigest()


cache = requests_cache.CachedSession('cache', allowable_methods=['GET', 'POST'], key_fn=custom_key,
                                     expire_after=datetime.timedelta(minutes=10))


def get_by_proxies(url, session='', **kwargs):
    headers.update({'Cookie': session})
    return cache.get(url, headers=headers, proxies=proxies, verify=False, **kwargs)


def post_by_proxies(url, session='', **kwargs):
    headers.update({'Cookie': session})
    return cache.post(url, headers=headers, proxies=proxies, verify=False, **kwargs)
