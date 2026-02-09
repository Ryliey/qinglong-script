## 列表

|                      脚本                      |                       介绍                       |                文档                 |
| :--------------------------------------------: | :----------------------------------------------: | :---------------------------------: |
| [steamtools.py](qinglong_script/steamtools.py) | [SteamTools论坛](https://bbs.steamtools.net)签到 | [steamtools.md](docs/steamtools.md) |
| [hifiti.py](qinglong_script/hifiti.py) | [HiFiNi](https://hifiti.com)签到 | [hifiti.md](docs/hifiti.md) |


## 使用

1. **添加依赖：**`青龙面板->依赖管理->python3->创建依赖->名称` 中填入，并开启 “**自动拆分**”。

    ```
    httpx
    curl-cffi
    selectolax
    ```

2. **拉取仓库：**`青龙面板->订阅管理->创建订阅->名称` 中填入。

    ```
    ql repo https://github.com/Ryliey/qinglong-script.git "" "__init__|logger|result|formatter" "notify|logger|result|formatter" "main"
    ```

    - 定时规则

    ```
    0 0 5 * * ?
    ```
