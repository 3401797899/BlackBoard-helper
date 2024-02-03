import json
import icalendar
import datetime
import time
import pytz
import requests
import logging
import asyncio
import aiohttp
import html

from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from django.db.models import F
from django_apscheduler.jobstores import DjangoJobStore, register_job
from django.core.cache import cache

from BlackBoard.settings import proxies
from utils.login import BBHelpLogin
from .get_data import check_homework, BBGetData, get_announcements
from utils.exception import ValidationException

# from blackboard.models import User, Homework

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), 'default')


def add_cache_count(name, count):
    # 记录数量
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    message_count = cache.get_or_set(name, {}, timeout=None)
    if not any([key.startswith(today) for key in message_count.keys()]):
        message_count = {}
    key = now.strftime('%Y-%m-%d %H')
    if key not in message_count:
        message_count[key] = 0
    message_count[key] += count
    cache.set(name, message_count, timeout=None)
    count_1 = cache.get_or_set(f"{name}_count", 0, timeout=None)
    cache.set(f"{name}_count", count_1 + count, timeout=None)


class BBHelpNotification:
    @staticmethod
    def extract_calendar_id_from_uid(uid):
        uid_parts = uid.split('-')
        if len(uid_parts) == 3:
            calendar_id = uid_parts[2]
            return calendar_id.split('@')[0]
        return None

    @staticmethod
    def parse_ics_data(ics_data):
        cal = icalendar.Calendar.from_ical(ics_data)

        events = []
        for component in cal.walk():
            if component.name == 'VEVENT':
                dtend = component.get('DTEND').dt
                summary = component.get('SUMMARY')
                uid = component.get('UID')
                calendar_id = BBHelpNotification.extract_calendar_id_from_uid(
                    uid)
                events.append({'dtend': dtend, 'summary': str(
                    summary), 'calendar_id': calendar_id})

        return events

    @staticmethod
    def _fetch_and_insert_homework(user):
        from blackboard.models import Homework
        if not user.ics_id or user.ics_id == 'guest':
            return
        url = f'https://wlkc.ouc.edu.cn/webapps/calendar/calendarFeed/{user.ics_id}/learn.ics'
        ics = requests.get(url).content
        events = BBHelpNotification.parse_ics_data(ics)
        now = datetime.datetime.now().astimezone(pytz.timezone('Asia/Shanghai'))
        events = [e for e in events if e['dtend'] > now]
        count = 0

        def delete_canceled_calendar(events, user):
            # 将删除的日程删除掉
            database_calendar = Homework.objects.filter(user=user).extra(
                where=[f'cast(`deadline` as DECIMAL) >= {now.timestamp()}']).values_list('calendar_id', flat=True)
            events_calendar = set([e['calendar_id'] for e in events])
            need_delete_events = set(database_calendar) - events_calendar

            if need_delete_events:
                for c_id in need_delete_events:
                    Homework.objects.filter(user=user, calendar_id=c_id).delete()
                    if c_id in events:
                        events.remove(c_id)
                logger.info(f'delete canceled events count : {len(need_delete_events)}')

        delete_canceled_calendar(events, user)

        for event in events:
            Homework.objects.update_or_create(calendar_id=event['calendar_id'], user=user, defaults={
                'name': html.unescape(event['summary']), 'deadline': event['dtend'].timestamp(),
            })
            count += 1

        add_cache_count('fetch_homework_count', count)
        logger.debug(f'Insert or Update {user.username}\'s {count} homeworks!')

    @staticmethod
    def fetch_and_insert_homework():
        from blackboard.models import User, Notify
        users = Notify.objects.filter(type='homework', open_status=True, count__gt=0, user__ics_id__isnull=False,
                                      user__open_id__isnull=False).exclude(user__ics_id='guest').values_list('user',
                                                                                                             flat=True)
        users = User.objects.filter(pk__in=users)
        for user in users:
            BBHelpNotification._fetch_and_insert_homework(user)
        logger.info(f'Insert {len(users)} users\' homeworks successfully!')

    @staticmethod
    async def fetch_ics_data(session, url):
        async with session.get(url) as response:
            return await response.read()

    @staticmethod
    async def async_fetch_and_insert_homework(user):

        from blackboard.models import Homework
        if not user.ics_id or user.ics_id == 'guest':
            return
        url = f'https://wlkc.ouc.edu.cn/webapps/calendar/calendarFeed/{user.ics_id}/learn.ics'
        async with aiohttp.ClientSession() as session:
            ics = await BBHelpNotification.fetch_ics_data(session, url)
        events = BBHelpNotification.parse_ics_data(ics)
        now = datetime.datetime.now().astimezone(pytz.timezone('Asia/Shanghai'))
        count = 0
        for event in events:
            if event['dtend'] > now:
                await Homework.objects.aupdate_or_create(calendar_id=event['calendar_id'], user=user, defaults={
                    'name': event['summary'], 'deadline': event['dtend'].timestamp(),
                })
                count += 1
        add_cache_count('fetch_homework_count', count)
        logger.debug(f'Insert or Update {user.username}\'s {count} homeworks!')
        return ics

    @staticmethod
    def get_open_notice_user():
        from blackboard.models import User
        users = User.objects.filter(status=True, subCount__gt=0, ics_id__isnull=False, open_id__isnull=False)
        return users

    @staticmethod
    async def fetch_and_insert_homeworks(users):
        logger.info('Fetch homeworks start!')
        try:
            async for user in users:
                await BBHelpNotification.async_fetch_and_insert_homework(user)
            logger.info(f'Insert homeworks successfully!')
        except Exception as e:
            logger.info(f"Insert homeworks error: {e}")

    @staticmethod
    def check_reminder(last_notice_time, deadline):
        current_time = time.time()

        # 计算距离截止时间的时间差
        time_diff = deadline - current_time

        # 判断是否需要提醒
        if time_diff <= 3 * 24 * 60 * 60:  # 三天内一天提醒一次
            # 获取当前日期的0点时间戳
            current_date = time.strftime(
                "%Y-%m-%d", time.localtime(current_time))
            current_date_start = int(time.mktime(
                time.strptime(current_date, "%Y-%m-%d")))

            # 判断今天是否还没提醒过
            if last_notice_time < current_date_start:
                return True

        if time_diff <= 24 * 60 * 60:  # 一天内
            # 判断是否需要第二次提醒
            if int(round(time_diff / 3600, 0)) in [1, 2, 8, 16]:
                return True
        return False

    @staticmethod
    def set_notice_time_and_sub_count(homework, now: float):
        homework.update_data('last_notice_time', now)
        from blackboard.models import Notify
        Notify.objects.filter(type='homework', user_id=homework.user_id).update(count=F('count') - 1)

    @staticmethod
    def update_course_name(homework):
        user = homework.user
        c_id = homework.calendar_id
        logger.debug(f'update {user.username}\'s course name')

        from blackboard.models import Homework
        try:
            session = BBHelpLogin(user.username, user.password).login()
        except ValidationException as e:
            # 密码错误
            if e.status.code == 40002:
                user.ics_id = None
                user.save()
            return 'error'

        url = 'https://wlkc.ouc.edu.cn/learn/api/public/v1/calendars/items'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.39',
            'Cookie': session
        }
        response = requests.get(url, headers=headers,
                                proxies=proxies, timeout=10).json()
        if 'results' not in response:
            return
        for each in response['results']:
            course_name = each['calendarName']
            if each['id'] == c_id:
                homework.update_data('course_name', course_name)
            calendar_id = each['id']
            Homework.objects.filter(calendar_id=calendar_id).update(
                course_name=course_name)
        # print(homework.course_name)

    @staticmethod
    def check_finished(homework):
        if homework.finished:
            return True
        try:
            session = BBHelpLogin(homework.user.username,
                                  homework.user.password).login(time_sleep=0)
        except ValidationException:
            return
        try:
            finished = check_homework(homework.calendar_id, session)['finished']
        except:
            logger.info(f"获取作业完成状态失败：{homework.name}，用户：{homework.user.username}")

        def _update_finished(homework, finished):
            if finished:
                homework.update_data('finished', finished)

        _update_finished(homework, finished)
        return finished

    @staticmethod
    def notify():
        from blackboard.models import Homework, Notify
        # 只获取user_id
        users = Notify.objects.filter(type='homework', open_status=True, count__gt=0,
                                      user__open_id__isnull=False).values_list('user_id', flat=True)
        # users = [1,]
        homeworks = Homework.objects.filter(user_id__in=users, finished=False).extra(
            where=[f'cast(`deadline` as DECIMAL) >= {time.time()}',
                   f'cast(`deadline` as DECIMAL) <= {time.time() + 3 * 24 * 60 * 60}']).order_by('user_id')
        count = 0
        now = time.time()
        for each in homeworks:
            logger.debug(f"Deal homework {each.name} deadline: {each.deadline}")
            # 判断是否需要提醒
            if BBHelpNotification.check_reminder(float(each.last_notice_time or 0), float(each.deadline)):
                # 只提醒没有完成的作业
                if not BBHelpNotification.check_finished(each):
                    # 获取课程名称
                    course_name = each.course_name
                    if course_name == '-':
                        if BBHelpNotification.update_course_name(each) == 'error':
                            continue
                        # print(each.course_name)
                    # 发送通知
                    access_token = WechatNotification.get_access_token()
                    if access_token:
                        count_now = WechatNotification.send_homework_message(each, access_token,
                                                                          each.course_name or '-') or 0
                        if count_now:
                            each.last_notice_time = now
                        count += count_now
                each.save()
        logger.info(f"成功提醒 {count} 作业!")

    @staticmethod
    def notify_score():
        now = time.time()
        from blackboard.models import Notify
        notifies = Notify.objects.filter(type='score', open_status=True, count__gt=0,
                                         user__open_id__isnull=False)
        count = 0
        for notify in notifies:
            result = BBGetData.get_score_list(BBHelpLogin(notify.user.username, notify.user.password).login())
            result = list(filter(lambda x: x['time'] >= float(notify.last_notice_time or 0) * 1000, result))
            if result:
                for each in result:
                    access_token = WechatNotification.get_access_token()
                    if access_token:
                        count += WechatNotification.send_score_message(access_token, notify.user, each, notify)
            notify.last_notice_time = now
            notify.save()
        logger.info(f"成功提醒 {count} 成绩!")

    @staticmethod
    def notice_notice():
        from blackboard.models import Notify
        notifies = Notify.objects.filter(type='notice', open_status=True, count__gt=0,
                                         user__open_id__isnull=False)
        count = 0
        for notify in notifies:
            result = get_announcements(BBHelpLogin(notify.user.username, notify.user.password).login(), '')
            result = list(filter(lambda x: x['time'] >= float(notify.last_notice_time or 0), result))
            if result:
                for each in result:
                    # print(each)
                    access_token = WechatNotification.get_access_token()
                    if access_token:
                        count += WechatNotification.send_notice_message(access_token, notify.user, each, notify)
            notify.last_notice_time = time.time()
            notify.save()
        logger.info(f"成功提醒{count}公告!")


