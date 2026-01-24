# Canopywave Dify 插件测试与发布指南

本指南将帮助您进行插件的本地开发调试以及最终的打包发布。

## ⚠️ 重要前提

本插件要求 **Python 3.10+** (推荐 3.12)。
由于系统自带 Python 版本较老，**必须使用虚拟环境**运行。

---

## 一、本地在线调试 (Remote Debugging)

用于在开发过程中实时测试代码修改，无需反复打包上传。

### 1. 准备环境

确保您已位于项目根目录：

```bash
cd /Users/lihui/canopywave
```

### 2. 启动插件

**必须**执行以下两条命令（缺一不可）：

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 启动主程序
python main.py
```

> **成功标志**：
> 终端显示 `INFO:dify_plugin.plugin:Installed model: canopywave`，且进程保持运行不退出。

### 3. 在 Dify 中测试

1.  打开 Dify 平台。
2.  进入 **设置 (Settings) > 模型提供商 (Model Provider)**。
3.  找到 **Canopywave** 卡片（如果显示 "Debugging"，说明连接成功）。
4.  点击卡片右上角的菜单，选择 **设置 (Setup)**，输入 API Key：
    - API Key: (填入您的 Canopywave API Key)
5.  保存后，创建一个简单的 Chat 应用，选择 Canopywave 下的模型（如 `deepseek-v3.1`）进行对话测试。

### 4. 常见问题排查

- **报错 `no available node` / `connected to old process`**：
  - 原因：后台运行了多个旧的 `python main.py` 进程。
  - **解决**：关闭所有终端窗口，或运行 `killall python python3` 清理所有进程，然后重新启动。
- **报错 `TypeError: ... abstract method`**：
  - 原因：连接到了旧代码进程。
  - **解决**：同上，杀掉进程重启。

---

## 二、打包发布 (Packaging)

当本地测试通过后，您可以将插件打包成 `.difypkg` 文件，用于正式安装或分享。

### 1. 生成安装包

在项目根目录（且已激活虚拟环境）下运行：

```bash
# 激活环境（如果未激活）
source venv/bin/activate

# 执行打包命令
python -m dify_plugin.cli package
```

**成功输出示例：**

```
Path: /Users/lihui/canopywave/canopywave.difypkg
Size: 12345 bytes
```

### 2. 上传安装

1.  在 Dify 的 **模型提供商** 页面，点击右上角的 **安装插件 (Install Plugin)**（或类似按钮，视版本而定）。
2.  选择 **本地上传 (Local Upload)**。
3.  选择刚才生成的 `canopywave.difypkg` 文件。
4.  安装完成后，您就可以像使用官方插件一样使用它了（不再需要本地终端运行 `python main.py`）。

---

## 三、文件结构说明

- `main.py`: 插件入口。
- `venv/`: 虚拟环境（不要修改，不要提交到 git）。
- `_assets/`: 存放图标 (`icon.svg`, `icon-dark.svg` 等)。
- `models/llm/llm.py`: 核心逻辑代码（已优化错误处理和参数映射）。
- `manifest.yaml`: 插件元数据定义。
