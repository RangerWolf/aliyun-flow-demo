import hashlib
import time
import urllib

import requests
import os
import logging
import sys
import urllib.parse
import datetime
import pytz
import hashlib
import base64
import hmac

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

BAIDU_APP_AK = 'YOUR_AK'
BAIDU_APP_SK = 'YOUR_SK'

LARK_WEBHOOK_URL = "YOUR_URL"
LARK_WEBHOOK_SECRET = "YOUR_SECRET"


def calc_sn(query_str, sk):
    """
    计算SN，此段代码直接从官网copy下来，写得不好别怪我
    :param query_str:
    :param sk:
    :return:
    """
    # 以get请求为例http://api.map.baidu.com/geocoder/v2/?address=百度大厦&output=json&ak=yourak
    # queryStr = '/geocoder/v2/?address=百度大厦&output=json&ak=yourak'

    # 对queryStr进行转码，safe内的保留字符不转换
    encodedStr = urllib.parse.quote(query_str, safe="/:=&?#+!$,;'@()*[]")

    # 在最后直接追加上yoursk
    rawStr = encodedStr + sk

    # md5计算出的sn值7de5a22212ffaa9e326444c75a58f9a0
    # 最终合法请求url是http://api.map.baidu.com/geocoder/v2/?address=百度大厦&output=json&ak=yourak&sn=7de5a22212ffaa9e326444c75a58f9a0
    sn = hashlib.md5(urllib.parse.quote_plus(rawStr).encode("utf-8")).hexdigest()
    return sn


def get_forcast(district_id):
    query_str = f'/weather/v1/?district_id={district_id}&data_type=all&ak={BAIDU_APP_AK}&output=json'
    sn = calc_sn(query_str, BAIDU_APP_SK)

    req_url = f"https://api.map.baidu.com{query_str}&sn={sn}"
    try:
        resp = requests.get(req_url)
        data = resp.json()
        if data['status'] == 0:
            return True, data['result']
        else:
            logging.info(data)
            return False, f"Error Code:{data['status']}, Error Msg: {data['message']}"

    except Exception as e:
        logging.exception(e)
        return False, str(e)


def gen_lark_sign(timestamp, secret):
    # 拼接timestamp和secret
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()

    # 对结果进行base64处理
    sign = base64.b64encode(hmac_code).decode('utf-8')

    return sign


def send_notifiation(msg):
    timestamp = int(time.time())

    resp = requests.post(
        LARK_WEBHOOK_URL, json={
            "msg_type": "text",
            "timestamp": timestamp,
            "sign": gen_lark_sign(timestamp, LARK_WEBHOOK_SECRET),
            "content": {"text": msg}}
    )


def format_data(data):
    """
    只显示今天的气温跟明天的预报，如果下雨等额外处理（目前还没有这个信息）
    :param info:
    :return:
    """
    print(data)

    # 获取时间
    tz_cst = pytz.timezone('Asia/Shanghai')
    now_cst = datetime.datetime.now(tz_cst)
    today = now_cst.strftime("%Y-%m-%d")
    tomorrow = now_cst + datetime.timedelta(days=1)
    tomorrow = tomorrow.strftime("%Y-%m-%d")

    today_forcast = ""
    tomorrow_forcast = ""

    # 获取对应的预报信息
    for item in data.get('forecasts', []):
        if item['date'] == today:
            today_forcast = f"今日天气：{item['text_day']} {item['low']}~{item['high']}℃ {item['wd_day']} {item['wc_day']}"
        if item['date'] == tomorrow:
            tomorrow_forcast = f"明日预报：{item['text_day']} {item['low']}~{item['high']}℃ {item['wd_day']} {item['wc_day']}"

    msg = f"{today_forcast}\n{tomorrow_forcast}"
    return msg


def run():
    # get this from : https://mapopen-website-wiki.cdn.bcebos.com/cityList/weather_district_id.csv
    district_id = "320100"  # 南京市
    success, data = get_forcast(district_id)
    if success:
        msg = format_data(data)
        send_notifiation(msg)
    else:
        send_notifiation(data)


if __name__ == '__main__':
    run()