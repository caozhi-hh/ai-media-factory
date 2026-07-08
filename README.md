# AI Media Factory 📚→🎬

**输入一本书名 → 自动生成一条 30 秒抖音讲书视频。**

一条命令，跑完 10 步流水线：搜资料 → 写文案 → 配音 → 声音优化 → 分镜 → 字幕 → 配图 → 渲染 → 质检 → 发布。

```
《百年孤独》  →  book.mp4 (27秒, 720×960, 中英字幕)
```

---

## ✨ 特性

- **全自动流水线** — 一本书名进，一个 MP4 出，中间无需人工干预
- **金句文案** — LLM 生成有文学质感的口播稿（金句开头、浓缩全书精华、共情结尾）
- **高质量配音** — 火山引擎语音合成大模型（深夜博主、渊博小叔等预设音色），支持声音复刻克隆音色
- **专业声音处理** — FFmpeg 高通滤波 + 响度归一化，配音清晰无杂音
- **AI 配图** — MiniMax 海螺图像（默认）/ CogView / Pollinations 多级回退
- **中英双语字幕** — 根据最终音频时间轴精确生成，淡入淡出动画
- **智能分镜** — 根据文案自动拆分场景，每段配独立画面
- **断点恢复** — 每步成功后存盘，失败可 `--resume` 续跑，不重复劳动
- **无水印** — 全程不添加任何水印或"AI生成"字样

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install edge-tts imageio-ffmpeg pillow numpy scipy websockets requests
```

需要 FFmpeg（项目使用 imageio-ffmpeg 捆绑版，无需单独安装）。

### 2. 配置密钥

```bash
cp config/.env.example .env
# 编辑 .env，至少填入 ZHIPUAI_API_KEY 和 VOLC_TTS_*
```

### 3. 生成视频

```bash
python main.py "百年孤独"
```

完成后视频在 `output/book.mp4`。

### 4. 断点续跑

```bash
python main.py "百年孤独" --resume
```

从 `output/state.json` 断点继续，已完成的步骤自动跳过。

---

## 🏗️ 架构

```
输入书名
   ↓
Research    搜集资料（作者/简介/核心观点/金句）
   ↓
Script      LLM 写 120-150 字口播稿（金句开头）
   ↓
Voice       火山引擎 TTS 合成配音
   ↓
VoiceMaster FFmpeg 高通滤波 + 响度归一化
   ↓
Storyboard  拆分场景（每段配一句文案 + 图片提示词）
   ↓
Subtitle    中英双语字幕（基于最终音频时间轴）
   ↓
HyperFrames MiniMax 生成场景配图
   ↓
Render      FFmpeg 合成视频（Ken Burns 缓慢缩放 + BGM 混音）
   ↓
QA          质量检查
   ↓
Publish     输出 MP4
```

### 目录结构

```
ai-media-factory/
├── main.py                  # 入口
├── .env                     # 密钥（不进 git）
├── config/                  # 配音/视频/主题配置
│   ├── voice.yaml           #   配音 provider + 音色 + 语速
│   └── video.yaml           #   视频参数
├── prompts/                 # LLM 提示词
│   ├── research.md
│   └── script.md            #   文案生成 prompt（金句风格）
├── workflows/
│   └── book.yaml            # 讲书工作流（10 步）
├── app/
│   ├── core/                # Agent + Scheduler + State
│   ├── skills/              # 10 个技能模块
│   │   ├── research/        #   资料搜集
│   │   ├── script/          #   文案生成
│   │   ├── voice/           #   配音
│   │   ├── voice_master/    #   声音优化
│   │   ├── storyboard/      #   分镜
│   │   ├── subtitle/        #   字幕
│   │   ├── hyperframes/     #   HTML + 配图
│   │   ├── render/          #   渲染
│   │   ├── qa/              #   质检
│   │   └── publish/         #   发布
│   └── providers/           # 第三方服务接入
│       ├── volcengine_tts.py    # 火山引擎 TTS（预设音色）
│       ├── voice_clone_tts.py   # 火山引擎声音复刻（克隆音色）
│       ├── minimax_gen.py       # MiniMax 图片生成
│       ├── free_gen.py          # 免费图片生成（Pollinations 回退）
│       └── llm.py               # 智谱 GLM 文案生成
├── assets/                  # 素材（BGM、字体、场景图）
├── output/                  # 生成产物
└── tests/
```

---

## ⚙️ 配置

### 换配音音色

编辑 `config/voice.yaml`：

```yaml
provider: volcengine          # volcengine=预设音色 / voice_clone=克隆音色 / edge_tts=免费
model: zh_male_shenyeboke_moon_bigtts   # 深夜博主（推荐讲书）
speed_ratio: 1.1              # 语速（0.5-2.0）
```

推荐男声：
- `zh_male_shenyeboke_moon_bigtts` — 深夜博主（沉稳，推荐讲书）
- `zh_male_yuanboxiaoshu_uranus_bigtts` — 渊博小叔（温润儒雅）

### 换图片生成模型

图片生成优先级在 `app/skills/hyperframes/asset_manager.py`：
1. MiniMax（默认，质量最高）
2. Pollinations（免费回退）
3. CogView（智谱，最后手段）

### 换 BGM

替换 `assets/bgm.aac`（建议 20-30 秒，纯音乐）。

---

## 🔑 需要的 API 密钥

| 服务 | 用途 | 是否必需 | 获取地址 |
|------|------|---------|---------|
| 智谱 AI | 文案生成 + 图片回退 | ✅ 必需 | open.bigmodel.cn |
| 火山引擎 | 配音 | ✅ 必需 | console.volcengine.com/speech |
| MiniMax | 配图 | 推荐 | platform.minimaxi.com |
| 火山声音复刻 | 克隆音色 | 可选 | 控制台训练后填入 |

---

## 📖 设计理念

本项目遵循"先跑通，再优化"的原则：

1. **单类清晰** — 第一版只做"书→视频"一件事，做到极致
2. **流水线思维** — 所有账号（书/电影/财经）本质是同一条流水线，换 Workflow 即可
3. **Provider 可替换** — 换 TTS/图片模型只改 Provider，不动业务逻辑
4. **断点恢复** — 每步存盘，失败不重来

---

## 📝 License

MIT
