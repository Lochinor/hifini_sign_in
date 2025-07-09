# -*- coding: utf-8 -*-
"""
cron: 1 0 0 * * *
new Env('HiFiNi');
"""

import json
import requests
import re
import os
import time
import random

requests.packages.urllib3.disable_warnings()


def multi_sign(json_str):
    try:
        configs = json.loads(json_str)
    except json.JSONDecodeError as e:
        send(f"解析HIFINI JSON时出错：{e}")
    else:
        # print(configs)
        for index, item in enumerate(configs):
            username = item.get("username")
            cookie = item.get("cookie")
            # 随机延迟
            sleep_time = random.uniform(1.0, 3.0 + index)
            print("============")
            print(f"第{index+1}次执行签到{username},等待 {sleep_time}")
            print(f"cookie: {cookie}")
            time.sleep(sleep_time)
            try_sign(cookie)
        
        print("---the end---")

                

def try_sign(cookie):
    print("-----------")
    status = check_sign_status(cookie)
    print(status)

    if status.get("status") and not status.get("signed"):
        sign_result = perform_sign('', cookie)
        print(sign_result)    


def check_sign_status(cookies):
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "zh-CN,zh;q=0.9",
        "cookie": cookies,
        "priority": "u=0, i",
        "referer": "https://www.hifini.net/sg_sign.htm",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    try:
        # 1. 获取签到页面内容（注意使用正确的域名）
        response = requests.get(
            "https://www.hifini.net/sg_sign.htm", headers=headers, timeout=10
        )
        html_content = response.text
        response.raise_for_status()

        # 2. 检查登录状态（更精确的判断）
        if "请登录" in html_content and "我的主页" not in html_content:
            return {"status": False, "message": "Cookie失效，请重新登录"}

        # 3. 更灵活的正则匹配
        status_pattern = r'var\s+s1\s*=\s*[\'"](.*?)[\'"];\s*var\s+s2\s*=\s*[\'"](.*?)[\'"];\s*var\s+s3\s*=\s*[\'"](.*?)[\'"]'
        match = re.search(status_pattern, html_content)

        if not match:
            return {"status": False, "message": "未找到签到状态信息"}

        s1_text, s2_text, s3_text = match.groups()

   
        result = {
            "status": True,
            "signed": s1_text == "已签",
            "message": "今日已签到" if s1_text == "已签" else "今日未签到",
            "total_people": s2_text.replace("人", "") if "人" in s2_text else s2_text,
            "consecutive_days": (
                re.search(r"(\d+)", s3_text).group(1)
                if re.search(r"(\d+)", s3_text)
                else "0"
            ),
        }

        return result

    except requests.exceptions.RequestException as e:
        return {"status": False, "message": f"请求失败: {str(e)}"}

def perform_sign(sign, cookie):
    max_retries = 5
    retries = 0
    msg = ""
    while retries < max_retries:
        try:
            msg += "第{}次执行签到\n".format(str(retries + 1))
            sign_in_url = "https://www.hifini.net/sg_sign.htm"
            headers = {
                "Cookie": cookie,
                "authority": "www.hifini.net",
                "accept": "text/plain, */*; q=0.01",
                "accept-language": "zh-CN,zh;q=0.9",
                "origin": "https://www.hifini.net",
                "referer": "https://www.hifini.net/",
                "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                "x-requested-with": "XMLHttpRequest",
            }

            rsp = requests.post(
                url=sign_in_url, headers=headers, timeout=15, verify=False
            )
            rsp_text = rsp.text.strip()
            print(rsp_text)
            success = False
            if "今天已经签过啦！" in rsp_text:
                msg += "已经签到过了，不再重复签到!\n"
                success = True
            elif "成功" in rsp_text:
                rsp_json = json.loads(rsp_text)
                msg += rsp_json["message"]
                success = True
            elif "503 Service Temporarily" in rsp_text or "502 Bad Gateway" in rsp_text:
                msg += "服务器异常！\n"
            elif "请登录后再签到!" in rsp_text:
                msg += "Cookie没有正确设置！\n"
                success = True
            elif "操作存在风险，请稍后重试" in rsp_text:
                msg += "没有设置sign导致的!\n"
                success = False
                send("hifini 签到失败：", msg)
            else:
                msg += "未知异常!\n"
                msg += rsp_text + "\n"

            # rsp_json = json.loads(rsp_text)
            # print(rsp_json['code'])
            # print(rsp_json['message'])
            if success:
                print("签到结果: ", msg)
                send("hifini 签到结果", msg)
                break  # 成功执行签到，跳出循环
            elif retries >= max_retries:
                print("达到最大重试次数，签到失败。")
                send("hifini 签到结果", msg)
                break
            else:
                retries += 1
                print("等待20秒后进行重试...")
                time.sleep(20)
        except Exception as e:
            print("签到失败，失败原因:" + str(e))
            send("hifini 签到结果", str(e))
            retries += 1
            if retries >= max_retries:
                print("达到最大重试次数，签到失败。")
                break
            else:
                print("等待20秒后进行重试...")
                time.sleep(20)


def send(title, content):
    print(title, content)
    # QLAPI.notify(title, content)


if __name__ == "__main__":
    json_str = os.getenv("HIFINI_JSON")
    cookie = os.getenv("HIFINI_COOKIE")

    if json_str:
        multi_sign(json_str)
    elif not cookie:
        send(
            "hifini 签到异常", "hifini 签到失败：没有获取到 cookie，请检查环境变量设置"
        )
    else:
       try_sign(cookie)