import base64
import json
import datetime
import os
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_job, register_events
from lxml import etree
from django.conf import settings
from utils.http_by_proxies import cache
from utils.get_data import class_list
from blackboard.views import status_cache
from .models import User, Homework
import time
from utils.login import login_by_my
from utils.http_by_proxies import proxies, headers

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), 'default')


@register_job(scheduler, 'interval', minutes=10, id='clearCaches', replace_existing=True)
def clear_caches():
    cache.cache.delete(expired=True)
    class_list.cache.delete(expired=True)
    status_cache.cache.delete(expired=True)


def resize_one(name):
    import sqlite3
    cache = sqlite3.connect(os.path.join(settings.BASE_DIR, name))
    cache.cursor().execute('vacuum;')
    cache.commit()
    cache.close()


@register_job(scheduler, 'interval', days=1, id='resizeSQlite', replace_existing=True)
def resizeSQlite():
    CACHE_LIST = ['cache.sqlite', 'class_list.sqlite', 'status_cache.sqlite']
    [resize_one(t) for t in CACHE_LIST]


def check_homework_finished(calendar_id, session):
    _id = calendar_id
    url = f'https://wlkc.ouc.edu.cn/webapps/calendar/launch/attempt/_blackboard.platform.gradebook2.GradableItem-{_id}'
    headers.update({'Cookie': session})
    r = status_cache.get(url, headers=headers, verify=False, expire_after=datetime.timedelta(minutes=10))
    e = etree.HTML(r.text)
    if e.xpath("//input[@class='submit button-1' and @name='bottom_开始']"):
        return False
    if e.xpath("//input[@class='submit button-1' and @name='bottom_提交']"):
        return False
    else:
        return True


def update_session(user):
    now = time.time()
    session = user.session
    from utils.login import verify, login_by_wlkc
    if not verify(session):
        session = login_by_wlkc(user.username, base64.b64decode(user.password.encode('utf-8')).decode('utf-8'))
        if session == 'login failed':
            return
        user.session = session
        user.expire = time.time() + 15 * 60
        user.save()
    return session


def insert_homework_by_user(user):
    session = update_session(user)
    url = 'https://wlkc.ouc.edu.cn/learn/api/public/v1/calendars/items'
    headers.update({'Cookie': session})
    r = requests.get(url, headers=headers, proxies=proxies).json()
    for each in r['results']:
        name = each['title']
        course = each['calendarName']
        calendar_id = each['id']
        finished = False
        rtime = int(time.mktime(
            time.strptime(each['end'].replace('T', ' ').replace('Z', ''), "%Y-%m-%d %H:%M:%S.%f"))) + 8 * 3600
        homework = Homework.objects.filter(calendar_id=calendar_id, user_id=user.id)
        if homework.exists():
            if homework.first().finished:
                continue
            finished = check_homework_finished(calendar_id, session)
            homework.update(user_id=user.id, name=name, deadline=rtime, finished=finished, calendar_id=calendar_id,
                            course_name=course)
        else:
            Homework.objects.create(
                user_id=user.id, name=name, deadline=rtime, finished=finished, calendar_id=calendar_id,
                course_name=course)
    # Homework.objects.bulk_update(homeworks, fields=['finished', 'deadline', 'name', 'course_name'])


def notice_user_homework(homework, access_token):
    url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"
    # data = {
    #     "touser": homework.user.open_id,
    #     "template_id": settings.TEMPLATE_ID,
    #     "page": "pages/home/home",
    #     "data": {
    #         "thing1": {
    #             "value": homework.name
    #         },
    #         "thing6": {
    #             "value": homework.course_name
    #         },
    #         "date3": {
    #             "value": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(homework.deadline)))
    #         }
    #     }
    # }
    data = {
        "touser": homework.user.open_id,
        "template_id": settings.TEMPLATE_ID,
        "page": "pages/home/home",
        "data": {
            "thing1": {
                "value": homework.name
            },
            "thing4": {
                "value": homework.course_name
            },
            "time2": {
                "value": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(homework.deadline)))
            },
            "phrase5": {
                "value": "未提交"
            },
            "thing6": {
                "value": homework.user.username
            }
        }
    }
    r = requests.post(url, data=json.dumps(data)).json()
    print(homework.user.username, r)
    if r['errcode'] == 0:
        homework.last_notice_time = time.time()
        user = homework.user
        user.subCount -= 1
        user.save()
        homework.save()


def notice_user():
    homeworks = Homework.objects.filter(finished=False, user__status=True, user__subCount__gt=0).extra(
        where=[f'cast(`deadline` as DECIMAL) >= {time.time()}']).select_related('user')
    now = time.time()
    for each in homeworks:
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={settings.APP_ID}&secret={settings.APP_SECRET}"
        r = requests.get(url).json()
        access_token = r['access_token']
        interval = float(each.deadline) - now
        try:
            notice_interval = now - float(each.last_notice_time)
        except:
            notice_interval = 3600 * 24 * 30
        if interval < 3600 * 24 * 3:
            if interval < 3600 * 6:
                if notice_interval > 2 * 3600:
                    notice_user_homework(each, access_token)
                else:
                    continue
            else:
                if notice_interval > 3600 * 24:
                    notice_user_homework(each, access_token)


@register_job(scheduler, 'interval', hours=1, id='noticeUser', replace_existing=True, start_date='2022-12-08 16:00:00')
def update_calendar():
    users = User.objects.filter(status=True, subCount__gt=0)
    for user in users:
        insert_homework_by_user(user)
    notice_user()


scheduler.start()
