import re
import requests
import time
import logging

from lxml import etree
from lxml.html.clean import Cleaner

from BlackBoard.settings import proxies

logger = logging.getLogger("utils.scheduler")

headers = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36"
}

def _gen_cookie_dict(cookie: str) -> dict:
    cookies = {}
    key, value = cookie.split('=', 1)
    cookies[key] = value[:-1]
    return cookies

def get_class_list(cookie: str) -> dict:
    """
    获取课程列表
    :param cookie: Cookie
    :return: {}
    """
    url = 'https://wlkc.ouc.edu.cn/webapps/portal/execute/tabs/tabAction'
    data = {
        'action': 'refreshAjaxModule',
        'modId': '_22_1',
        'tabId': '_1_1',
        'tab_tab_group_id': '_1_1'
    }
    cookies = _gen_cookie_dict(cookie)
    r = requests.post(url=url, data=data, headers=headers, cookies=cookies, proxies=proxies, verify=False)
    e = etree.HTML(r.text)
    li_s = e.xpath('//li')
    data_list = []
    for li in li_s:
        course_name = li.find('a').text  # 例如：2021Q080502101247-2005177: 计算机科学与技术导论
        teacher = "".join(
            [_.text.replace('\xa0', '') for _ in li.findall('div[@class="courseInformation"]/span[@class="name"]')])
        # 忽略自己添加的课程
        course_id = re.search('id=(_.*?)&', li.find('a').attrib['href'].replace(' ', ''))
        if course_id:
            course_id = course_id.group(1)
            data_list.append({'name': course_name, 'teacher': teacher,
                              'id': course_id})

    # 按学期分类
    data = dict()
    for each in data_list:
        course_name = each['name'].split()
        if len(course_name) > 1:
            # 获取课程名称，删除课程编号
            course_name = course_name[-1]
        else:
            # 处理未开启课程编号的情况，全部放入未指定学期
            if '未指定学期' not in data:
                data['未指定学期'] = []
            data['未指定学期'].append({
                'name': course_name[-1], 'teacher': each['teacher'], 'id': each['id']
            })
            continue
        year = each['name'][:5]
        if year not in data.keys():
            data[year] = []
        data[year].append({'name': course_name, 'teacher': each['teacher'], 'id': each['id']})
    s = ['C', 'X', 'Q', '期']  # 期为未指定学期
    # 将学期排序
    result = sorted(data.items(), key=lambda x: x[0][:4] + str(s.index(x[0][-1])), reverse=True)
    return dict(result)


def get_class_detail_by_id(id: str, cookie: str) -> list:
    """
    获取某一课程的列表
    :param url: 课程url
    :param cookie: Cookie
    :return: []
    """
    url = "https://wlkc.ouc.edu.cn/webapps/blackboard/execute/launcher?type=Course&id=" + id + "&url="
    cookies = _gen_cookie_dict(cookie)
    r = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False)
    r.encoding = 'utf-8'
    data = []
    e = etree.HTML(r.text)
    li_s = e.xpath("//ul[@class='courseMenu']/li[not(contains(@class,'divider'))]")
    for li in li_s:
        if 'subhead' in li.attrib['class']:
            data.append({"name": li.find('h3/span').text, "type": "subhead"})
            continue
        a = li.find('a')
        text = a.find('span').text
        link = a.attrib['href']
        content_id = re.search('content_id=(.*?)&', link)
        if content_id:
            data.append({"name": text, "type": "content", "id": content_id.group(1)})
            continue
        tool_id = re.search('tool_id=(.*?)&', link)
        if tool_id and tool_id.group(1) == "_136_1":
            data.append({"name": text, "type": "announcement"})
    return data


