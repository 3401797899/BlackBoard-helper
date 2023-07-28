import traceback
import re

from rest_framework.exceptions import MethodNotAllowed
from rest_framework.viewsets import ViewSet
from django.conf import settings

from .response import Response
from .response_status import ResponseStatus
from .exception import ValidationException


class ViewSetPlus(ViewSet):
    """
    增强 ViewSet 的功能, 增加 URL 的定义相关字段和自定义的异常类型
    :param base_url_path: URL 根路径, 所有 ViewSet 下 mapping 修饰器都会自动在 URL 最开始增加该路径
    :param base_url_name: URL 的别名, 用于后端跳转场景
    :param url_pattern: 在 `urlpatterns` 中注册使用的 URL 匹配路径
    :param as_api_view: 接口注册 URL 的形式,
                      True: 以 APIView 的形式在 `urlpatterns` 中添加
                      False: 在 drf 的 router 里注册
    """
    base_url_path = ""
    base_url_name = ""
    url_pattern = ""

    as_api_view = False

    def handle_exception(self, exc) -> Response:
        """
        对异常的处理函数进行封装, 打印异常信息并给前端返回对应的提示信息
        :param exc: 异常
        :return Response: 自定义的返回类, 见 .response.Response
        """
        # TODO:添加错误信息显示在控制台或者使用日志记录
        # print(exc)
        # logger.error(exc)

        debug = getattr(settings, 'DEBUG', True)
        debug_level = getattr(settings, 'DEBUG_LEVEL', 'console')

        if debug:
            if debug_level == 'console':
                # 报错定位不准，放弃了
                # file = exc.__traceback__.tb_frame.f_globals["__file__"]
                # line = exc.__traceback__.tb_lineno
                e = "".join(traceback.format_exception(
                    *(type(exc), exc, exc.__traceback__)))
                pattern = re.compile(r'File \"(.*)\", line (\d+),')
                exception = re.findall(pattern, e)[-1]
                print(
                    f'\033[1;31m[Error] {exc} in file "{exception[0]}" , line {exception[1]}\033[0m')
            elif debug_level == 'default':
                # 默认报错
                traceback.print_exc()
            else:
                pass

        if isinstance(exc, MethodNotAllowed):
            return Response(ResponseStatus.METHOD_NOT_ALLOWED_ERROR)

        if isinstance(exc, ValidationException):
            return Response(exc.status)

        return Response(ResponseStatus.UNEXPECTED_ERROR)


class APIViewPlus(ViewSetPlus):
    """
    支持 APIView 的写法, 实现默认的 get, post, delete 等处理函数便于 URL 的绑定
    """
    as_api_view = True

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="GET")

    def post(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="POST")

    def put(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="PUT")

    def patch(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="PATCH")

    def delete(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="DELETE")

    def head(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="HEAD")

    def options(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="OPTIONS")

    def trace(self, request, *args, **kwargs):
        raise MethodNotAllowed(method="TRACE")
