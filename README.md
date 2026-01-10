# AstrBot LLM 消息总结插件

一个基于 AstrBot 的群聊/私聊消息总结插件，支持按命令即时生成摘要，也可定时自动归档到 Markdown；支持展开合并转发的聊天记录参与总结。

## 功能概览
- 群内命令 `/消息总结 [条数]`：拉取最近 N 条群聊记录并用 LLM 总结。
- 私聊命令 `/群总结 [条数] [群号]`：在私聊中指定群号获取摘要（需在该群内）。
- 转发总结 `/转发总结`：对合并转发的聊天记录进行总结。
- 最大记录数、Token 上限可在 AstrBot WebUI 配置。
- 自动总结：支持定时任务、分群配置、按时间窗口分段，并将结果写入 AstrBot 数据目录 `plugins_data/astrbot_plugin_chatsummary_v2/auto_summaries/*.md` 归档。

## 安装与部署
1. 将本插件目录放入 AstrBot 的 `plugins/`，保持 `main.py`、`metadata.yaml`、`_conf_schema.json` 在根目录。
2. 重启 AstrBot 或在 WebUI 重新加载插件。
3. 在 WebUI 的"插件配置"中找到 `astrbot_plugin_chatsummary_v2`，按需调整自动总结开关。

## 使用

### 基本用法
- 群聊：`/消息总结 120`（输出以"合并转发"形式发送）
- 私聊：`/群总结 80 123456789`（输出以"合并转发"形式发送）
- 转发：直接转发聊天记录 + 命令 `/转发总结`

### 其他特性
- 如果发送合并转发的聊天记录，插件会自动展开转发节点参与总结。
- 自动总结：在配置中开启 `auto_summary.enabled` 后，自动推送到目标群并写入数据目录 `plugins_data/astrbot_plugin_chatsummary_v2/auto_summaries/*.md` 归档。
- 条数需为整数，且受 `limits.max_chat_records` 约束，超过时会自动截断。

## 配置项
- `limits.max_chat_records`：拉取的最大聊天记录条数（默认 200）。
- `limits.max_input_chars`：发送给 LLM 的上下文最大字符数，用于裁剪输入，避免超出模型上下文窗口。
- `limits.max_tokens`：LLM 输出 token 上限，用于控制回复长度。
- `auto_summary`：
  - `enabled`：是否开启定时总结。
  - `interval_minutes`：轮询间隔（分钟）。
  - `target_groups`：要自动总结的群号列表，默认包含群号 656843194。
  - `time_window_minutes`：时间窗口（分钟），用于按时间窗口分段。
  - `min_messages`：新消息少于此值时跳过总结，默认为 1。

自动总结结果会保存到 AstrBot 数据目录 `plugins_data/astrbot_plugin_chatsummary_v2/auto_summaries/` 下，文件名包含群号和时间，便于归档追溯。

## 说明
- 插件仅支持 aiocqhttp 适配器。
- 若提示未配置可用的模型，请检查 AstrBot Provider 设置。
- 如需自定义格式，可直接调整 `limits/max_input_chars`、`limits/max_tokens` 控制输入/输出长度。
- 参考laopanmemz的消息总结插件，因为需求更多而完全重构，故新开v2版而不提交pr
## 参考
- [AstrBot 官方文档](https://astrbot.app)
- [参考插件](https://github.com/laopanmemz/astrbot_plugin_chatsummary)  