class WechatNotification:
    @staticmethod
    def _send_message(access_token, data, type, user_id, notify):
        from blackboard.models import Notify
        url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"
        try:
            r = requests.post(url, data=json.dumps(data), timeout=2).json()
            # print(r)
        except:
            return 0
        if 'refuse' in r['errmsg']:
            notify.set_count(0)
            return 0
        notify.set_count(notify.count - 1)
        return 1

    @staticmethod
    def send_homework_message(homework, access_token, course_name):
        from blackboard.models import Notify
        notify = Notify.objects.get(user_id=homework.user_id, type='homework')
        logger.debug(
            f'Notice: user: {homework.user.username} homework: {homework.name} course: {course_name}')
        data = {
            "touser": homework.user.open_id,
            "template_id": settings.TEMPLATE_ID,
            "page": "pages/home/home",
            "data": {
                "thing1": {
                    "value": homework.name[:20]
                },
                "thing6": {
                    "value": course_name[:20]
                },
                "date3": {
                    "value": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(float(homework.deadline))))
                }
            }
        }
        count = WechatNotification._send_message(access_token, data, 'homework', homework.user_id, notify)
        notify.save()
        if count:
            logger.info(f"提醒用户 {homework.user.username} 作业： {homework.name} 成功！")
        return count

    @staticmethod
    def send_score_message(access_token, user, detail, notify):
        data = {
            "touser": user.open_id,
            "template_id": settings.SCORE_TEMPLATE_ID,
            "page": "pages/home/home",
            "data": {
                "thing4": {
                    "value": detail['course_name'][:20]
                },
                "thing27": {
                    "value": detail['name'][:20]
                },
                "number28": {
                    "value": f"{detail['score']} / {detail['total_score']}"
                },
                "time29": {
                    "value": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(float(detail['time']))))
                }
            }
        }
        count = WechatNotification._send_message(access_token, data, 'score', user.id, notify)
        if count:
            logger.info(f"提醒用户 {user.username} 课程成绩： {detail['name']} 成功！")
        return count

    @staticmethod
    def send_notice_message(access_token, user, detail, notify):
        data = {
            "touser": user.open_id,
            "template_id": settings.NOTICE_TEMPLATE_ID,
            "page": "pages/home/home",
            "data": {
                "thing1": {
                    "value": detail['title'][:20]
                },
                "thing4": {
                    "value": detail['author'][:20]
                },
                "date2": {
                    "value": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(float(detail['time']))))
                }
            }
        }
        count = WechatNotification._send_message(access_token, data, 'notice', user.id, notify)
        if count:
            logger.info(f"提醒用户 {user.username} 公告： {detail['title']} 成功！")
        return count

    @staticmethod
    def get_access_token():
        if token := cache.get('miniprogram_access_token'):
            return token
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={settings.APP_ID}&secret={settings.APP_SECRET}"
        r = requests.get(url, timeout=2).json()
        if 'errcode' in r:
            logger.info(f"获取小程序access_token错误，errcode:{r['errcode']}，message:{r['errmsg']}")
            return False
        cache.set('miniprogram_access_token', r['access_token'], timeout=r['expires_in'])
        return r['access_token']


