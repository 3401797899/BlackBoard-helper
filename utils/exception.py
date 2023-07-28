"""
自定义异常类
"""
from utils.response_status import ResponseStatus


class ValidationException(Exception):
    """
    ValidationException 字段验证错误包装类

    ValidationException 对象中 status 属性为响应状态的枚举
    """

    def __init__(self, status: ResponseStatus) -> None:
        """
        :param status: 返回的状态类
        """
        self.status = status
