from django.db import models
from dirtyfields import DirtyFieldsMixin


# Create your models here.
class User(DirtyFieldsMixin, models.Model):
    username = models.CharField(verbose_name='学号', max_length=100)
    password = models.CharField(verbose_name='base64加密密码', max_length=100, null=True)
    session = models.CharField(verbose_name='最后一次登录的session', max_length=150)
    expire = models.CharField(verbose_name='session过期的时间戳', max_length=50)
    open_id = models.CharField(verbose_name='微信小程序open_id', max_length=255, null=True)
    # status = models.BooleanField(verbose_name='通知是否开启', default=False)
    # subCount = models.IntegerField(verbose_name='剩余通知次数', default=0)
    ics_id = models.CharField(verbose_name='BB平台日历ics_id', max_length=255, null=True, default=None)
    token = models.CharField(verbose_name='BB平台Token', max_length=255, default=None, null=True)
    created_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        db_table = 'users'


class Notify(models.Model):
    notify_type = (
        ('homework', '作业'),
        ('score', '成绩'),
        ('notice', '公告'),
    )

    user = models.ForeignKey(User, verbose_name='所属用户', on_delete=models.CASCADE)
    type = models.CharField(verbose_name='通知类型', max_length=20, choices=notify_type)
    count = models.IntegerField(verbose_name='通知次数', default=0)
    last_notice_time = models.CharField(verbose_name="上次提醒时间", max_length=255, default='0')
    open_status = models.BooleanField(verbose_name='是否开启', default=False)
    
    def set_count(self, count):
        self.count = count
    
    class Meta:
        verbose_name = '通知'
        verbose_name_plural = verbose_name
        db_table = 'notifies'


class Homework(models.Model):
    user = models.ForeignKey(User, verbose_name='所属用户', on_delete=models.CASCADE)
    name = models.CharField(verbose_name='作业名称', max_length=255)
    course_name = models.CharField(verbose_name='课程名称', max_length=255, default='-')
    deadline = models.CharField(verbose_name='截至时间', max_length=200)
    finished = models.BooleanField(verbose_name='是否完成', default=False)
    calendar_id = models.CharField(verbose_name='calendar_id', max_length=100)
    last_notice_time = models.CharField(verbose_name="上次提醒时间", max_length=255)
    created_time = models.DateTimeField(auto_now_add=True)

    def update_data(self, key, value):
        self.__dict__[key] = value

    class Meta:
        verbose_name = '作业'
        verbose_name_plural = verbose_name
        db_table = 'homeworks'
