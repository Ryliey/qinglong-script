"""
name: SteamTools签到
cron: 0 6 * * *
"""

import os
import re
import requests
from typing import Dict, Optional

from logger import logger


class SteamToolsSignIn:
    def __init__(self, cookies_str: Optional[str] = None):
        self.base_url = "https://bbs.steamtools.net/plugin.php?id=dc_signin:sign"
        self.cookies = self._parse_cookies(cookies_str)

    def _parse_cookies(self, cookies_str: Optional[str] = None) -> Dict[str, str]:
        """
        解析cookies字符串为字典格式
        Args:
            cookies_str: cookies字符串，格式如 'key1=value1; key2=value2'
        Returns:
            Dict[str, str]: 解析后的cookies字典
        """
        cookies_str = os.environ.get("STEAM_COOKIES")
        if not cookies_str:
            logger.error("未设置环境变量 STEAM_COOKIES")
            exit(1)

        return dict(cookie.split("=") for cookie in cookies_str.split("; "))

    def _get_formhash(self, response: requests.Response) -> str:
        """
        从响应中提取formhash值
        Args:
            response: 网页响应对象
        Returns:
            str: 提取到的formhash值
        Raises:
            ValueError: 当未能找到formhash时抛出
        """
        formhash_match = re.search(r'name="formhash" value="(\w+)"', response.text)
        if not formhash_match:
            raise ValueError("未能获取formhash")
        return formhash_match.group(1)

    def sign(self) -> Optional[int]:
        """
        执行签到操作
        Returns:
            Optional[int]: 成功返回获得的T币数量，失败返回None
        """
        try:
            # 第一次请求获取formhash
            response = requests.post(self.base_url, cookies=self.cookies)
            response.raise_for_status()

            formhash = self._get_formhash(response)

            # 签到请求数据
            sign_data = {
                "formhash": formhash,
                "signsubmit": "yes",
                "handlekey": "signin",
                "emotid": "4",
                "referer": "https://bbs.steamtools.net/plugin.php?id=dc_signin",
                "content": "没有开心，哪里来的幸福？要开心啦",
            }

            # 发送签到请求
            sign_response = requests.post(
                self.base_url, cookies=self.cookies, data=sign_data
            )
            sign_response.raise_for_status()

            # 匹配奖励T币
            match = re.search(r"随机奖励T币(\d+)", sign_response.text)
            if match:
                t_coins = int(match.group(1))
                logger.info(f"签到成功！获得 {t_coins} T币")
                return t_coins
            else:
                logger.warning("未找到奖励T币信息")
                return None

        except requests.RequestException as e:
            logger.error(f"网络请求错误: {e}")
        except ValueError as e:
            logger.error(f"签到过程错误: {e}")

        return None


def main():
    try:
        signin = SteamToolsSignIn()
        signin.sign()
    except Exception as e:
        print(f"签到脚本执行失败: {e}")


if __name__ == "__main__":
    main()
