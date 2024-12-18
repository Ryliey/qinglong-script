## 列表

|                             脚本                             |                       介绍                       |                             文档                             |
| :----------------------------------------------------------: | :----------------------------------------------: | :----------------------------------------------------------: |
| [pt-checkin.py](https://github.com/Ryliey/qinglong-script/blob/main/qinglong_script/pt-checkin.py) |              PT站签到，支持多个站点              | [pt-checkin.md](https://github.com/Ryliey/qinglong-script/blob/main/docs/pt-checkin.md) |
| [steamtools.py](https://github.com/Ryliey/qinglong-script/blob/main/qinglong_script/steamtools.py) | [SteamTools论坛](https://bbs.steamtools.net)签到 |                                                              |



## 使用

1. 添加依赖，`青龙面板->依赖管理->python3->创建依赖->名称` 填入。

```
requests
```

2. 拉取仓库，`青龙面板->订阅管理->创建订阅->名称` 中填入。

```
ql repo https://github.com/Ryliey/qinglong-script.git "" "__init__|logger" "notify|logger" "main"
```

- 定时规则

```
0 0 5 * *
```
