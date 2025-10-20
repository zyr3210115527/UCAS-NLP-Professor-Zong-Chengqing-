'''
代码名称：爬取人民日报数据为txt文件（带进度条）
编写日期：2025年1月1日
作者：github（caspiankexin）修改增强版
版本：第4版
功能：爬取人民日报新闻数据并显示进度条
可爬取的时间范围：2024年12月起
注意：此代码仅供交流学习，不得用于其他用途。
'''

import requests
import bs4
import os
import datetime
import time
from tqdm import tqdm   # 新增进度条模块

def fetchUrl(url):
    '''
    功能：访问 url 的网页，获取网页内容并返回
    参数：目标网页的 url
    返回：目标网页的 html 内容
    '''
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    }

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text


def getPageList(year, month, day):
    '''
    功能：获取当天报纸的各版面的链接列表
    参数：年，月，日
    '''
    url = f'http://paper.people.com.cn/rmrb/pc/layout/{year}{month}/{day}/node_01.html'
    html = fetchUrl(url)
    bsobj = bs4.BeautifulSoup(html, 'html.parser')
    temp = bsobj.find('div', attrs={'id': 'pageList'})
    if temp:
        pageList = temp.ul.find_all('div', attrs={'class': 'right_title-name'})
    else:
        pageList = bsobj.find('div', attrs={'class': 'swiper-container'}).find_all('div', attrs={'class': 'swiper-slide'})
    linkList = []

    for page in pageList:
        link = page.a["href"]
        url = f'http://paper.people.com.cn/rmrb/pc/layout/{year}{month}/{day}/{link}'
        linkList.append(url)

    return linkList


def getTitleList(year, month, day, pageUrl):
    '''
    功能：获取报纸某一版面的文章链接列表
    参数：年，月，日，该版面的链接
    '''
    html = fetchUrl(pageUrl)
    bsobj = bs4.BeautifulSoup(html, 'html.parser')
    temp = bsobj.find('div', attrs={'id': 'titleList'})
    if temp:
        titleList = temp.ul.find_all('li')
    else:
        titleList = bsobj.find('ul', attrs={'class': 'news-list'}).find_all('li')
    linkList = []

    for title in titleList:
        tempList = title.find_all('a')
        for temp in tempList:
            link = temp["href"]
            if 'content' in link:
                url = f'http://paper.people.com.cn/rmrb/pc/content/{year}{month}/{day}/{link}'
                linkList.append(url)

    return linkList


def getContent(html):
    '''
    功能：解析 HTML 网页，获取新闻的文章内容
    参数：html 网页内容
    '''
    bsobj = bs4.BeautifulSoup(html, 'html.parser')

    # 获取文章标题
    try:
        title = bsobj.h3.text + '\n' + bsobj.h1.text + '\n' + bsobj.h2.text + '\n'
    except:
        title = '（无标题）\n'

    # 获取文章内容
    pList = bsobj.find('div', attrs={'id': 'ozoom'}).find_all('p')
    content = ''
    for p in pList:
        content += p.text + '\n'

    return title + content


def saveFile(content, path, filename):
    '''
    功能：将文章内容 content 保存到本地文件中
    参数：要保存的内容，路径，文件名
    '''
    if not os.path.exists(path):
        os.makedirs(path)

    file_path = os.path.join(path, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def download_rmrb(year, month, day, destdir):
    '''
    功能：爬取《人民日报》网站 某年 某月 某日 的新闻内容，并保存在 指定目录下
    参数：年，月，日，文件保存的根目录
    '''
    pageList = getPageList(year, month, day)
    print(f"\n开始爬取 {year}-{month}-{day} 的数据，共 {len(pageList)} 个版面...\n")

    for pageNo, page in enumerate(tqdm(pageList, desc=f"{year}-{month}-{day} 版面进度", ncols=80), start=1):
        try:
            titleList = getTitleList(year, month, day, page)
            for titleNo, url in enumerate(tqdm(titleList, desc=f"第{pageNo}版文章进度", ncols=80, leave=False), start=1):
                html = fetchUrl(url)
                content = getContent(html)
                path = os.path.join(destdir, f"{year}{month}{day}")
                fileName = f"{year}{month}{day}-{str(pageNo).zfill(2)}-{str(titleNo).zfill(2)}.txt"
                saveFile(content, path, fileName)
        except Exception as e:
            print(f"日期 {year}-{month}-{day} 下的版面 {page} 出现错误：{e}")
            continue


def gen_dates(b_date, days):
    day = datetime.timedelta(days=1)
    for i in range(days):
        yield b_date + day * i


def get_date_list(beginDate, endDate):
    '''
    获取日期列表
    '''
    start = datetime.datetime.strptime(beginDate, "%Y%m%d")
    end = datetime.datetime.strptime(endDate, "%Y%m%d")

    data = []
    for d in gen_dates(start, (end - start).days + 1):
        data.append(d)
    return data


if __name__ == '__main__':
    print("欢迎使用人民日报爬虫（带进度条）！")
    beginDate = input('请输入开始日期（如20241201）:')
    endDate = input('请输入结束日期（如20241205）:')
    destdir = input("请输入数据保存的文件夹路径（如 D:/rmrb_data）:")

    data = get_date_list(beginDate, endDate)
    print(f"\n将爬取 {len(data)} 天的人民日报数据...\n")

    for d in tqdm(data, desc="整体进度（按天）", ncols=80):
        year = str(d.year)
        month = str(d.month).zfill(2)
        day = str(d.day).zfill(2)
        download_rmrb(year, month, day, destdir)
        print(f"✅ {year}-{month}-{day} 爬取完成！")
        time.sleep(5)  # 防止被封IP，可调整

    input("\n🎉 所有日期爬取完成！按回车键退出程序。")
