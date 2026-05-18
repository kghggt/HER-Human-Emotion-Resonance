# HER — Human Emotion Resonance

AI 伴侣聊天助手，支持文字对话 + 语音合成（GPT-SoVITS）。

## 版本

| 版本 | 说明 | 大小 |
|---|---|---|
| **轻量版** (`AI伴侣_v1.0_lite.zip`) | 纯文字聊天，即开即用 | ~100 MB |
| **完整版** (`AI伴侣_v1.0_full.*.zip`) | 含 TTS 语音引擎，需下载 4 个分卷 | ~4.8 GB |

## 完整版分卷解压

```powershell
# Windows PowerShell
cmd /c "copy /b AI伴侣_v1.0_full.zip.aa + AI伴侣_v1.0_full.zip.ab + AI伴侣_v1.0_full.zip.ac + AI伴侣_v1.0_full.zip.ad AI伴侣_v1.0_full.zip"
```

## 快速开始

- **轻量版**：解压 `AI伴侣_v1.0_lite.zip` → 双击 `AI_Companion.exe`
- **完整版**：合并分卷得到 `AI伴侣_v1.0_full.zip` → 解压 → 双击 `AI_Companion.exe`

首次运行自动弹出设置界面，填写 API Key 即可开始聊天。

## 技术栈

- LLM: DeepSeek-V3 (via SiliconFlow / OpenAI 兼容 API)
- TTS: GPT-SoVITS
- GUI: PyQt5
- 打包: PyInstaller

## License

MIT
