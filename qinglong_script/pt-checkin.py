import os
import re
import requests
from typing import Dict, Optional, List

from logger import logger


class SiteCheckin:
    """
    站点签到类，处理单个站点的签到逻辑
    """

    def __init__(self, site_config: Dict[str, str]):
        """
        初始化站点签到类

        :param site_config: 包含站点配置信息的字典
                            应包含 'url', 'cookies_env_var', 'checkin_path'
        """
        self.site_name = site_config.get("name", "未知站点")
        self.base_url = site_config["url"]
        self.checkin_path = site_config.get("checkin_path", "/attendance.php")
        self.cookies = self._get_cookies(site_config["cookies_env_var"])

        # 签到结果解析正则表达式配置
        self.result_pattern = site_config.get(
            "result_pattern",
            (
                r"这是您的第 <b>(\d+)</b> 次签到，"
                r"已连续签到 <b>(\d+)</b> 天，"
                r"本次签到获得 <b>(\d+)</b> 个.*?。"
                r"你目前拥有补签卡 <b>(\d+)</b> 张"
            ),
        )

    def _get_cookies(self, cookies_env_var: str) -> Dict[str, str]:
        """
        从环境变量获取cookies

        :param cookies_env_var: 存储cookies的环境变量名
        :return: 解析后的cookies字典
        """
        cookies_str = os.environ.get(cookies_env_var)
        if not cookies_str:
            logger.error(f"未设置环境变量 {cookies_env_var}")
            return {}

        try:
            return dict(cookie.split("=", 1) for cookie in cookies_str.split("; "))
        except Exception as e:
            logger.error(f"{self.site_name} cookies解析失败: {e}")
            return {}

    def parse_signin_result(self, html_content: str) -> Optional[Dict[str, str]]:
        """
        解析签到结果

        :param html_content: 签到页面的HTML内容
        :return: 解析后的签到详细信息字典
        """
        try:
            match = re.search(self.result_pattern, html_content)

            if not match:
                logger.warning(f"{self.site_name} 签到解析失败：未找到匹配的签到信息")
                # 调试：保存未匹配的页面内容
                # self._save_debug_html(html_content)
                return None

            total_times, continuous_days, bonus, makeup_cards = match.groups()
            return {
                "site_name": self.site_name,
                "total_times": total_times,
                "continuous_days": continuous_days,
                "bonus": bonus,
                "makeup_cards": makeup_cards,
            }

        except Exception as e:
            logger.error(f"{self.site_name} 签到解析发生错误: {e}")
            return None

    def _save_debug_html(self, html_content: str):
        """
        保存调试用的HTML内容

        :param html_content: 要保存的HTML内容
        """
        debug_file = f"{self.site_name}_debug.html"
        try:
            with open(debug_file, "w", encoding="utf-8") as file:
                file.write(html_content)
            logger.info(f"调试信息已保存到 {debug_file}")
        except Exception as e:
            logger.error(f"保存调试文件失败: {e}")

    def sign(self) -> Optional[Dict[str, str]]:
        """
        执行签到操作

        :return: 签到结果详细信息
        """
        if not self.cookies:
            logger.error(f"{self.site_name} 未配置有效cookies")
            return None

        try:
            response = requests.get(
                f"{self.base_url}{self.checkin_path}", cookies=self.cookies, timeout=10
            )
            response.raise_for_status()

            return self.parse_signin_result(response.text)

        except requests.RequestException as e:
            logger.error(f"{self.site_name} 签到请求失败: {e}")
            return None


class PTSiteManager:
    """
    PT站点签到管理器，负责管理多个站点的签到流程和通知
    """

    def __init__(self):
        """
        初始化PTSiteManager，获取启用的站点配置
        """
        self.enabled_sites = self._get_enabled_sites()
        self.success_sites: List[Dict[str, str]] = []
        self.failed_sites: List[str] = []

    def _get_enabled_sites(self) -> List[Dict[str, str]]:
        """
        获取环境中启用的站点配置

        :return: 站点配置列表
        """
        # 预定义的站点配置
        all_sites = [
            {
                "name": "HDPT",
                "url": "https://hdpt.xyz",
                "cookies_env_var": "HDPT_COOKIES",
            },
            {
                "name": "PTLGS",
                "url": "https://ptlgs.org",
                "cookies_env_var": "PTLGS_COOKIES",
            },
            {
                "name": "RAINGFH",
                "url": "https://raingfh.top",
                "cookies_env_var": "RAINGFH_COOKIES",
            },
        ]

        # 从环境变量获取启用的站点
        enabled_sites_str = os.environ.get("ENABLED_SITES", "")

        if not enabled_sites_str:
            logger.warning("未设置 ENABLED_SITES 环境变量，将使用所有预配置站点")
            return all_sites

        # 解析启用的站点
        enabled_sites = [site.strip() for site in enabled_sites_str.split(",")]

        return [site for site in all_sites if site["name"] in enabled_sites]

    def _perform_checkin(self, site_config: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
        对单个站点执行签到

        :param site_config: 站点配置信息
        :return: 签到结果详细信息
        """
        try:
            site_checkin = SiteCheckin(site_config)
            return site_checkin.sign()
        except Exception as e:
            logger.error(f"{site_config['name']} 签到发生未知错误: {e}")
            return None

    def execute_checkins(self):
        """
        执行所有启用站点的签到操作
        """
        if not self.enabled_sites:
            logger.error("没有可用的站点配置")
            return

        for site_config in self.enabled_sites:
            result = self._perform_checkin(site_config)

            if result:
                self.success_sites.append(result)
            else:
                self.failed_sites.append(site_config["name"])

    def _format_success_notification(self, site_result: Dict[str, str]) -> str:
        """
        格式化单个站点成功签到的通知信息

        :param site_result: 签到结果详细信息
        :return: 格式化的通知字符串
        """
        return (
            f"✅ {site_result['site_name']} 签到成功！\n"
            f"🌟 积分: {site_result['bonus']}\n"
            f"📅 连续签到: {site_result['continuous_days']} 天\n"
            f"🎫 补签卡: {site_result['makeup_cards']} 张"
        )

    def send_notification(self):
        """
        发送签到通知
        """
        if not self.success_sites and not self.failed_sites:
            return

        # 构建通知内容
        notify_title = "PT站签到结果"
        notify_content = []

        # 处理成功的站点
        for site_result in self.success_sites:
            notify_content.append(self._format_success_notification(site_result))

        # 处理失败的站点
        if self.failed_sites:
            notify_content.append(f"❌ 签到失败站点: {', '.join(self.failed_sites)}")

        # 发送通知
        full_notify_content = "\n\n".join(notify_content)
        print(full_notify_content)
        QLAPI.notify(notify_title, full_notify_content)


def main():
    manager = PTSiteManager()
    manager.execute_checkins()
    manager.send_notification()


if __name__ == "__main__":
    main()
