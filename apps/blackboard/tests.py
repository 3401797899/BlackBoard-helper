from django.test import TestCase
from rest_framework.test import APIClient
import os

session = None


class LoginViewTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_1_login_success(self):
        global session
        url = '/login/'
        username = os.environ.get('BB_USERNAME')
        password = os.environ.get('BB_PASSWORD')
        data = {'username': username, 'password': password}
        response = self.client.post(url, data, format='json')
        print(response.data)

        self.assertTrue('data' in response.data)
        self.assertTrue('session_id' in response.data['data']['session'], msg='登录失败')
        session = response.data['data']['session']

    def test_get_class_list(self):
        self.assertIsNotNone(session, msg='Session为空')

        url = f'/api/classlist/?session={session}'
        response = self.client.get(url)

        self.assertTrue('data' in response.data)
        self.assertTrue(len(response.data['data']) > 0, msg='获取课程列表失败')

    def test_get_class_menu(self):
        self.assertIsNotNone(session, msg='Session为空')

        url = f'/api/classmenu/?session={session}&id=_25110_1'
        response = self.client.get(url)

        self.assertTrue('data' in response.data)
        self.assertTrue(len(response.data['data']) > 0, msg='获取课程菜单失败')

    def test_get_details(self):
        self.assertIsNotNone(session, msg='Session为空')

        url = f'/api/details/?session={session}&course_id=_25110_1&content_id=_979812_1'
        response = self.client.get(url)

        self.assertTrue('data' in response.data)
        self.assertTrue(len(response.data['data']) > 0, msg='获取课程详情失败')

    def test_get_announcements(self):
        self.assertIsNotNone(session, msg='Session为空')

        url = f'/api/announcements/?session={session}&course_id=_25110_1'
        response = self.client.get(url)

        self.assertTrue('data' in response.data)
        self.assertTrue(len(response.data['data']) > 0, msg='获取公告失败')

    def test_get_score(self):
        self.assertIsNotNone(session, msg='Session为空')

        url = f'/api/course_score/?session={session}&course_id=_25110_1'
        response = self.client.get(url)

        self.assertTrue('data' in response.data)
        self.assertTrue(len(response.data['data']) > 0, msg='获取成绩失败')

    def test_check_homework(self):
        self.assertIsNotNone(session, msg='Session为空')

        url = f'/api/check_homework/?session={session}&id=_157606_1'
        response = self.client.get(url)

        self.assertTrue('data' in response.data)
        self.assertTrue(response.data['data']['finished'], msg='获取作业失败')
