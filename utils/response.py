import json

from django.http import HttpResponse

from utils.response_status import ResponseStatus


class Response(HttpResponse):
    """
    HttpResponse 的包装类
    将响应状态 status 与响应数据 data 生成 JSON 格式的响应内容
    其中如果 status 不存在或类型错误, 则以意外错误作为响应状态

    Example:
        return Response(ResponseStatus.OK)

        data = {'key': 'value'}
        return Response(ResponseStatus.OK, data)
    """
    def __init__(self, status: ResponseStatus, data=None):
        """

        :param status: 返回的状态类
        :param data: 返回的数据
        """
        content = {}

        if not status or not isinstance(status, ResponseStatus):
            status = ResponseStatus.UNEXPECTED_ERROR

        content['code'] = status.code
        content['msg'] = status.msg

        if status == ResponseStatus.OK and data is not None:
            content['data'] = data

        content = json.dumps(content)

        super().__init__(content=content,
                         content_type='application/json',
                         status=200,
                         charset='utf-8')
