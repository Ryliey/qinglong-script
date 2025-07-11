"""
name: SteamTools签到
cron: 0 6 * * *
"""

import os
import re
import requests

from logger import logger
from typing import Dict, Tuple, List
from selectolax.parser import HTMLParser


class SteamTools:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept-Language": "zh-CN,zh;q=0.8",
        "Referer": "https://bbs.steamtools.net/plugin.php?id=dc_signin&action=index",
    }

    def __init__(self, cookies_dict: Dict[str, str]):
        self._base_url = "https://bbs.steamtools.net"
        self._stats_url = f"{self._base_url}/plugin.php?id=dc_signin"
        self._submit_url = f"{self._base_url}/plugin.php?id=dc_signin:sign"

        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.cookies.update(cookies_dict)
        self.session.timeout = 10

    def _parse_signin_stats(self) -> Tuple[str, str, bool, HTMLParser]:
        try:
            status_resp = self.session.get(self._stats_url)
            status_resp.raise_for_status()
            html = HTMLParser(status_resp.text)

            login_link = html.css_first(
                'a[href*="member.php?mod=logging&action=login"]'
            )
            if login_link:
                logger.error("登录失败，请检查Cookie是否失效")
                raise ValueError("登录失败，请检查Cookie是否失效")

            user_name_elem = html.css_first("#myitem")
            user_name = user_name_elem.text() if user_name_elem else "未知用户"

            signin_days_elem = html.css_first("div.sign-num")
            signin_days = signin_days_elem.text() if signin_days_elem else "0"

            signin_button = html.css_first(".sign_div > a:nth-child(3)")
            signin_text = signin_button.text() if signin_button else ""

            needs_signin = signin_text == "签到"
            if needs_signin:
                logger.debug(f"用户 {user_name} 开始签到")
            else:
                logger.debug(f"用户 {user_name} 今日已签到")

            return user_name, signin_days, needs_signin, html
        except Exception as e:
            logger.error(f"获取签到状态失败: {e}")
            return "未知用户", "0", False, HTMLParser("")

    def _extract_formhash(self, html: HTMLParser) -> str:
        formhash = html.css_first("#scbar_form > input:nth-child(2)")

        if not formhash or not (value := formhash.attributes.get("value")):
            logger.error("页面结构异常，Formhash提取失败")
            raise ValueError("未能获取formhash")
        logger.debug(f"成功获取Formhash: {value[:4]}****")
        return value

    def _extract_reward(self, resp_html: str) -> str:
        html = HTMLParser(resp_html)
        reward_message = html.css_first("#messagetext > p:nth-child(1)")

        if not reward_message:
            logger.error("解析奖励信息失败")
            return "0"

        message_text = reward_message.text().strip()
        match = re.search(r"随机奖励T币\s*(\d+)", message_text)

        return match.group(1) if match else "0"

    def _submit_sign(self, html: HTMLParser) -> str:
        try:
            form_data = {
                "formhash": self._extract_formhash(html),
                "signsubmit": "yes",
                "handlekey": "signin",
                "emotid": "4",
                "referer": "https://bbs.steamtools.net/plugin.php?id=dc_signin",
                "content": "没有开心，哪里来的幸福？要开心啦",
            }

            resp = self.session.post(self._submit_url, data=form_data)
            resp.raise_for_status()

            return self._extract_reward(resp.text)
        except requests.HTTPStatusError as e:
            logger.error(f"HTTP状态异常: {e.response.status_code}")
            return "0"
        except Exception as e:
            logger.error(f"签到请求失败: {e}")
            return "0"

    def execute(self) -> str:
        try:
            user_name, signin_days, needs_signin, html = self._parse_signin_stats()

            if needs_signin:
                reward = self._submit_sign(html)

                message = (
                    f"账号：{user_name}\n奖励：{reward}\n已连续签到 {signin_days} 天"
                )
            else:
                message = (
                    f"账号：{user_name}\n今日已手动签到\n已连续签到 {signin_days} 天"
                )

            return message
        except Exception as e:
            logger.error(f"执行签到失败: {e}")
            return f"签到失败: {str(e)}"
        finally:
            self.session.close()


class MultiAccountSignIn:
    def __init__(self, cookies_env_name: str, executor_class: type):
        self.cookies_env_name = cookies_env_name
        self.executor_class = executor_class

        self.cookies_env = os.environ.get(cookies_env_name)
        if not self.cookies_env:
            logger.error(f"未设置环境变量 {cookies_env_name}")
            raise ValueError(f"未设置环境变量 {cookies_env_name}")

    def _get_cookies_list(self) -> List[str]:
        cookies_list = self.cookies_env.split("&")

        cookies_list = [cookie.strip() for cookie in cookies_list if cookie.strip()]

        if not cookies_list:
            raise ValueError("未找到有效的cookie")

        logger.debug(f"账号数量：{len(cookies_list)}")
        return cookies_list

    @staticmethod
    def _parse_cookies(cookies_str: str) -> Dict[str, str]:
        if not cookies_str:
            raise ValueError("Cookie字符串不能为空")
        return dict(cookie.split("=") for cookie in cookies_str.split("; "))

    def _process_account(self, account_num: int, cookies_str: str) -> str:
        try:
            cookies_dict = self._parse_cookies(cookies_str)
            signin = self.executor_class(cookies_dict)
            return signin.execute()
        except Exception as e:
            return f"账号 {account_num} 任务失败: {str(e)}"

    def execute_all(self) -> str:
        try:
            cookies_list = self._get_cookies_list()
            messages = ["***** 开始任务 *****"]

            for i, cookies_str in enumerate(cookies_list, 1):
                messages.append(f"\n----- 账号 {i} -----")
                account_result = self._process_account(i, cookies_str)
                messages.append(account_result)

            messages.append("\n***** 任务结束 *****")
            return "\n".join(messages)

        except Exception as e:
            error_msg = f"任务执行失败: {str(e)}"
            logger.error(error_msg)
            return error_msg


def main():
    multi_signin = MultiAccountSignIn(
        cookies_env_name="STEAMTOOLS_COOKIES",
        executor_class=SteamTools,
    )
    message = multi_signin.execute_all()
    print(message)
    QLAPI.notify("SteamTools签到", message)


if __name__ == "__main__":
    main()
