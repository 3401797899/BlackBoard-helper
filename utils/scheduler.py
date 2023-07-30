import json
import icalendar
import datetime
import time
import pytz
import requests
import logging

from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_job

from BlackBoard.settings import proxies
from utils.login import BBHelpLogin
from .get_data import check_homework

# from blackboard.models import User, Homework
logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), 'default')


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
                calendar_id = BBHelpNotification.extract_calendar_id_from_uid(uid)
                events.append({'dtend': dtend, 'summary': str(summary), 'calendar_id': calendar_id})

        return events

    @staticmethod
    def _fetch_and_insert_homework(user):
        from blackboard.models import Homework
        url = f'https://wlkc.ouc.edu.cn/webapps/calendar/calendarFeed/{user.ics_id}/learn.ics'
        ics = requests.get(url).content
        events = BBHelpNotification.parse_ics_data(ics)
        now = datetime.datetime.now().astimezone(pytz.timezone('Asia/Shanghai'))
        count = 0
        for event in events:
            if event['dtend'] > now:
                Homework.objects.update_or_create(calendar_id=event['calendar_id'], defaults={
                    'user': user, 'name': event['summary'],
                    'deadline': event['dtend'].timestamp(),
                })
                count += 1
        logger.debug(f'Insert {user.username}\'s {count} homeworks!')

    @staticmethod
    def fetch_and_insert_homework():
        from blackboard.models import User
        users = User.objects.filter(status=True, subCount__gt=0)
        for user in users:
            BBHelpNotification._fetch_and_insert_homework(user)
        logger.info(f'Insert {len(users)} users\' homeworks successfully!')

    @staticmethod
    def check_reminder(last_notice_time, deadline):
        current_time = time.time()

        # 计算距离截止时间的时间差
        time_diff = deadline - current_time

        # 判断是否需要提醒
        if time_diff <= 5 * 24 * 60 * 60:  # 五天内一天提醒一次
            # 获取当前日期的0点时间戳
            current_date = time.strftime("%Y-%m-%d", time.localtime(current_time))
            current_date_start = int(time.mktime(time.strptime(current_date, "%Y-%m-%d")))

            # 判断今天是否还没提醒过
            if last_notice_time < current_date_start:
                return True

        if time_diff <= 24 * 60 * 60:  # 一天内
            # 判断是否需要第二次提醒
            if int(round(time_diff / 3600, 0)) in [8, 16]:
                return True
        return False

    @staticmethod
    def set_notice_time_and_sub_count(homework, now: float):
        homework.last_notice_time = now
        homework.user.subCount -= 1
        homework.user.save()
        homework.save()

    @staticmethod
    def update_course_name(user):
        logger.debug(f'update {user.username}\'s course name')
        from blackboard.models import Homework
        session = BBHelpLogin(user.username, user.password).login()
        url = 'https://wlkc.ouc.edu.cn/learn/api/public/v1/calendars/items'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.39',
            'Cookie': session
        }
        response = requests.get(url, headers=headers, proxies=proxies, timeout=2).json()
        if 'results' not in response:
            return None
        first_course = None
        flag = False
        for each in response['results']:
            course_name = each['calendarName']
            if not flag:
                first_course = course_name
                flag = True
            calendar_id = each['id']
            Homework.objects.filter(calendar_id=calendar_id).update(course_name=course_name or '个人')
        return first_course

    @staticmethod
    def check_finished(homework):
        if homework.finished:
            return True
        session = BBHelpLogin(homework.user.username, homework.user.password).login()
        return check_homework(homework.calendar_id, session)['finished']

    @staticmethod
    def notify():
        from blackboard.models import Homework
        homeworks = Homework.objects.filter(user__status=True, user__subCount__gt=0).extra(
            where=[f'cast(`deadline` as DECIMAL) >= {time.time()}']).select_related('user')
        now = time.time()
        count = 0
        for each in homeworks:
            if BBHelpNotification.check_reminder(float(each.last_notice_time or 0), float(each.deadline)):
                if not BBHelpNotification.check_finished(each):
                    # 获取课程名称
                    course_name = each.course_name
                    if course_name == '-':
                        course_name = BBHelpNotification.update_course_name(each.user)

                    logger.debug(f'Notice: user: {each.user.username} homework: {each.name} course: {each.course_name}')
                    access_token = WechatNotification.get_access_token()
                    if access_token:
                        WechatNotification.send_message(each, access_token, course_name or '-')
                        BBHelpNotification.set_notice_time_and_sub_count(each, now)
                        count += 1
        logger.info(f"Notice {count} homeworks successfully!")


class WechatNotification:
    @staticmethod
    def send_message(homework, access_token, course_name):
        url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"
        data = {
            "touser": homework.user.open_id,
            "template_id": settings.TEMPLATE_ID,
            "page": "pages/home/home",
            "data": {
                "thing1": {
                    "value": homework.name
                },
                "thing6": {
                    "value": course_name
                },
                "date3": {
                    "value": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(float(homework.deadline))))
                }
            }
        }
        try:
            r = requests.post(url, data=json.dumps(data), timeout=2).json()
        except:
            logger.debug(f'notice {homework.user.username}\'s {homework.name} error!')
            return
        if r['errcode'] == 0:
            homework.last_notice_time = time.time()
            user = homework.user
            user.subCount -= 1
            user.save()
            homework.save()

    @staticmethod
    def get_access_token():
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={settings.APP_ID}&secret={settings.APP_SECRET}"
        try:
            r = requests.get(url, timeout=2).json()
        except:
            logger.debug('get access token error!')
            return None
        return 'access_token' in r and r['access_token']


@register_job(scheduler, 'interval', hours=24, id='fetchHomework', replace_existing=True,
              start_date='2022-12-08 15:30:00')
def fetchHomework():
    logger.info('Fetch homeworks start!')
    BBHelpNotification.fetch_and_insert_homework()
    logger.info('Fetch homeworks finished!')


@register_job(scheduler, 'interval', hours=1, id='noticeUser', replace_existing=True, start_date='2022-12-08 16:00:00')
def notify():
    logger.info('Notice user start!')
    BBHelpNotification.notify()
    logger.info('Notice user finished!')


# fetchHomework()
# notify()
scheduler.start()
