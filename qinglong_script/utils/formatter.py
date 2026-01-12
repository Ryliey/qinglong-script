"""统一的签到结果格式化模块"""


def format_header() -> str:
    return "***** 开始任务 *****"


def format_footer() -> str:
    return "\n***** 任务结束 *****"


def format_separator(account_num: int) -> str:
    return f"\n----- 账号 {account_num} -----"


def format_error(error: str) -> str:
    return f"状态: {error}"
