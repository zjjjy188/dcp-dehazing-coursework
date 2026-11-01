# 暗通道先验图像去雾的复现与改进

图像处理与分析课程项目，复现 [ngydc/dehazing-dark-channel](https://github.com/ngydc/dehazing-dark-channel)。保留原版源码，新增等价加速、正则项调整、成对评价、批处理和本地演示。

## 修改内容

- 空间最小滤波代替逐像素暗通道循环。
- 批量线性求解代替逐像素 3×3 矩阵求逆，保留彩色引导滤波与边界含义。
- 区分 0..255 和 0..1 图像的正则项尺度，通过开发集选参。
- 尝试稳健大气光和亮区保护，开发集未选中，最终默认关闭。
- 增加中文路径、批处理、EXIF 方向修正、透射率导出、本地交互演示。

原项目已包含引导滤波，不将其称为新增算法；本项目不声称提出新的去雾理论。

## 实测结果与限制

最终使用全新保留的 12 张图像，每张三档雾，共 36 个合成样本。

- 原版：平均 PSNR 20.571 dB，SSIM 0.9224。
- 最终方案：平均 PSNR 20.543 dB，SSIM 0.9291。
- SSIM 提升约 0.0067，PSNR 降低约 0.028 dB，存在质量取舍。
- 等价加速版与原版的流水线最大误差为 3.29e-15。
- 同一张 320×214 图像预热后三次计时，中位数从 3.3507 秒降至 0.0822 秒，约 40.74 倍。计时受本机后台负载影响。

全部算法使用 CPU，没有 GPU 加速。BSDS500 教学子集与人工深度代理合成雾不构成标准去雾基准，不代表真实世界普遍提升。真实雾图只作定性对比。

## 安装与运行

本机实测 Windows 11、Python 3.14.6。源码使用 Python 3.10 及以上语法，其他环境需验证依赖兼容性。建议独立虚拟环境。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m coursework.cli images --output outputs --mode improved
.\.venv\Scripts\python.exe -m coursework.cli images/street.jpg --output outputs --mode fast
.\.venv\Scripts\python.exe -m coursework.app
```

使用保存的 selected_config.json 即可运行，不必重跑完整实验。也可执行 启动演示.ps1。界面只监听 127.0.0.1，不开公网分享；大图在演示中缩放至最长边 1280 像素，命令行保留输入分辨率。

## 完整复现实验

```powershell
python -m coursework.experiment
```

脚本执行数值等价性与边界检查，下载固定 28 张源图像并合成雾，用 16 张开发图像的 48 个样本选参，然后在另 12 张图像的 36 个样本上评价，保存指标、消融、耗时和图像。下载需要联网，源图像不在本仓库重复分发。下载 URL 固定到源仓库提交，清单含 SHA-256。算法和合成过程确定，计时每次不同。

## 目录说明

- dehazing.py、guidedfilter.py、main.py：原样保留的上游源码。
- coursework/core.py：优化算法；cli.py、app.py：批处理和演示。
- coursework/experiment.py：数据、选参、评价；metrics.py：指标。
- data/manifest.json：来源、划分、SHA-256。
- results/summary.json：最终汇总；metrics.csv：逐样本指标。
- results/validation_search.csv：开发集选参；selected_config.json：最终配置。
- results/pilot/：先导试验记录。
- 实验说明.md、THIRD_PARTY.md：公平比较、实验限制、数据和方法来源。

data/clean/、results/examples/、results/real/ 不纳入 Git，可重跑生成。

## 公平比较

原版结果也统一裁剪至有效范围后评价，避免 main.py 直接转 uint8 的越界回绕。原版在 0..255 引导图上用 epsilon=0.001，等价版在 0..1 上用 0.001/255²；最终开发集选中 epsilon=0.0001。

先导试验的小开发集选出的稳健大气光未可靠泛化，该轮全部 16 张图像随后并入开发集，最终 12 张测试图像另行保留，未参与选参。先导指标单独保留，不混入最终均值。

小规模合成数据、人工深度及固定文件名选择均有限制。天空、白色物体、严重偏色仍可能失败。速度提升来自保持数值等价的计算优化，质量变化需结合两个指标理解。

## 来源

上游提交 c0a5754734aec068be4c420f8aa2145b960b8511，保留 MIT 许可证；数据与文献见 [THIRD_PARTY.md](THIRD_PARTY.md)。主要依赖的实测版本见 requirements-tested.txt。

## 原项目示例

![](./images/street.jpg)  ![](./images/street_scene_radiance_ref.jpg) ![](./images/street_dark_channel.jpg) 
![](./images/street_ref_transmission.jpg) 

