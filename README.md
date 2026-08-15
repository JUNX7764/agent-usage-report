# Agent Usage Report ——「我用 Agent 干了啥」

盘点本机 AI Agent 的使用记录，生成一份好看、好玩、可以转发炫耀的**单文件 HTML 战绩报告**。

它是什么：一次轻松的 AI 使用回顾。
它不是：评审材料、考核依据、绩效评分——不需要你补充任何材料，不会给任何人打分。

## 30 秒上手

**这不是需要部署的软件，是给你正在用的 AI Agent 装的一个技能。**不用跑测试、不用配环境，三选一：

1. **最省事**：把本仓库链接直接发给你的 Agent（Claude Code / Proma / Hermes / Codex 等）：
   > 装一下这个 skill：https://github.com/JUNX7764/agent-usage-report ，装好了帮我生成报告
2. **手动装**：clone 到你 Agent 的 skills 目录（如 `~/.claude/skills/`、`~/.hermes/skills/`），然后对它说：
   > 看看我用 Agent 干了啥
3. **不装也行**：clone 下来，让 Agent「读这个仓库的 SKILL.md，按它帮我生成报告」

Agent 会自己问你两件事（统计哪个时间段、报告署什么名），然后全自动跑完，报告出现在桌面：`~/Desktop/{署名}_{期间标签}_我用Agent干了啥/`。

> 开发者流程（跑测试、改脚本）见文末「开发与验证」——日常使用不需要。

## 它能做什么

- **自动发现本机 AI Agent**：扫描 Proma、Claude Code、OpenCode、Hermes、Cursor、Codex、Windsurf、Aider、Cline、Kimi Code、Gemini CLI、Qwen Code、Zed、Warp 等 50+ 常见 Agent（macOS / Linux / Windows 跨平台）
- **三层防漏扫**：路径目录之外，还检测 PATH / 运行进程 / 环境变量里的 Agent 信号（在跑但没扫到数据目录会显式报警），并启发式发现目录外的疑似 Agent 数据目录让用户认领——扫描结果永远让用户确认，不静默漏报
- **识别你参与的项目**：自动区分「你做的」和「下载的开源项目」，后者默认排除
- **盘点会话成果**：按主题聚类会话，关联到项目，标注里程碑与成就
- **生成单文件 HTML 报告**：数据大字报、隐藏战绩（夜猫子时刻/周末加班/连续并肩天数）、AI 干员图鉴、成就墙、跨项目时间线
- **一键分享**：报告右上角 SHARE，复制一段有人味儿的战报文案，或调起系统分享把 HTML 发出去（全本地，零网络请求）
- **瑞士国际主义视觉**：网格点阵 + 克莱因蓝高亮 + 无衬线字体，单文件离线可开，直接截图或发文件给朋友

## Agent 会执行的流程

1. 确认时间段与报告署名（一次问完，不收集工号等身份信息）
2. 扫描本机已安装的 AI Agent（只检测存在性，不读内容）
3. 扫描项目目录，识别 AI 参与过的项目（只查痕迹，不读内容）
4. 安全扫描：排除密钥、识别潜在的 prompt 注入文件
5. 深挖会话，聚类成果，按时间段统计
6. 渲染单文件 HTML 到桌面：`~/Desktop/{署名}_{期间标签}_我用Agent干了啥/`

## 隐私承诺

- **只读**：不修改任何源文件，不复制证据，不上传、不发送、不发布任何内容
- **密钥不入报告**：安全扫描仅用于排除敏感信息，绝不回显值
- **不编造**：会话记录只能证明「讨论过/尝试过/执行过」，找不到就如实标注「未记录」
- **范围可控**：未确认的项目与会话一律不读取
- **过程文件不可见**：扫描中间产物都在 `~/.agent-usage-report/` 隐藏目录，桌面只出现最终报告

## 开发与验证

纯 Python 标准库，无第三方依赖（Python 3.8+）。

```bash
# 运行测试
python3 -m unittest discover -s tests -p 'test_*.py'
# 语法检查
python3 -m py_compile scripts/*.py
```

报告输出由确定性计算（`build_report_data.py`）+ 纯模板渲染（`render_report.py`）组成：同样的输入永远渲染出同样的页面。

## 项目结构

```
SKILL.md                                  # Skill 主文档（含完整流程与红线）
scripts/
  scan_agents.py                          # 检测本机已安装的 Agent
  scan_secrets.py                         # 密钥扫描（只用来排除，不回显）
  scan_injection.py                       # prompt 注入检测
  inventory.py                            # 项目文件清单
  collect_git_evidence.py                 # Git 代表性提交摘要
  build_report_data.py                    # 确定性统计计算
  render_report.py                        # 纯模板 HTML 渲染
references/
  agent-discovery.md                      # Agent 检测与路径映射
  source-adapters.md                      # 各家 Agent 会话读取方法（含实测可抄的片段）
  output-contract.md                      # 报告数据与输出契约
  safety-policy.md                        # 授权与隐私边界
  narrative-writing-guide.md              # 文案写作指南
tests/                                    # 单元测试
evals/                                    # 评估用例
```

## 贡献

你的 Agent 没被扫到？某个路径在你平台上不对？欢迎提 issue 或 PR 带上真实数据路径——检测目录靠社区共同维护，厂商也会随版本改存储布局。

## 免责声明

本报告仅供个人回顾与分享娱乐，不代表任何第三方评价。