def get_content_by_id(course_id: str, content_id: str, cookie: str) -> list:
    """
    通过content_id获取获取内容
    :param course_id: 课程id
    :param content_id: 内容id
    :param cookie: session
    :return: []
    """
    url = f'https://wlkc.ouc.edu.cn/webapps/blackboard/content/listContent.jsp?course_id={course_id}&content_id={content_id}'
    cookies = _gen_cookie_dict(cookie)
    t = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False)
    cleaner = Cleaner()
    cleaner.javascript = True
    html = cleaner.clean_html(t.text)
    e = etree.HTML(html)
    data = []
    li_s = e.xpath("//ul[@class='contentList']/li")
    for li in li_s:
        name = li.find('div[@class="item clearfix"]/h3').xpath("string(.)").replace('\n', '').replace(' ', '')
        d = {"name": name, "details": {}}
        _content_id = li.find('div[@class="item clearfix"]/h3/a')
        if _content_id is not None:
            href = _content_id.attrib['href']
            _content_id = re.search('content_id=_(.*?_1)', href)
            if _content_id and _content_id.group(1) != content_id:
                id_type = "content"
                if "uploadAssignment" in href:
                    id_type = "homework"
                d = {"name": name, "id": _content_id.group(1), "type": id_type, "details": {}}
            else:
                d['details']['file'] = [
                    {
                        "name": name,
                        "href": "https://wlkc.ouc.edu.cn" + href
                    }
                ]
        t = li.find('div[@class="details"]')
        if t is not None:
            text = t.find('div[@class="vtbegenerated"]')
            if text is not None:
                d['details']['text'] = etree.tostring(text, encoding='utf-8').decode('utf-8')
            file = t.find('div[@class="contextItemDetailsHeaders clearfix"]')
            if file is not None:
                if "file" not in d["details"].keys():
                    d['details']['file'] = list()
                f = file.findall('.//ul[@class="attachments clearfix"]/li')
                for each in f:
                    a = each.find('a')
                    d['details']['file'].append(
                        {"name": a.xpath('string(.)'), "href": "https://wlkc.ouc.edu.cn" + a.attrib['href']})
        data.append(d)
    return data


def get_class_score(course_id: str, cookie: str) -> list:
    url = f'https://wlkc.ouc.edu.cn/webapps/bb-mygrades-BBLEARN/myGrades?course_id={course_id}&stream_name=mygrades'
    cookies = _gen_cookie_dict(cookie)
    t = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False)
    e = etree.HTML(t.text)
    data = []
    li_s = e.xpath("//div[@id='grades_wrapper']/div")
    for li in li_s:
        inf = {
            'score': li.findtext("div[@class='cell grade']/span[@class='grade']"),
            'class_type': li.attrib['class'].replace('sortable_item_row', '').replace('row expanded', '').strip(),
            'lastactivity': li.attrib['lastactivity'][:-3],
            'duedate': li.attrib['duedate'][:-3]
        }
        if inf['class_type'] == 'graded_item_row' or inf['class_type'] == 'submitted_item_row' or inf[
            'class_type'] == '':
            # 可点击的标题
            title = li.find('./div[@class="cell gradable"]/a')
            inf['title'] = title.text.strip()
            inf['column_id'] = title.attrib['id']
            if 'id' not in title.attrib:
                inf['title'] = li.findtext('./div[@class="cell gradable"]/span')
        elif inf['class_type'] == 'calculatedRow' or inf['class_type'] == 'upcoming_item_row':
            inf['title'] = li.findtext('./div[@class="cell gradable"]/span').strip()
        else:
            raise Exception
        totlescore = li.findtext('./div/span[@class="pointsPossible clearfloats"]')
        inf['totlescore'] = totlescore.strip('/') if totlescore else ""  # 有总分返回总分，没有返回空串
        data.append(inf)
    return data


