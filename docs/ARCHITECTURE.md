# AI Media Factory — 架构说明书(开发宪法)

> 本文件是项目唯一权威。所有开发对照它,Claude 不自由发挥。新增/修改必先回到本文件。

## 0. 一句话定位

> 一个完全自动化的 AI 自媒体生产平台,通过 Agent + Skills + Workflow 实现图书号、电影号、知识号等内容的批量生成。

## 1. 系统目标

不是开发一个图书号,而是 **AI Media Factory**。图书号只是第一个 Workflow。
未来支持:Book / Movie / History / Finance / Podcast 等。

- 整个系统采用 **Agent + Skills + Workflow** 架构
- 任何 Workflow 只能通过组合 Skill 完成
- **Core 永远不能知道业务逻辑**,所有业务逻辑全部放 Skill

## 2. 六层架构(领域驱动 + 插件化)

| 层 | 职责 | 位置 |
|---|---|---|
| **Core** | 调度(读 workflow / 执行 skill / 存 state / 日志 / 异常恢复),零业务 | `app/core/` |
| **Skill** | 一个能力,一个职责,可独立测试 | `app/skills/` |
| **Workflow** | Skill 的编排,YAML 配置,改 yaml 不改代码 | `workflows/*.yaml` |
| **Provider** | 封装具体第三方(Edge TTS / 火山 / HyperFrames / Remotion / ffmpeg),换供应商不影响 Skill | 各 Skill 内部模块(如 `voice_master/ffmpeg.py`) |
| **Preset** | 风格 / 音频 / 视频主题,全配置化 | `config/*.yaml`、`presets/`、各 Skill `presets/` |
| **State** | 全流程唯一数据对象,支持序列化和断点恢复 | `app/core/state.py` |

## 3. 12 条开发原则

1. **Skill 单一职责** —— 一个 Skill 只做一件事(ResearchSkill 只搜集,不写文案 / 不生成视频 / 不调其它 Skill)
2. **Skill 可替换** —— VoiceSkill 今天 EdgeTTS,以后 ElevenLabs / FishSpeech / CosyVoice,不影响其它模块
3. **Core 无业务** —— Core 只读 Workflow / 执行 Skill / 保存 State / 记录日志 / 异常恢复
4. **Workflow 全 yaml 配置化** —— Book / Movie / History 全放 `workflows/*.yaml`,不写死
5. **Prompt 外置** —— 所有 prompt 放 `prompts/`,禁止写在 python
6. **配置全 yaml** —— `voice.yaml video.yaml book.yaml theme.yaml`,禁止硬编码
7. **Skill 输入输出 VideoState** —— 禁止自己保存状态
8. **断点恢复** —— Research / Script 已完成、Voice 失败 → 重跑只续 Voice,不重跑已完成

> 原则 9-12 见下方 QA(§10)、日志(§11)、插件(§12)、最终目标(§13)。

## 4. 目录

```
ai-media-factory/
├── app/
│   ├── core/            agent.py workflow.py scheduler.py state.py logger.py event.py
│   ├── skills/          research/ script/ voice/ voice_master/ subtitle/
│   │                    storyboard/ hyperframes/ render/ qa/ publish/
│   ├── workflows/ prompts/ presets/   (app 内部占位)
├── workflows/           book.yaml movie.yaml history.yaml      ← YAML 配置(原则4)
├── prompts/             research.md script.md qa.md            ← Prompt 外置(原则5)
├── presets/             voice/ theme/
├── config/              voice.yaml video.yaml book.yaml theme.yaml  ← 全 yaml(原则6)
├── plugins/             movie/ history/ finance/ wechat/ douyin/ xiaohongshu/ youtube/ tiktok/
├── assets/ output/ tests/ docs/
└── main.py
```

## 5. State(全流程唯一,§第四部分)

`VideoState` 字段:`book topic research script voice_path subtitle_path storyboard html_path video_path publish_url logs status`

- 任何 Skill:输入 `VideoState` → 修改 → 返回 `VideoState`
- `save(path) / load(path)` 序列化,用于断点恢复

## 6. Skill 清单(10 个,禁止 BookSkill / MovieSkill)

ResearchSkill · ScriptSkill · VoiceSkill · VoiceMasterSkill · SubtitleSkill ·
StoryboardSkill · HyperFramesSkill · RenderSkill · QASkill · PublishSkill

> Book / Movie 是 Workflow,不是 Skill。

## 7. Workflow(§第六部分)

Book = `Research→Script→Voice→VoiceMaster→Subtitle→Storyboard→HyperFrames→Render→QA→Publish`
Movie / History 除前两个 Skill 外,其它全复用。改 `workflows/*.yaml` 即改流程,不改 python。

## 8. Voice Master 独立(§第七部分)

`app/skills/voice_master/` = `preset.py` + `ffmpeg.py` + `processor.py` + `presets/{book,podcast,movie}.json`
永远 `VoiceSkill → VoiceMasterSkill` 分开。

## 9. HyperFrames 子流程(§第八部分)

视频生成必须走:`Storyboard → HTML Generator → Asset Manager → Subtitle Manager → Timeline Builder → Render`
Storyboard / Render 是独立 Skill,中间四步在 `HyperFramesSkill` 内部。Remotion 同理。

## 10. QA(§第九部分,9 项检查)

字幕重叠 / 字幕超时 / 字幕超屏 / 字体缺失 / 图片不存在 / 音频为空 / HTML 报错 / FFmpeg 失败 / MP4 不可播放

## 11. 日志(§第十部分)

每个 Skill:`START → SUCCESS/FAILED → TIME → OUTPUT`
格式:`[Skill名] START / SUCCESS / 耗时 Xs / 输出 xxx`,见 `app/core/logger.py`。

## 12. 插件化(§第十一部分)

`plugins/{movie,history,finance,wechat,douyin,xiaohongshu,youtube,tiktok}/` —— 复制即扩展,不改 Core。

## 13. 最终目标(§第十二部分)

一句话:"制作《活着》的30秒抖音视频" → Agent 自动跑完整链 → 结束

## 14. V0.1 假实现边界

- 架构 / 接口 / 目录 / 配置 **100% 按本规范落地**
- Skill **实现先假**(只填 state 字段),后续 Step 逐个替换真实能力
- V0.1 唯一目标:`python main.py "活着"` 跑通 10 Skill → `output/book.mp4` + 断点恢复

## 15. 规范遵从映射(12 部分 → 落地)

| 规范部分 | 落地位置 |
|---|---|
| 1 系统目标 | 本文件 §1-2 + `app/core/agent.py` |
| 2 开发原则 | 本文件 §3 + Core/Skill 代码体现 |
| 3 目录 | 项目根目录结构 |
| 4 State | `app/core/state.py` |
| 5 Skill | `app/skills/*/` |
| 6 Workflow | `workflows/book.yaml` + `app/core/workflow.py` |
| 7 Voice Master | `app/skills/voice_master/` |
| 8 HyperFrames | `app/skills/hyperframes/` 子模块 |
| 9 QA | `app/skills/qa/` |
| 10 日志 | `app/core/logger.py` |
| 11 插件 | `plugins/` |
| 12 最终目标 | `main.py` 端到端 |
