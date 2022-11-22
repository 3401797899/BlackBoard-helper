import json
import time

import requests
import selenium.webdriver.support.wait
from lxml import etree
from lxml.html.clean import Cleaner
import re
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def get_class_list(cookie: str) -> list:
    """
    获取课程列表
    :param cookie: Cookie
    :return: []
    """
    url = 'https://wlkc.ouc.edu.cn/webapps/portal/execute/tabs/tabAction'
    data = {
        'action': 'refreshAjaxModule',
        'modId': '_22_1',
        'tabId': '_1_1',
        'tab_tab_group_id': '_1_1'
    }
    proxies = {
        "http": "socks5://127.0.0.1:1080",
        "https": "socks5://127.0.0.1:1080"
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',
        'Cookie': cookie
    }
    r = requests.post(url, data=data, headers=headers, verify=False, proxies=proxies)
    e = etree.HTML(r.text)
    li = e.xpath('//li')
    data = []
    for i in li:
        name = i.findall('a')[0].text
        teacher = "".join(
            [j.text.replace('\xa0', '') for j in i.findall('div[@class="courseInformation"]/span[@class="name"]')])
        i_id = re.findall('id=(\_.*?)&', i.findall('a')[0].attrib['href'].replace(' ', ''))
        if i_id:
            i_id = i_id[0]
            data.append({'name': name, 'teacher': teacher,
                         'id': i_id})
    return data


def get_class_detail_by_url(url: str, cookie: str) -> list:
    """
    获取某一课程的列表
    :param url: 课程url
    :param cookie: Cookie
    :return: []
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',
        'Cookie': cookie
    }
    proxies = {
        "http": "socks5://127.0.0.1:1080",
        "https": "socks5://127.0.0.1:1080"
    }
    r = requests.get(url, verify=False, headers=headers, proxies=proxies)
    r.encoding = 'utf-8'
    data = []
    e = etree.HTML(r.text)
    ul = e.xpath("//ul[@class='courseMenu']/li[not(contains(@class,'divider'))]")
    for li in ul:
        if 'subhead' in li.attrib['class']:
            data.append({"name": li.findall('h3')[0].findall('span')[0].text, "type": "subhead"})
            continue
        a = li.findall('a')[0]
        text = a.findall('span')[0].text
        link = a.attrib['href']
        content_id = re.findall('content_id=(.*?)&', link)
        if content_id:
            data.append({"name": text, "type": "content", "id": content_id[0]})
            continue
        tool_id = re.findall('tool_id=(.*?)&', link)
        if tool_id and tool_id[0] == "_136_1":
            data.append({"name": text, "type": "announcement"})
    return data


# def get_item_detail(url: str, cookie: str) -> list:
#     """
#     获取详细页面内容
#     :param url: url地址
#     :param cookie: cookie
#     :return: []
#     """
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',
#         'Cookie': cookie
#     }
#     t = requests.get(url, headers=headers, verify=False)
#     data = []
#     # with open('a.html', 'r', encoding='utf-8') as f:
#     #     result = f.read()
#     e = etree.HTML(t.text)
#     ul = e.xpath("//ul[@class='contentList']/li")
#     for li in ul:
#         name = li.findall('div[@class="item clearfix"]/h3/span')[1].text
#         file = "https://wlkc.ouc.edu.cn" + li.findall('.//a')[0].attrib['href']
#         data.append({"name": name, "file": file})
#     return data