@register_job(scheduler, 'interval', hours=6, id='fetchHomework', replace_existing=True,
              start_date='2022-12-08 15:30:00')
def fetchHomework():
    start = time.time()
    from blackboard.models import Notify
    count = Notify.objects.filter(type='homework', open_status=True, count__gt=0,
                                  user__open_id__isnull=False, user__ics_id__isnull=False).exclude(
        user__ics_id='guest').count()
    from django.db import close_old_connections
    close_old_connections()
    # from threading import Thread
    # def run_fetch():
    #     asyncio.run(BBHelpNotification.fetch_and_insert_homeworks(BBHelpNotification.get_open_notice_user()))
    # thread = Thread(target=run_fetch)
    # thread.start()
    BBHelpNotification.fetch_and_insert_homework()
    end = time.time()
    logger.info(f'Fetch {count} users\' homeworks finished! time : {end - start:.0f} s')


@register_job(scheduler, 'interval', hours=1, id='noticeUser', replace_existing=True, start_date='2022-12-08 16:00:00',
              max_instances=50)
def notify():
    hour = datetime.datetime.now().hour
    if 1 <= hour <= 5:
        return
    # 防止Error:
    # (2013, 'Lost connection to MySQL server during query')
    from django.db import close_old_connections
    close_old_connections()

    start_time = time.time()
    BBHelpNotification.notify()
    end_time = time.time()
    logger.info(f"提醒任务结束，耗时：{end_time - start_time:.0f}s")


# 注册事件


# fetchHomework()
# notify()
# scheduler.start()
# BBHelpNotification.notice_notice()
