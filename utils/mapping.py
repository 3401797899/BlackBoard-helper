"""
效仿 Spring 的注解, 基于 @action 封装了一些更加常用装饰器
@get_mapping
@post_mapping
@put_mapping
@delete_mapping
!不要将一个 URL 的同一种请求(GET, POST)映射到两个不同的函数上
"""

from functools import wraps

from rest_framework.decorators import action
import requests
from utils.response import Response
from utils.response_status import ResponseStatus


def get_mapping(value: str, detail: bool = False):
    """
    该装饰器装饰的函数会映射到 URL {value}/ 的 GET 方法上
    :param value: url 路径片段
    :param detail: 是否是含参数的 URL
    """

    def decorator(func):
        @action(methods=["GET"], url_path=value, detail=detail)
        @wraps(func)
        def wrapper_function(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper_function

    return decorator


def post_mapping(value: str, detail: bool = False):
    """
    该装饰器装饰的函数会映射到 URL {value}/ 的 POST 方法上
    """

    def decorator(func):
        @action(methods=["POST"], url_path=value, detail=detail)
        @wraps(func)
        def wrapper_function(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper_function

    return decorator


def delete_mapping(value: str, detail: bool = False):
    """
    该装饰器装饰的函数会映射到 URL {value}/ 的 DELETE 方法上
    """

    def decorator(func):
        @action(methods=["DELETE"], url_path=value, detail=detail)
        @wraps(func)
        def wrapper_function(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper_function

    return decorator


def put_mapping(value: str, detail: bool = False):
    """
    该装饰器装饰的函数会映射到 URL {value}/ 的 PUT 方法上
    """

    def decorator(func):
        @action(methods=["PUT"], url_path=value, detail=detail)
        @wraps(func)
        def wrapper_function(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper_function

    return decorator
