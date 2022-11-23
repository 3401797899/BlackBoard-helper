"""
自动化收集 View 中的类并根据 `base_url_path`, `base_url_name` 生成对应的 URL
使用时要求符合以下规范:
    1. 所有的 app 放在 'apps' 目录下, 该目录和项目在根目录下
    2. 只收集 app.{app_name}.views 中继承 ViewSetPlus 或者 APIViewPlus 的类
    3. 如果不设置 `base_url_path`, `base_url_name`, `url_pattern` 的值, 会默认使用类名的小写字母作为默认值
"""

from pathlib import Path
from typing import Type, Tuple, ClassVar
from importlib import import_module
from inspect import getmembers, isclass

from django.urls import path
from rest_framework.routers import SimpleRouter

from .api_view import ViewSetPlus
import os


def load_object(package_path: str) -> Tuple[str, object]:
    """
    :param package_path:
    :return:
    """
    try:
        dot = package_path.rindex('.')
    except ValueError:
        raise ValueError("Error loading object '%s': not a full path" % package_path)
    module, name = package_path[:dot], package_path[dot + 1:]
    mod = import_module(module)
    try:
        obj = getattr(mod, name)
    except AttributeError:
        raise NameError("Module '%s' doesn't define any object named '%s'" % (module, name))
    return name, obj


class RouterBuilder:

    def __init__(self, trailing_slash=True):
        print("========== RouterBuilder: V0.2 ==========")
        print("Created By ITStudio, All rights reserved")
        print("== Start auto build router")
        self.router = SimpleRouter(trailing_slash)
        self.slash = '/' if trailing_slash else ''
        self.url_patterns = []
        self._auto_collect()
        print("== auto build finished")
        print()

    def _auto_collect(self):
        """
        自动收集 app 中的 views.py 里的类, 如果符合规范就自动构建 URL
        :return None
        """
        project_dir_path = Path(__file__).resolve().parent.parent
        project_dir = os.listdir(project_dir_path)
        print("RouterBuilder run in project's path: {}".format(project_dir_path))
        if "apps" not in project_dir:
            raise FileNotFoundError("Can't find 'apps' directory")
        apps_dir = os.path.join(project_dir_path, "apps")
        for app_name in os.listdir(apps_dir):
            views_file_path = os.path.join(apps_dir, app_name)
            views_file_path = os.path.join(views_file_path, "views.py")
            if not os.path.isfile(views_file_path):
                # ignore files like __init__.py or dictionary like __pycache__
                continue
            # if you want to import a .py from module, use `fromlist` !!
            views_module = __import__("apps.{}.views".format(app_name), fromlist=('views',))
            for one in getmembers(views_module):
                if isclass(one[1]):
                    clazz = "apps.{}.views.{}".format(app_name, one[0])
                    self._add_clazz(clazz)

    def collect(self, app_name: str, filename: str):
        """
        提供一个手动添加文件进行自动构建路由的入口
        """
        views_module = __import__("apps.{}.{}".format(app_name, filename), fromlist=(filename,))
        for one in getmembers(views_module):
            if isclass(one[1]):
                clazz = "apps.{}.{}.{}".format(app_name, filename, one[0])
                self._add_clazz(clazz)

    def _add_class(self, view_set: Type[ViewSetPlus]):
        """
        添加一个 View 类到 RouterBuilder 中并生成对应的 URL
        :param view_set: View 类
        :return None
        """
        if not view_set.base_url_path:
            url_path = str(view_set.__name__).lower()
        elif view_set.base_url_path == '/':
            url_path = ''
        else:
            url_path = view_set.base_url_path
        if not view_set.base_url_name:
            url_name = str(view_set.__name__).lower()
        else:
            url_name = view_set.base_url_name
        if view_set.as_api_view:
            if view_set.url_pattern:
                url_pattern = view_set.url_pattern
            else:
                url_pattern = url_path
            self.url_patterns.append(
                path(r"{}{}".format(url_pattern, self.slash), view_set.as_view({
                    "get": "get",
                    "post": "post",
                    "delete": "delete",
                    "put": "put"
                }))
            )
            print("auto add urlPatterns: {}, corresponding Class: {}".format(
                url_pattern, view_set.__name__))
        else:
            self.router.register(
                r"{}".format(url_path),
                view_set,
                url_name
            )
            print("auto add router: {}, corresponding Class: {}".format(
                view_set.base_url_path, view_set.__name__))

    def _add_clazz(self, clazz_path: str):
        """
        添加一个类的包路径到 RouterBuilder 中并基于反射生成对应的 URL
        :param clazz_path:
        :return None
        """
        name, clazz = load_object(clazz_path)
        # ignore the base class itself
        if name == "ViewSetPlus" or name == "APIViewPlus":
            return
        if issubclass(clazz, ViewSetPlus):
            self._add_class(clazz)
        else:
            # print(
            #     "Class {} may not be the subclass of RestfulViewSet, "
            #     "it will be ignored in building router".format(name)
            # )
            return

    @property
    def urls(self):
        return self.router.urls