def get_content_by_id(course_id: str, content_id: str, cookie: str) -> list:
    """
    通过content_id获取获取内容
    :param course_id: 课程id
    :param content_id: 内容id
    :param cookie: session
    :return: []
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',
        'Cookie': cookie
    }
    proxies = {
        "http": "socks5://127.0.0.1:1080",
        "https": "socks5://127.0.0.1:1080"
    }
    url = f'https://wlkc.ouc.edu.cn/webapps/blackboard/content/listContent.jsp?course_id={course_id}&content_id={content_id}'
    t = requests.get(url, headers=headers, verify=False, proxies=proxies)
    cleaner = Cleaner()
    cleaner.javascript = True
    html = cleaner.clean_html(t.text)
    e = etree.HTML(html)
    data = []
    ul = e.xpath("//ul[@class='contentList']/li")
    for li in ul:
        name = li.findall('div[@class="item clearfix"]/h3')[0].xpath("string(.)").replace('\n', '').replace(' ', '')
        d = {"name": name, "details": {}}
        _content_id = li.find('div[@class="item clearfix"]/h3/a')
        if _content_id is not None:
            href = _content_id.attrib['href']
            _content_id = re.findall('content_id=_(.*?_1)', href)
            if _content_id and _content_id[0] != content_id:
                id_type = "content"
                if "uploadAssignment" in href:
                    id_type = "homework"
                d = {"name": name, "id": _content_id[0], "type": id_type, "details": {}}
            else:
                d['details']['file'] = [
                    {
                        "name": name,
                        "href": "https://wlkc.ouc.edu.cn" + href
                    }
                ]
        t = li.findall('div[@class="details"]')
        if t:
            text = t[0].findall('div[@class="vtbegenerated"]')
            if text:
                d['details']['text'] = etree.tostring(text[0], encoding='utf-8').decode('utf-8')
            file = t[0].findall('div[@class="contextItemDetailsHeaders clearfix"]')
            if file:
                if "file" not in d["details"].keys():
                    d['details']['file'] = list()
                f = file[0].findall('.//ul[@class="attachments clearfix"]/li')
                for each in f:
                    a = each.findall('a')[0]
                    d['details']['file'].append(
                        {"name": a.xpath('./text()')[0], "href": "https://wlkc.ouc.edu.cn" + a.attrib['href']})
        data.append(d)
    return data


# def get_class_score(course_id: str, cookie: str) -> list:
#     """
#     获取课程成绩
#     :param course_id:
#     :param cookie:
#     :return:
#     """
#     headers = {
#         'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
#         'Cookie': cookie
#     }
#     url = f'https://wlkc.ouc.edu.cn/webapps/bb-mygrades-BBLEARN/myGrades?course_id={course_id}&stream_name=mygrades'  # 目标网址
#     t = requests.get(url, headers=headers, verify=False)
#     e = etree.HTML(t.text)
#
#     tdata = []
#     position = []
#     for i in range(100000, 100050, 1):
#         j = str(i)
#         position.append(j)
#     # print(position)
#     num = '//div[@position=100000]'
#     for i in range(1, 50, 1):
#         num = num.replace(position[i - 1], position[i])
#         score = e.xpath(num + '/div/span[@class="grade"]/text()') + ['null']
#
#         temp = '/a/text()' if score[0] != '-' else '/text()'
#         title = e.xpath(num + '/div[@class="cell gradable"]' + temp) + ['null']
#         ddl = e.xpath(num + '/div/div[@class="activityType"]/text()') + ['null']
#         checktime = e.xpath(num + '/div/span[@class="lastActivityDate"]/text()') + ['null']
#         totlescore = e.xpath(num + '/div/span[@class="pointsPossible clearfloats"]/text()') + ['null']
#         tdata.append({"title": title[0].strip(), "deadline": ddl[0].strip(), "checktime": checktime[0].strip(),
#                       "score": score[0].strip(), "totlescore": totlescore[0].strip()})
#     data = []
#     for i in tdata:
#         if i.get('title') != 'null':
#             data.append(i)
#     return data
#
#
# def get_class_try(course_id: str, content_id: str, cookie: str) -> list:
#     headers = {
#         'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
#         'Cookie': cookie
#     }
#     url = f'https://wlkc.ouc.edu.cn/webapps/assignment/uploadAssignment?content_id={content_id}&course_id={course_id}&group_id=&mode=view'
#     t = requests.get(url, headers=headers, verify=False)
#     e = etree.HTML(t.text)
#     titles = e.xpath('//span[@class="mainLabel"]/text()')
#     data = []
#     inf = {}
#     if len(titles) > 2:
#         scores1 = e.xpath('//span[@class="pointsGraded"]/text()')  # 多次尝试
#         times = e.xpath('//span[@class="subHeader dateStamp"]/text()')
#         for i in range(2, len(titles)):
#             inf['name'] = titles[i]
#             inf['time'] = times[i - 2]
#             inf['score'] = scores1[i - 2]
#             data.append(inf)
#     else:
#         scores2 = e.xpath('//div/input/@value')[2:]  # 一次
#         times = e.xpath('//*[@class="subHeader  dateStamp "]/text()')
#
#         for i in range(1, len(scores2)):
#             inf['name'] = titles[i]
#             inf['time'] = times[0].strip()
#             inf['score'] = scores2[i - 1]
#             data.append(inf)
#     return data
def get_class_score(course_id: str, cookie: str) -> list:
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
        'Cookie': cookie
    }
    proxies = {
        "http": "socks5://127.0.0.1:1080",
        "https": "socks5://127.0.0.1:1080"
    }
    url = f'https://wlkc.ouc.edu.cn/webapps/bb-mygrades-BBLEARN/myGrades?course_id={course_id}&stream_name=mygrades'  # 目标网址
    t = requests.get(url, headers=headers, verify=False, proxies=proxies)
    e = etree.HTML(t.text)
    data = []
    ul = e.xpath("//div[@id='grades_wrapper']/div")
    for li in ul:
        inf = {'score': li.xpath('.//span[@class="grade"]/text()')[0], 'class_type': li.xpath('./@class')[0][
                                                                                     18:-13],
               'lastactivity': li.xpath('./@lastactivity')[0][:-3], 'duedate': li.xpath('./@duedate')[0][:-3]}
        if inf['class_type'] == 'graded_item_row' or inf['class_type'] == 'submitted_item_row':
            inf['title'] = li.xpath('./div[@class="cell gradable"]/a/text()')[0].strip()  # 标题
        else:
            inf['title'] = li.xpath('./div[@class="cell gradable"]/span/text()')[0].strip()
        totlescore = li.xpath('./div/span[@class="pointsPossible clearfloats"]/text()')
        inf['totlescore'] = totlescore[0].strip('/') if totlescore != [] else ""  # 有总分返回总分，没有返回空串
        data.append(inf)
    return data