def get_announcements(cookie: str, course_id: str) -> list:
    url = "https://wlkc.ouc.edu.cn/webapps/blackboard/execute/announcement?method=search&viewChoice=2&course_id=" + course_id
    cookies = _gen_cookie_dict(cookie)
    s = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False).text
    cleaner = Cleaner()
    cleaner.javascript = True
    html = cleaner.clean_html(s)
    e = etree.HTML(html)
    li_s = e.xpath("//ul[@id='announcementList']/li")
    data = list()
    for each in li_s:
        content_ele = each.find("div[@class='details']/div[@class='vtbegenerated']")
        if content_ele is not None:
            content = etree.tostring(content_ele,
                                     encoding="utf-8").decode("utf-8").rstrip()
        else:
            content = ''
        # content = re.sub(r"src=\"https://wlkc.ouc.edu.cn/(bbcswebdav/.*?)\"",
        #                  r'src="https://bbh.yangyq.net/img/\1?cookie=' + cookie + "\"", content)
        # content = re.sub(r'width=".*?"', 'width="100%"', content)
        ltime = each.find("div[@class='details']/p[1]/span").text[6:]
        _time = re.search('(\d{4})年(\d{1,2})月(\d{1,2})日 星期.{1} (.{1})午(\d{2})时(\d{2})分(\d{2})秒 CST', ltime)
        hour = _time[5] if _time[4] == '上' or (_time[4] == '下' and _time[5] == '12') else str(int(_time[5]) + 12)
        time_str = f'{_time[1]}-{_time[2].zfill(2)}-{_time[3].zfill(2)} {hour.zfill(2)}:{_time[6].zfill(2)}:{_time[7].zfill(2)}'
        rtime = time.mktime(time.strptime(time_str, "%Y-%m-%d %H:%M:%S"))
        _data = {
            "title": each.find("h3").text.lstrip(),
            "time": rtime,
            "content": content,
            "author": each.xpath("div[@class='announcementInfo']/p[1]")[0].xpath("string(.)")[5:],
            "course": each.xpath("div[@class='announcementInfo']/p[2]")[0].xpath("string(.)")[5:],
        }
        if _data not in data:
            data.append(_data)
    _data = sorted(data, key=lambda x: -x['time'])
    return _data


def submit_homework1(cookie: str, url: str, course_id, content_id, files: str = None, content: str = '',
                     name: str = None):
    try:
        cookies = _gen_cookie_dict(cookie)
        html = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False).text
        e = etree.HTML(html)
        nonce = e.xpath("//input[@name='blackboard.platform.security.NonceUtil.nonce']/@value")[0]
        ajaxid = e.xpath("//input[@name='blackboard.platform.security.NonceUtil.nonce.ajax']/@value")[0]
        data = {
            'blackboard.platform.security.NonceUtil.nonce': nonce,
            'blackboard.platform.security.NonceUtil.nonce.ajax': ajaxid,
            'isAjaxSubmit': 'true',
            'course_id': course_id,
            'content_id': content_id,
            'attempt_id': '',
            'mode': 'view',
            'recallUrl': '/webapps/blackboard/content/listContent.jsp?content_id=_530680_1&amp;course_id=_10425_1',
            'newFile_linkTitle': name,
            'textbox_prefix': ['studentSubmission.text', 'student_commentstext'],
            'student_commentstext': content,
            'newFilefilePickerLastInput': 'dummyValue',
            'newFile_attachmentType': ['L'],
            'newFile_fileId': ['new'],
            'dispatch': 'submit',
            'studentSubmission.type': 'H',
            'studentSubmission.text': '',
            'student_commentstype': 'H'
        }
        file = {
            'newFile_LocalFile0': open(files, 'rb')
        }
        r = requests.post('https://wlkc.ouc.edu.cn/webapps/assignment/uploadAssignment?action=submit', data=data,
                          files=file, headers=headers, proxies=proxies, cookies=cookies, verify=False)
        return 'destinationUrl' in r.text
    except:
        return False


