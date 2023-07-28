import hashlib
import re

from requests_cache import CachedSession


def key_func(*, request, **kwargs):
    path = request.path
    data = str(request.data)
    params = str(request.query_params)
    return hashlib.md5((path + params + data).encode(encoding='utf-8')).hexdigest()


def custom_key(request, **kwargs):
    cookie = request.headers.get('Cookie', '')
    session = re.search('s_session_id=(.+?);', cookie)
    if session:
        return session.group(1)
    else:
        return ''


session_status_cache = CachedSession('session_cache', key_fn=custom_key)