def get_class_try(course_id: str, content_id: str, cookie: str) -> list:
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
        'Cookie': cookie
    }
    proxies = {
        "http": "socks5://127.0.0.1:1080",
        "https": "socks5://127.0.0.1:1080"
    }
    url = f'https://wlkc.ouc.edu.cn/webapps/assignment/uploadAssignment?content_id={content_id}&course_id={course_id}&group_id=&mode=view'
    t = requests.get(url, headers=headers, verify=False, proxies=proxies)
    e = etree.HTML(t.text)

    data = []
    judge = e.xpath("//div[@id='currentAttempt_attemptList']")
    if judge:  # 多次尝试
        ul = e.xpath('//div[@id="currentAttempt_attemptList"]/ul/li')
        for li in ul:
            inf = {'title': li.xpath('.//span[@class="mainLabel"]/text()')[0],
                   'score': li.xpath('.//span[@class="pointsGraded"]')[0].text,
                   'time': li.xpath('.//span[@class="subHeader dateStamp"]/text()')[0]}
            data.append(inf)
    else:
        inf = {'title': e.xpath('//div[@class="grade readOnly"]/input[@id="currentAttempt_grade"]/@title')[0],
               'score': e.xpath('//div[@class="grade readOnly"]/input[@id="currentAttempt_grade"]/@value')[0],
               'time': e.xpath('//*[@id="currentAttempt_label"]/label/span[2]/text()')[0].strip()}
        data.append(inf)
    return data


def get_calendar(start: str, end: str, cookie: str) -> list:
    url = f"https://wlkc.ouc.edu.cn/webapps/calendar/calendarData/selectedCalendarEvents?start={start}&end={end}&course_id=&mode=personal"
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
        'Cookie': cookie
    }
    proxies = {
        "http": "socks5://127.0.0.1:1080",
        "https": "socks5://127.0.0.1:1080"
    }
    raw_data = requests.get(url, headers=headers, proxies=proxies).json()
    data = list()
    for each in raw_data:
        d = {
            "course": each["calendarName"],
            "title": each["title"],
            "start": each["start"],
            "end": each["end"],
            "type": each["eventType"]
        }
        if each["eventType"] == "作业":
            d["id"] = each["itemSourceId"]
        data.append(d)
    return data