def get_detail_score(course_id: str, cookie: str) -> list:
    cookies = _gen_cookie_dict(cookie)
    url = f'https://wlkc.ouc.edu.cn/webapps/bb-mygrades-BBLEARN/myGrades?course_id={course_id}&stream_name=mygrades'  # 目标网址
    respnse = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False)
    content = respnse.content.decode('utf8')
    html = etree.HTML(content)
    # 根据3类不同的情况，获取分数，文件，批注
    a_id = html.xpath('//div[@id="grades_wrapper"]//div[@class="cell gradable"]/a/@id')
    data = []
    inf = {}
    for i in a_id:  # 一个课程的每一项作业
        type_ = html.xpath('//div[@id="grades_wrapper"]//div//a[@id="' + i + '"]/@onclick')
        web = re.findall(r"[(](.*?)[)]", str(type_))
        web = "".join(web).strip("'")  # 获取/webapps/...
        type_ = str(type_)[38:39]  # 获取类型

        if (type_ == 'g'):  # 测验和签到
            title = html.xpath('//div[@id="grades_wrapper"]//div//a[@id="' + i + '"]/text()')
            # print(title)
            url = 'https://wlkc.ouc.edu.cn' + web
            content = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False).text
            html_g = etree.HTML(content)
            det = list()  # 列表
            subtime = html_g.xpath('//table//tr//td[2]/text()')
            sum = len(subtime)
            if (sum == 0):
                times = "无尝试提交"
                deadline = html_g.xpath('//div//li[3]//div[@class="field"]/text()') + ['null']
                det.append({"times": times, "submissiontime": "null", "deadline": deadline[0].strip(),
                            "score": "null", "totalscore": "null", "background": "null"})
            else:
                for i in range(1, sum + 1, 1):
                    times = "第" + str(i) + "次提交"
                    submissiontime = html_g.xpath('//table//tr[' + str(i + 1) + ']//td[2]/text()') + ['null']
                    deadline = html_g.xpath('//div//li[3]//div[@class="field"]/text()') + ['null']
                    score = html_g.xpath('//table//tr[' + str(i + 1) + ']//td//strong/text()') + ['null']
                    totalscore = html_g.xpath('//div//li[4]//div[@class="field"]/text()') + ['null']
                    det.append(
                        {"times": times, "submissiontime": submissiontime[0].strip(), "deadline": deadline[0].strip(),
                         "score": score[0].strip(), "totalscore": totalscore[0].strip(), "background": "null"})

            inf[title[0]] = det
            # print(inf)

        elif (type_ == 'b'):  # 互评
            title = html.xpath('//div[@id="grades_wrapper"]//div//a[@id="' + i + '"]/text()')
            homeworkid = re.findall(r"[_](.*?)[_]", i)
            submissiontime = html.xpath('//*[@id="' + homeworkid[0] + '"]/div[2]/span[1]/text()') + ['null']
            # print(title)
            # print(submissiontime)
            url = 'https://wlkc.ouc.edu.cn' + web
            content = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False).text
            html_b = etree.HTML(content)
            det = list()  # 列表
            bg = html_b.xpath('//div//tr//td[2]/text()')  # 反馈
            sum = len(bg)
            # print(sum)
            if (sum == 0):
                originscore = html_b.xpath('//li[4]//div[@class="field"]/text()') + ['null']
                # print(originscore)
                if "null" in originscore[0]:
                    score = "null"
                    totalscore = "null"
                else:
                    num = originscore[0].index("/")
                    score = (originscore[0][:num]).strip()
                    totalscore = (originscore[0][num + 1:]).strip()
                # print(score)
                # print(totalscore)
                det.append({"times": "第1次提交", "submissiontime": submissiontime[0].strip(), "deadline": "null",
                            "score": score, "totalscore": totalscore, "background": "null"})
                inf[title[0]] = det
                # print(inf)
            else:
                times = html_b.xpath('//h2[@class="evaluator"]//span/text()')  # 评估者姓名
                for i in range(1, sum + 1, 1):
                    originscore = html_b.xpath('//*[@id="containerdiv"]/table[' + str(i) + ']/tbody/tr/td[1]/text()')
                    num = originscore[0].index("/")
                    score = (originscore[0][:num]).strip()
                    totalscore = (originscore[0][num + 1:]).strip()
                    det.append(
                        {"times": times[i - 1].strip(), "submissiontime": submissiontime[0].strip(), "deadline": "null",
                         "score": score, "totalscore": totalscore, "background": bg[i - 1].strip()})
                inf[title[0]] = det
            # print(inf)

        elif (type_ == 'a'):  # 正常提交
            title = html.xpath('//div[@id="grades_wrapper"]//div//a[@id="' + i + '"]/text()')
            homeworkid = re.findall(r"[_](.*?)[_]", i)
            deadline = html.xpath('//*[@id="' + homeworkid[0] + '"]/div[1]/div[1]/text()')
            # print(title)
            url = 'https://wlkc.ouc.edu.cn' + web
            # print(url)
            content = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False).text
            html_a = etree.HTML(content)
            det = list()  # 列表
            trytime = html_a.xpath('//span[@class="mainLabel"]/text()')
            sum = len(trytime)
            if (sum > 2):  # 多次尝试
                score = html_a.xpath('//span[@class="pointsGraded"]/text()') + ['null']
                submissiontime = html_a.xpath('//span[@class="subHeader dateStamp"]/text()') + ['null']
                totalscore = html_a.xpath('//*[@id="aggregateGrade_pointsPossible"]/text()') + ['null']
                newweb = html_a.xpath('//div[@id="currentAttempt_attemptList"]//a//@href')
                for i in range(2, sum, 1):
                    url = 'https://wlkc.ouc.edu.cn' + newweb[i - 2]
                    content = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False).text
                    html_aa = etree.HTML(content)
                    # print(url)
                    background = html_aa.xpath(
                        '//*[@id="currentAttempt_feedback"]/div/p/span[1]/text()') + html_aa.xpath(
                        '//*[@id="currentAttempt_feedback"]/div/p/text()') + ['null']
                    # print(background)
                    det.append({"times": "第" + str(i - 1) + "次提交", "submissiontime": submissiontime[i - 2].strip(),
                                "deadline": deadline[0].strip(),
                                "score": score[i - 2].strip(), "totalscore": totalscore[0][1:].strip(),
                                "background": background[0].strip()})  # bg读不到
                inf[title[0]] = det
            else:  # 一次尝试
                score = html_a.xpath('//div[@class="grade readOnly"]//input//@value') + ['null']
                submissiontime = html_a.xpath('//*[@id="currentAttempt_label"]/label/span[2]/text()') + ['null']
                totalscore = html_a.xpath('//*[@id="aggregateGrade_pointsPossible"]/text()') + ['null']
                background = html_a.xpath('//*[@id="currentAttempt_feedback"]/div/p/text()') + ['null']
                det.append(
                    {"times": "第1次提交", "submissiontime": submissiontime[0].strip(), "deadline": deadline[0].strip(),
                     "score": score[0].strip(), "totalscore": totalscore[0][1:].strip(),
                     "background": background[0].strip()})
                inf[title[0]] = det
    data.append(inf)
    return data


