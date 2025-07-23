"""
name: SteamTools签到
cron: 0 6 * * *
"""

import os
import re
import requests
from typing import Dict, Tuple, List

from utils.result import Result
from utils.logger import logger
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

    def _parse_signin_stats(self) -> Result[Tuple[str, str, bool, HTMLParser]]:
        try:
            status_resp = self.session.get(self._stats_url)
            status_resp.raise_for_status()
            html = HTMLParser(status_resp.text)

            login_link = html.css_first(
                'a[href*="member.php?mod=logging&action=login"]'
            )
            if login_link:
                return Result.failure("Cookie已失效，请重新获取")

            user_name_elem = html.css_first("#myitem")
            user_name = user_name_elem.text() if user_name_elem else "未知用户"

            signin_days_elem = html.css_first("div.sign-num")
            signin_days = signin_days_elem.text() if signin_days_elem else "获取失败"

            signin_button = html.css_first(".sign_div > a:nth-child(3)")
            signin_text = signin_button.text() if signin_button else ""

            needs_signin = signin_text == "签到" or signin_days == "已签到"

            if needs_signin:
                logger.debug(f"用户 {user_name} 开始签到")
            else:
                logger.debug(f"用户 {user_name} 今日已签到")

            return Result.success((user_name, signin_days, needs_signin, html))
        except Exception as e:
            return Result.failure(f"网络请求失败: {str(e)}")

    def _extract_formhash(self, html: HTMLParser) -> Result[str]:
        formhash = html.css_first("#scbar_form > input:nth-child(2)")

        if not formhash or not (value := formhash.attributes.get("value")):
            return Result.failure("页面解析失败: 未找到formhash")
            
        logger.debug(f"成功获取Formhash: {value[:4]}****")
        return Result.success(value)

    def _submit_sign(self, html: HTMLParser) -> Result[str]:
        try:
            formhash_result = self._extract_formhash(html)
            if not formhash_result.is_success:
                return formhash_result

            form_data = {
                "formhash": formhash_result.value,
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
            return Result.failure(f"网络请求失败: HTTP {e.response.status_code}")
        except Exception as e:
            return Result.failure(f"签到请求失败: {str(e)}")

    def _extract_reward(self, resp_html: str) -> Result[str]:
        html = HTMLParser(resp_html)
        reward_message = html.css_first("#messagetext > p:nth-child(1)")

        if not reward_message:
            return Result.failure("页面解析失败: 未找到奖励信息")

        message_text = reward_message.text().strip()
        match = re.search(r"随机奖励T币\s*(\d+)", message_text)

        if not match:
            return Result.failure("页面解析失败: 未找到T币数量")

        return Result.success(f"{match.group(1)} T币")

    def execute(self) -> str:
        try:
            stats_result = self._parse_signin_stats()
            if not stats_result.is_success:
                return self._format_error(stats_result.error)

            user_name, signin_days, needs_signin, html = stats_result.value

            if needs_signin:
                reward_result = self._submit_sign(html)
                if not reward_result.is_success:
                    return self._format_error(reward_result.error)

                return self._format_success(
                    user_name=user_name,
                    reward=reward_result.value,
                    days=int(signin_days) + 1
                )
            else:
                return self._format_success(
                    user_name=user_name,
                    status="今日已签到",
                    days=int(signin_days)
                )
        except Exception as e:
            return self._format_error(f"未知错误: {str(e)}")
        finally:
            self.session.close()

    @staticmethod
    def _format_success(user_name: str, days: int, reward: str = None, status: str = None) -> str:
        message = {
            "用户": user_name,
            "奖励" if reward else "状态": reward or status,
            "连续签到": f"{days}天"
        }
        return "\n".join(f"{k}: {v}" for k, v in message.items())

    @staticmethod
    def _format_error(error: str) -> str:
        return f"状态: {error}"


class MultiAccountSignIn:
    def __init__(self, cookies_env_name: str, executor_class: type):
        self.cookies_env_name = cookies_env_name
        self.executor_class = executor_class

        self.cookies_env = os.environ.get(cookies_env_name)
        if not self.cookies_env:
            raise ValueError(f"环境变量未设置: {cookies_env_name}")

    def _get_cookies_list(self) -> Result[List[str]]:
        cookies_list = self.cookies_env.split("&")
        cookies_list = [cookie.strip() for cookie in cookies_list if cookie.strip()]

        if not cookies_list:
            return Result.failure("环境变量解析失败: 未找到有效cookie")

        logger.debug(f"账号数量: {len(cookies_list)}")
        return Result.success(cookies_list)

    @staticmethod
    def _parse_cookies(cookies_str: str) -> Result[Dict[str, str]]:
        if not cookies_str:
            return Result.failure("Cookie解析失败: 字符串为空")
        try:
            cookies_dict = dict(cookie.split("=") for cookie in cookies_str.split("; "))
            return Result.success(cookies_dict)
        except Exception as e:
            return Result.failure(f"Cookie解析失败: {str(e)}")

    def _process_account(self, cookies_str: str) -> str:
        try:
            cookies_result = self._parse_cookies(cookies_str)
            if not cookies_result.is_success:
                return self._format_error(cookies_result.error)

            signin = self.executor_class(cookies_result.value)
            return signin.execute()
        except Exception as e:
            return self._format_error(f"未知错误: {str(e)}")

    def execute_all(self) -> str:
        try:
            cookies_result = self._get_cookies_list()
            if not cookies_result.is_success:
                return self._format_error(cookies_result.error)

            messages = [self._format_header()]

            for i, cookies_str in enumerate(cookies_result.value, 1):
                messages.extend([
                    self._format_separator(i),
                    self._process_account(cookies_str)
                ])

            messages.append(self._format_footer())
            return "\n".join(messages)

        except Exception as e:
            error_msg = f"任务执行失败: {str(e)}"
            logger.error(error_msg)
            return self._format_error(error_msg)

    @staticmethod
    def _format_header() -> str:
        return "***** 开始任务 *****"

    @staticmethod
    def _format_footer() -> str:
        return "\n***** 任务结束 *****"

    @staticmethod
    def _format_separator(account_num: int) -> str:
        return f"\n----- 账号 {account_num} -----"

    @staticmethod
    def _format_error(error: str) -> str:
        return f"状态: {error}"


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