def get_announcements(cookie: str, course_id: str) -> list:
    url = "https://wlkc.ouc.edu.cn/webapps/blackboard/execute/announcement?method=search&viewChoice=2&course_id=" + course_id
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
        'Cookie': cookie
    }
    proxies = {
        "http": "socks5://127.0.0.1:1080",
        "https": "socks5://127.0.0.1:1080"
    }
    s = requests.get(url, headers=headers, proxies=proxies).text
    cleaner = Cleaner()
    cleaner.javascript = True
    html = cleaner.clean_html(s)
    e = etree.HTML(html)
    ul = e.xpath("//ul[@id='announcementList']/li")
    data = list()
    for each in ul:
        content_ele = each.find("div[@class='details']/div[@class='vtbegenerated']")
        if content_ele:
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


def submit_homework(cookie: str, url: str, files: list = None, content: str = '', submit: bool = False):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    op = Options()
    op.add_argument("blink-settings=imagesEnabled=false")
    op.add_argument('--headless')
    op.add_argument('--disable-gpu')
    op.add_argument("window-size=1024,768")
    op.add_argument("--no-sandbox")
    chrome = webdriver.Chrome("/tmp/chrome/chromedriver", options=op)
    chrome.get('https://wlkc.ouc.edu.cn/learn/api')
    chrome.add_cookie({
        'name': 's_session_id',
        'value': cookie.split("=")[-1][:-1],
        'path': '/',
        'domain': 'wlkc.ouc.edu.cn',
        'secure': True,
    })
    chrome.get(url)
    # selenium.webdriver.support.wait.WebDriverWait(chrome, 3).until(
    #     EC.presence_of_element_located((By.CLASS_NAME, 'locationPane')))
    try:
        chrome.find_element(By.ID, "currentAttempt")
        status = True
    except:
        status = False
    if status:
        e = etree.HTML(chrome.page_source)
        # 作业说明
        ele = e.xpath("//div[@id='contentDetails']//div[@class='vtbegenerated']")
        description = ''
        if ele:
            description = etree.tostring(ele[0], encoding="utf-8").decode("utf-8")
            description = re.sub(r">\s+<", "><", description).strip()
        # 获取提交的文件
        ul = e.xpath("//ul[@id='currentAttempt_submissionList']/li")
        files = []
        for li in ul:
            name = li.find("a").text.strip()
            href = li.find("div[@class='downloadFile']/a").attrib.get("href").strip()
            files.append({"name": name, "href": href})
        # 获取最高成绩
        score = e.xpath("//input[@id='aggregateGrade']")[0].attrib.get("value")
        # 获取反馈
        feedback = e.xpath("//div[@id='currentAttempt_feedback']//div[@class='vtbegenerated']")
        if feedback:
            feedback = etree.tostring(feedback[0], encoding="utf-8").decode("utf-8")
            feedback = re.sub(">\s+<", "><", feedback).strip()
        else:
            feedback = ""
        # chrome.close()
        return {
            'description': description,
            'files': files,
            'score': score,
            'feedback': feedback,
            'resubmit': not not e.xpath("//input[@value='开始新的']")
        }
    else:
        try:
            chrome.find_element(By.ID, "agree_button").click()
        except:
            pass
        if files:
            file = chrome.find_element(By.ID, "newFile_chooseLocalFile")
            file.send_keys("\n ".join([i[0] for i in files]))
            tb = chrome.find_elements(By.XPATH, "//tbody[@id='newFile_table_body']/tr")
            for i in range(len(tb)):
                each = chrome.find_element(By.XPATH, f"//tbody[@id='newFile_table_body']/tr[{i + 1}]//td[2]/input")
                each.send_keys(Keys.CONTROL + 'a')
                each.send_keys(Keys.DELETE)
                each.send_keys(files[i][1])

        chrome.switch_to.frame("student_commentstext_ifr")
        chrome.find_element(By.ID, "tinymce").send_keys(content)
        chrome.switch_to.default_content()
        # chrome.find_element(By.ID, "uploadAssignmentFormId").submit()
        chrome.execute_script("checkDupeFile('submit')")
        try:
            alert = chrome.switch_to.alert
            text = alert.text
            chrome.close()
            return text
        except:
            flag = True
            while flag:
                try:
                    chrome.find_element(By.ID, "currentAttempt")
                    flag = False
                except:
                    pass
            chrome.close()
            return True

    # except Exception as e:
    #     print(e)
    #     print(e.__traceback__)
    #     return False