def check_homework(calendar_id, cookie):
    url = f'https://wlkc.ouc.edu.cn/webapps/calendar/launch/attempt/_blackboard.platform.gradebook2.GradableItem-{calendar_id}'
    cookies = _gen_cookie_dict(cookie)
    r = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False)
    u = r.url
    content_id = re.search('content_id=(.*?)&', u)
    course_id = re.search('course_id=(.*?)&', u)
    e = etree.HTML(r.text)
    if not all([content_id, course_id]):
        return {
            'finished': False,
            'submit': True,
            'content_id': '-',
            'course_id': '-'
        }
    data = {
        'finished': False,
        'submit': False,
        'content_id': content_id.group(1),
        'course_id': course_id.group(1)
    }
    des = e.xpath("//div[@class='vtbegenerated']")
    if des:
        description = etree.tostring(des[0], encoding="utf-8").decode("utf-8").strip()
        cleaner = Cleaner()
        cleaner.javascript = True
        data['description'] = cleaner.clean_html(description)
    if e.xpath("//input[@class='submit button-1' and @name='bottom_开始']") or e.xpath("//input[@class='submit button-1' and @name='bottom_继续']"):
        return data
    # 处理考试，默认没有完成
    if e.xpath("//input[@class='submit button-1' and @name='bottom_提交']"):
        return data
    else:
        if e.xpath("//input[@class='submit button-1' and @name='bottom_开始新的']"):
            data.update({'finished': True, 'submit': True})
        else:
            data.update({'finished': True, 'submit': False})
        return data


class BBGetData:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.39',
    }

    @staticmethod
    def get_ics_id(session):
        cookies = _gen_cookie_dict(session)
        url = 'https://wlkc.ouc.edu.cn/webapps/calendar/calendarFeed/url'
        response = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=False).text
        pattern = r'calendarFeed/([^/]+)/learn.ics'
        match = re.search(pattern, response)
        if match:
            ics_id = match.group(1)
            return ics_id
        else:
            # 如果未找到匹配项，返回None
            return None
