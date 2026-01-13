"""
name: hifiti 签到
cron: 0 6 * * *
"""

from ast import List
import os
import re
import httpx
from typing import Dict
from selectolax.parser import HTMLParser

from utils.result import Result
from utils.logger import logger
from utils.formatter import (
    format_header,
    format_footer,
    format_separator,
    format_error,
)


class Hifiti:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0",
        "Accept-Language": "zh-CN,zh;q=0.8",
        "Referer": "https://hifiti.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(self, cookies_dict: Dict[str, str]):
        self._base_url = "https://hifiti.com"
        self._sign_url = f"{self._base_url}/sg_sign.htm"

        self.client = httpx.Client(
            headers=self.headers,
            cookies=cookies_dict,
            timeout=10,
        )

    def _parse_signin_stats(self) -> Result[str]:
        try:
            resp = self.client.get(self._sign_url)
            resp.raise_for_status()
            html = HTMLParser(resp.text)

            login_link = html.css_first(".icon-plus")
            if login_link:
                return Result.failure("Cookie已失效，请重新获取")

            user_name_elem = html.css_first(".username > a:nth-child(1)")
            user_name = user_name_elem.text() if user_name_elem else "未知用户"

            return Result.success(user_name)
        except httpx.RequestError as e:
            return Result.failure(f"网络请求失败: {str(e)}")
        except (KeyError, AttributeError) as e:
            return Result.failure(f"页面解析失败: {str(e)}")
        except Exception as e:
            return Result.failure(f"未知错误: {str(e)}")

    def _submit_sign(self) -> Result[str]:
        try:
            resp = self.client.post(self._sign_url)
            resp.raise_for_status()

            return self._extract_signin_stats(resp)
        except httpx.HTTPStatusError as e:
            return Result.failure(f"网络请求失败: HTTP {e.response.status_code}")
        except Exception as e:
            return Result.failure(f"签到请求失败: {str(e)}")

    def _extract_signin_stats(self, resp: httpx.Response) -> Result[str]:
        data = resp.json()

        if not data:
            return Result.failure("未找到奖励信息")

        message_text = data.get("message", "")
        if "今天已经签过啦！" in message_text:
            return Result.success("今日已签到")

        match = re.search(r"(?<=总奖励)(\d+)", message_text)
        if not match:
            return Result.failure(f"未找到奖励数量: {message_text}")

        return Result.success(f"{match.group(1)}金币")

    def sign_in(self) -> str:
        try:
            stats_result = self._parse_signin_stats()
            if not stats_result.is_success:
                return format_error(stats_result.error)
            user_name = stats_result.value

            _signin_result = self._submit_sign()
            if not _signin_result.is_success:
                return format_error(_signin_result.error)

            if _signin_result.value != "今日已签到":
                return self._format_success(
                    user_name=user_name,
                    result=_signin_result.value,
                )
            else:
                return self._format_success(user_name=user_name, status="今日已签到")
        except Exception as e:
            return format_error(f"签到失败: {str(e)}")
        finally:
            self.client.close()

    @staticmethod
    def _format_success(user_name: str, result: str = None, status: str = None) -> str:
        message = {
            "用户": user_name,
            "奖励" if result else "状态": result or status,
        }
        return "\n".join(f"{k}: {v}" for k, v in message.items())


class AccountTaskRunner:
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
            cookies_dict = dict(
                cookie.split("=", 1) for cookie in cookies_str.split("; ")
            )
            return Result.success(cookies_dict)
        except Exception as e:
            return Result.failure(f"Cookie解析失败: {str(e)}")

    def _process_account(self, cookies_str: str) -> str:
        try:
            cookies_result = self._parse_cookies(cookies_str)
            if not cookies_result.is_success:
                return format_error(cookies_result.error)

            signin = self.executor_class(cookies_result.value)
            return signin.sign_in()
        except Exception as e:
            return format_error(f"未知错误: {str(e)}")

    def run(self) -> str:
        try:
            cookies_result = self._get_cookies_list()
            if not cookies_result.is_success:
                return format_error(cookies_result.error)

            messages = [format_header()]

            for i, cookies_str in enumerate(cookies_result.value, 1):
                messages.extend(
                    [format_separator(i), self._process_account(cookies_str)]
                )

            messages.append(format_footer())
            return "\n".join(messages)

        except Exception as e:
            error_msg = f"任务执行失败: {str(e)}"
            logger.error(error_msg)
            return format_error(error_msg)


def main():
    multi_signin = AccountTaskRunner(
        cookies_env_name="HIFITI_COOKIES",
        executor_class=Hifiti,
    )
    message = multi_signin.run()
    print(message)
    QLAPI.notify("Hifiti 签到", message)


if __name__ == "__main__":
    main()
