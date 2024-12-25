"""
name: SteamTools签到
cron: 0 6 * * *
"""

import os
import re
import requests
from typing import Dict, Optional, Tuple

from logger import logger


class SteamToolsSignIn:
    """
    SteamTools论坛签到类
    """

    def __init__(self):
        self.base_url = "https://bbs.steamtools.net/plugin.php?id=dc_signin:sign"
        self.cookies = self._get_cookies()
        self.site_name = "SteamTools"

    def _get_cookies(self) -> Dict[str, str]:
        """
        从环境变量获取并解析cookies

        :return: 解析后的cookies字典
        """
        cookies_str = os.environ.get("STEAMTOOLS_COOKIES")
        if not cookies_str:
            logger.error("未设置环境变量 STEAMTOOLS_COOKIES")
            return {}

        try:
            return dict(cookie.split("=", 1) for cookie in cookies_str.split("; "))
        except Exception as e:
            logger.error(f"Cookies解析失败: {e}")
            return {}

    def _get_formhash(self, response: requests.Response) -> str:
        """
        从响应中提取formhash值

        :param response: 网页响应对象
        :return: 提取到的formhash值
        :raises ValueError: 当未能找到formhash时抛出
        """
        formhash_match = re.search(r'name="formhash" value="(\w+)"', response.text)
        if not formhash_match:
            raise ValueError("未能获取formhash")
        return formhash_match.group(1)

    def _parse_signin_result(self, html_content: str) -> Optional[int]:
        """
        解析签到结果，获取奖励T币数量

        :param html_content: 签到响应的HTML内容
        :return: 获得的T币数量，失败返回None
        """
        match = re.search(r"随机奖励T币(\d+)", html_content)
        if match:
            return int(match.group(1))
        return None

    def sign(self) -> Tuple[bool, Optional[int]]:
        """
        执行签到操作

        :return: (是否成功的布尔值, 获得的T币数量)
        """
        if not self.cookies:
            logger.error("未配置有效cookies")
            return False, None

        try:
            # 第一次请求获取formhash
            response = requests.post(self.base_url, cookies=self.cookies, timeout=10)
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
                self.base_url, cookies=self.cookies, data=sign_data, timeout=10
            )
            sign_response.raise_for_status()

            t_coins = self._parse_signin_result(sign_response.text)
            if t_coins is not None:
                logger.info(f"签到成功！获得 {t_coins} T币")
                return True, t_coins

            logger.warning("签到失败：未找到奖励T币信息")
            return False, None

        except requests.RequestException as e:
            logger.error(f"网络请求错误: {e}")
        except ValueError as e:
            logger.error(f"签到过程错误: {e}")
        except Exception as e:
            logger.error(f"未知错误: {e}")

        return False, None

    def format_notification(self, success: bool, t_coins: Optional[int] = None) -> str:
        """
        格式化通知内容

        :param success: 签到是否成功
        :param t_coins: 获得的T币数量
        :return: 格式化后的通知内容
        """
        if success and t_coins is not None:
            return f"✅ {self.site_name} 签到成功！\n" f"🪙 获得T币: {t_coins}"
        else:
            return f"❌ {self.site_name} 签到失败！"


def main():
    """
    主函数：执行签到并发送通知
    """
    try:
        signin = SteamToolsSignIn()
        success, t_coins = signin.sign()

        # 构建通知内容
        notify_title = "SteamTools签到结果"
        notify_content = signin.format_notification(success, t_coins)

        # 发送通知
        print(notify_content)
        QLAPI.notify(notify_title, notify_content)

    except Exception as e:
        error_msg = f"签到脚本执行失败: {e}"
        logger.error(error_msg)
        QLAPI.notify("SteamTools签到失败", error_msg)


if __name__ == "__main__":
    main()
