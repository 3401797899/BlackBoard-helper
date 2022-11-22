from utils.response_status import ResponseStatus


class MyResponseStatus(ResponseStatus):
    LOGIN_ERROR = (40002, '账号或密码错误')
