# ✨ HER — Human Emotion Resonance (v2.0)

[![GitHub release](https://img.shields.io/github/v/release/kghggt/HER-Human-Emotion-Resonance?color=blueviolet)](https://github.com/kghggt/HER-Human-Emotion-Resonance/releases/tag/v2.0)
[![License](https://img.shields.io/github/license/kghggt/HER-Human-Emotion-Resonance?color=blue)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-0078d7.svg)](README.md)

**HER (Human Emotion Resonance)** 是一款基于 PyQt5 与本地嵌入式 **GPT-SoVITS 语音引擎** 构建的 **AI 情感伴侣聊天桌面应用**。后台搭载强大的 **DeepSeek-V3** 大语言模型，带给你兼具视觉、文字与声音的沉浸式伴侣陪伴体验。

---

## 🚀 HER v2.0 重大更新说明

> **HER v2.0** 是一次面向未来的全方位重构版本，在**视觉美化**、**系统架构**以及**TTS人声交互**上实现了质的飞跃。

### 🎨 1. 极光暗黑玻璃拟态 UI (Premium Interface)
* **极光发光动效**：AI 头像与发送按钮引入了极具未来感的极光微光阴影（Glow Effect），让界面呼吸律动。
* **物理滑入动画**：消息气泡新增 `300ms OutCubic` 物理曲线滑入效果，多维呈现，交互极其灵动。
* **高级调色板**：主窗口重绘为深邃优雅的星空黑（`#080818`），搭配紫靛粉三色渐变的用户气泡，极具现代科技质感。
* **精美设置窗口**：选项选项卡增加了生动的 Emoji 标识，重新调配了带渐变滑槽的创意度滑块。

### 🔊 2. 智能动作/情绪文字 TTS 净化 (Action-Filter Technology)
* **独创的降噪净化技术**：大模型在扮演角色时常常输出括号描述动作或表情（如 `（害羞地低头）嗯…你说的对啦～` 或 `*摸摸头* 别担心`）。
* **完美呈现，自然阅读**：v2.0 独创正则匹配过滤，**在聊天气泡中完整保留括号描述以供阅读，但在发送给 TTS 合成语音前自动将它们完美净化剔除**，防止 TTS 机械性念出括号，实现宛如真人日常对话般流畅体验。

### 🚀 3. 高 DPI 视网膜缩放适配 (Retina Display Ready)
* 全面接入 Qt High DPI 缩放算法（`AA_EnableHighDpiScaling`），彻底告别旧版本在 2K / 4K 高分辨率显示器下界面字体与图标模糊的问题，字字锐利。

### 📂 4. 现代模块化架构重塑 (Modular Architecture)
* 告别了 v1.0 单文件巨石（597行）的杂乱无章。v2.0 将代码优雅地解耦为 **5 大高内聚低耦合模块**，使二次开发与功能扩展无比清爽：
  * `ai_client.py`：管理 OpenAI 兼容 API 请求与线程安全的对话历史。
  * `tts_service.py`：负责 GPT-SoVITS 子进程的轮询生命周期、语音合成与异步播放。
  * `widgets.py`：高颜值的自定义 UI 组件（气泡、打字等待状态、更新说明等）。
  * `chat_window.py`：主聊天窗口与安全的异步信号槽通信。
  * `assistant.py`：纯净轻量（43行）的引导与启动入口。

---

## 📅 版本更新日志 (Changelogs)

点击下方版本链接，可查阅各版本详细的新增特性与技术说明文档：

* 🚀 [**HER v2.0.0**](docs/changelogs/v2.0.md) — 模块化重构、极光发光暗黑 UI、智能 TTS 括号动作过滤、高 DPI 支持（2026-05-25）
* 📝 [**HER v1.0.0**](docs/changelogs/v1.0.md) — 首发版文字聊天伴侣、GPT-SoVITS 本地语音合成基础框架（2026-05-18）

---

## 📦 版本分发说明

| 版本 | 包含内容 | 适用场景 | 文件大小 |
|---|---|---|---|
| **轻量版** (`AI伴侣_v1.0_lite.zip`) | 纯文字聊天，即开即用 | 适合仅需文本聊天的轻度体验 | ~100 MB |
| **完整版** (`AI伴侣_v1.0_full.*.zip`) | 包含 GPT-SoVITS 独立本地语音运行环境与模型权重 | **完整体验**，支持极致的本地真人声线合成 | ~4.8 GB |

### 完整版分卷解压缩指令

完整版因体积较大采用分卷压缩，解压前请在分卷所在目录下打开 **PowerShell** 运行以下命令进行合并：

```powershell
cmd /c "copy /b AI伴侣_v1.0_full.zip.aa + AI伴侣_v1.0_full.zip.ab + AI伴侣_v1.0_full.zip.ac + AI伴侣_v1.0_full.zip.ad AI伴侣_v1.0_full.zip"
```

---

## ⚡ 快速开始 (开发模式)

### 1. 安装依赖
确保本地 Python 环境为 3.8+，在根目录下执行：
```bash
pip install -r requirements.txt
```

### 2. 启动应用
* **Windows 脚本快捷启动**：双击运行 `start.bat` 或 `start.ps1`
* **命令行启动**：
```bash
python assistant.py
```

### 3. 配置
首次启动将自动弹出**配置面板**。你只需要填写由 SiliconFlow 等平台提供的 **DeepSeek-V3 API Key** 即可开启对话！

---

## 🛠️ 技术栈

* **LLM**: DeepSeek-V3 (via SiliconFlow / OpenAI 兼容 API)
* **TTS**: GPT-SoVITS (本地子进程独立常驻，Port `9880`)
* **GUI Framework**: PyQt5 (Fusion Style + Custom Stylesheet)
* **Packaging**: PyInstaller

---

## 📜 许可证

本项目基于 [MIT License](LICENSE) 许可开源。
