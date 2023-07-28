# BB平台助手API

BB平台助手API是基于Django实现的针对中国海洋大学海大云学堂（本科BB平台）的一系列API，用于OUC-SRDP项目BB平台助手。

## 接口文档

### 本程序接口文档(APIFOX)： 

链接: https://apifox.com/apidoc/shared-69754f2a-9682-4f50-b25e-339e58a5f2c2

访问密码 : 8hDjDuIg

### BlackBoard官方API：

https://developer.blackboard.com/portal/displayApi


## 已实现功能

- [x] 登录
- [x] 获取课程列表
- [x] 获取课程菜单
- [x] 获取课程内容详细页
- [x] 获取课程公告
- [x] 获取课程成绩
- [x] 获取课程单个成绩详细提交记录
- [x] 获取课程公告
- [x] 提交作业
- [x] 作业ddl通知
- [x] 获取作业是否完成

## 部署

### 环境

Python3.7+ 和 Mysql数据库【如果使用其他数据库请在settings.py中修改】

### API部署

1. 克隆本仓库 / 下载本仓库代码，并进入代码目录

2. 安装依赖

   ```bash
   pip install -r requirements.txt
   ```

3. 修改config.json中的配置信息

   ```js
   {
     "APP_ID": "", // 微信小程序APP_ID
     "APP_SECRET": "", // 微信小程序APP_SECRET
     "TEMPLATE_ID": "", // 微信小程序消息TEMPLATE_ID
     "MYSQL_NAME": "bbhepler", // 数据库名称
     "MYSQL_HOST": "localhost", // 数据库地址
     "MYSQL_USER": "root", // 数据库用户
     "MYSQL_PASS": "123456", // 数据库密码
     "MYSQL_PORT": 3306, // 数据库端口
     "SECRET_KEY": "", // Django SECRET_KEY，随机字符串
     "NOTICE_HOMEWORK_DEADLINE": false // 是否开启作业提醒功能
   }
   ```

4. 初始化数据库

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. 启动服务

   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

6. 访问 http://127.0.0.1:8000/ 即可看到页面。

## Bugs

如果发现Bug或有其他想要的功能，欢迎通过Issue进行提出。也欢迎大家提交PR共同维护这个项目。

## License

Copyright Bai, 2022.
