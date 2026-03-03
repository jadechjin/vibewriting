# 常见问题解答（FAQ）

---

## TeX Live 安装

### Q: 如何在 Windows 上安装 TeX Live？

**方法一：官方安装程序（推荐）**

1. 下载安装程序：访问 [https://tug.org/texlive/acquire-netinstall.html](https://tug.org/texlive/acquire-netinstall.html)，下载 `install-tl-windows.exe`
2. 以管理员身份运行安装程序
3. 选择安装方案：建议选择 **"Full"（完整安装）**，约 8GB，包含所有包
4. 等待安装完成（通常需要 30~60 分钟）
5. 安装完成后，验证安装：

```cmd
xelatex --version
latexmk --version
```

**方法二：MiKTeX（轻量替代，按需下载包）**

```
https://miktex.org/download
```

> **注意**：vibewriting 使用 `ctex` 宏包，MiKTeX 首次编译时会自动下载，需要网络连接。

**验证中文支持**：

```bash
# 在项目目录下运行
bash build.sh build
```

如果编译成功且中文字符正常显示，说明 TeX Live 中文支持已就绪。

---

### Q: 如何在 macOS 上安装 TeX Live？

**方法一：MacTeX（推荐，TeX Live 的 macOS 发行版）**

```bash
# 下载 MacTeX.pkg（约 4GB）
# https://tug.org/mactex/mactex-download.html

# 或使用 Homebrew
brew install --cask mactex
```

安装完成后刷新 PATH：

```bash
eval "$(/usr/libexec/path_helper)"
```

**方法二：BasicTeX（精简版，约 100MB）**

```bash
brew install --cask basictex

# 安装 vibewriting 所需的额外包
sudo tlmgr install latexmk ctex xeCJK collection-langchinese
```

验证安装：

```bash
xelatex --version
latexmk --version
kpsewhich ctexart.cls  # 应返回文件路径
```

---

### Q: 如何在 Linux（Ubuntu/Debian）上安装 TeX Live？

**方法一：系统包管理器（快速但版本可能较旧）**

```bash
sudo apt-get update
sudo apt-get install -y texlive-full  # 完整安装
# 或精简安装
sudo apt-get install -y texlive-xetex texlive-lang-chinese latexmk
```

**方法二：官方安装程序（获取最新版本）**

```bash
# 下载安装脚本
wget https://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz
tar -xzf install-tl-unx.tar.gz
cd install-tl-*/

# 运行安装
sudo perl install-tl --scheme=full

# 添加到 PATH（添加到 ~/.bashrc 或 ~/.zshrc）
export PATH="/usr/local/texlive/2024/bin/x86_64-linux:$PATH"
```

---

## Dify 知识库配置

### Q: 如何获取 Dify API 凭据？

1. 登录 Dify 控制台（[https://cloud.dify.ai](https://cloud.dify.ai) 或私有部署地址）
2. 进入 **设置 > API 密钥**，创建一个新的 API 密钥
3. 进入 **知识库**，找到目标数据集，URL 中的 UUID 即为 `VW_DIFY_DATASET_ID`

将获取的信息填入 `.env`：

```env
VW_DIFY_API_BASE_URL=https://api.dify.ai/v1
VW_DIFY_API_KEY=app-xxxxxxxxxxxxxxxxxxxx
VW_DIFY_DATASET_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

### Q: Dify 知识库是必须的吗？

不是必须的。vibewriting 可以在不配置 Dify 的情况下运行，此时文献检索仅依赖 paper-search MCP（通过 SerpAPI 搜索公开学术数据库）。

如果 `VW_DIFY_API_KEY` 未设置，相关功能会被自动跳过，验证脚本会显示黄色警告而非红色错误。

---

## LaTeX 编译失败排查

### Q: 提示 `latexmk: not found` 或 `xelatex: not found`

TeX Live 未正确安装或未添加到系统 PATH。

**解决步骤**：

1. 确认 TeX Live 已安装：
   ```bash
   which xelatex  # 应返回路径如 /usr/local/texlive/2024/bin/.../xelatex
   ```

2. 如果命令不存在，将 TeX Live 的 bin 目录添加到 PATH：
   ```bash
   # Linux/macOS，添加到 ~/.bashrc 或 ~/.zshrc
   export PATH="/usr/local/texlive/2024/bin/x86_64-linux:$PATH"

   # Windows，在系统环境变量中添加 TeX Live bin 目录
   # 通常为 C:\texlive\2024\bin\windows
   ```

3. 重新运行验证脚本：
   ```bash
   uv run scripts/validate_env.py
   ```

---

### Q: 编译时提示字体缺失（font not found）

常见错误信息：`! Font ...不存在` 或 `kpathsea: Running mktexmf ...`

**解决方案**：

1. **Linux**：安装思源字体或文泉驿字体：
   ```bash
   sudo apt-get install fonts-noto-cjk
   # 或
   sudo apt-get install fonts-wqy-zenhei
   ```

2. **Windows**：`ctex` 默认使用系统 CJK 字体（宋体/黑体），通常无需额外安装。如出现问题，在 `paper/main.tex` 中显式指定字体：
   ```latex
   \setCJKmainfont{SimSun}    % 宋体
   \setCJKsansfont{SimHei}    % 黑体
   ```

3. **macOS**：
   ```latex
   \setCJKmainfont{STSong}    % 华文宋体
   \setCJKsansfont{STHeiti}   % 华文黑体
   ```

刷新字体缓存后重新编译：

```bash
fc-cache -fv
bash build.sh build
```

---

### Q: 提示 `Citation 'xxx' on page Y undefined`

BibTeX 引用未找到或 `.bib` 文件格式有误。

**解决步骤**：

1. 检查引用文件是否存在且格式正确：
   ```bash
   bash build.sh check  # 运行 checkcites 检查未使用/未定义的引用
   ```

2. 确认 `.bib` 文件使用 UTF-8 编码（禁止其他编码）

3. 确认引用键仅包含 ASCII 字符（不含中文、特殊符号）

4. 重新完整编译：
   ```bash
   bash build.sh clean  # 清理所有构建产物
   bash build.sh build  # 重新编译
   ```

---

### Q: 编译陷入无限循环或长时间不结束

`VW_COMPILE_TIMEOUT_SEC` 控制单次编译的超时时间，默认 120 秒。如果长时间无响应：

1. 按 `Ctrl+C` 中断
2. 清理构建目录：
   ```bash
   bash build.sh clean
   ```
3. 检查 `.log` 文件中的具体错误：
   ```bash
   # 构建日志位于
   cat paper/build/main.log | tail -50
   ```

---

## 检查点恢复

### Q: 写作过程中断了，如何从断点继续？

vibewriting 在每个阶段完成后会自动保存检查点到 `output/checkpoint.json`。

恢复方法：

```
/write-paper "论文主题" --resume
```

系统会读取检查点，跳过已完成的阶段，从中断处继续。

---

### Q: 如何查看当前进度？

检查点文件 `output/checkpoint.json` 记录了各阶段的完成状态：

```bash
# 查看检查点内容（需安装 jq）
jq '.' output/checkpoint.json

# 不安装 jq 时
uv run python -m json.tool output/checkpoint.json
```

---

### Q: 想从头重新运行，如何清除检查点？

```bash
# 删除检查点和运行指标
rm -f output/checkpoint.json output/run_metrics.json

# 如果也想清除证据卡缓存
rm -f data/processed/literature/literature_cards.jsonl

# 然后重新运行
/write-paper "论文主题"
```

---

## 数据管线问题

### Q: 运行数据管线时提示 `No data files found`

确认原始数据文件已放置在正确目录：

```
data/raw/          ← 原始数据文件放这里
data/processed/    ← 处理后的数据自动生成在这里
```

如果使用自定义数据目录，在 `paper_config.yaml` 中设置：

```yaml
data_dir: "/path/to/your/data"
```

或通过命令行覆盖：

```bash
uv run python -m vibewriting.pipeline.cli run \
  --data-dir /path/to/your/data \
  --output-dir output \
  --seed 42
```

---

### Q: 每次运行结果不一样，如何保证可复现性？

确保 `random_seed` 在 `paper_config.yaml` 和环境变量中一致：

```yaml
# paper_config.yaml
random_seed: 42
```

```env
# .env
VW_RANDOM_SEED=42
```

注意：`VW_RANDOM_SEED` 环境变量优先级高于 `paper_config.yaml` 中的 `random_seed`。

---

## Python 依赖问题

### Q: `uv sync` 失败，提示网络错误

使用国内镜像源：

```bash
uv sync --index-url https://pypi.tuna.tsinghua.edu.cn/simple/
```

或配置全局镜像（在 `~/.config/uv/uv.toml` 中）：

```toml
[[index]]
url = "https://pypi.tuna.tsinghua.edu.cn/simple/"
default = true
```

---

### Q: 提示 Python 版本不匹配

vibewriting 要求 Python 3.12+。查看当前版本：

```bash
python --version
uv python list  # 查看 uv 管理的 Python 版本
```

如果需要安装 Python 3.12：

```bash
uv python install 3.12
uv sync  # 重新同步依赖
```

---

### Q: 运行 `uv run pytest` 时测试失败

1. 先确认环境变量已正确配置：
   ```bash
   uv run scripts/validate_env.py
   ```

2. 运行特定测试模块而非全量：
   ```bash
   uv run pytest tests/test_models.py -v
   ```

3. 查看详细错误输出：
   ```bash
   uv run pytest -v --tb=long
   ```

---

## 其他问题

### Q: 如何更新 vibewriting 到最新版本？

```bash
git pull origin main
uv sync  # 同步新依赖
uv run scripts/validate_env.py  # 验证环境
```

---

### Q: 在哪里报告 Bug 或提交功能请求？

在项目 GitHub 仓库提交 Issue，请附上：

1. 操作系统和版本
2. Python 版本（`python --version`）
3. TeX Live 版本（`xelatex --version`）
4. 完整错误信息
5. `uv run scripts/validate_env.py --json` 的输出
