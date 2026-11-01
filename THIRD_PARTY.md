# 来源与许可

## 复现项目

- 上游：[ngydc/dehazing-dark-channel](https://github.com/ngydc/dehazing-dark-channel)
- 固定提交：`c0a5754734aec068be4c420f8aa2145b960b8511`
- 许可：MIT，见原样保留的 `LICENSE`。
- 原样保留：`dehazing.py`、`guidedfilter.py`、`main.py` 和原示例图像。
- `guidedfilter.py` 自带对 joyeecheung/dark-channel-prior-dehazing 的来源说明，保留该说明。
- 新增实现位于 `coursework/`，没有把上游原有的引导滤波作为新增创新。

## 实验图像

BSDS500 原本是自然图像分割与边界检测数据集，本作业只使用自然 RGB 图像，**未使用分割标注，也不将其称为官方去雾基准**。

- 镜像：[BIDS/BSDS500](https://github.com/BIDS/BSDS500)
- 固定提交：`a04b7c6c3a9f0ace74bf205c72a43d32e1c72722`
- 28 张源图像的下载地址、SHA-256 与本实验划分记录于 `data/manifest.json`。
- 源图像不随代码仓库再次分发，执行实验脚本时从原镜像下载；图像权利归原权利人。
- 报告中的图像仅用于本课程研究与结果说明。
- 引用：P. Arbelaez, M. Maire, C. Fowlkes, J. Malik. Contour Detection and Hierarchical Image Segmentation. IEEE TPAMI, 33(5), 898–916, 2011.

## 方法参考

1. K. He, J. Sun, X. Tang. Single Image Haze Removal Using Dark Channel Prior. CVPR, 2009. [作者项目页](https://people.csail.mit.edu/kaiming/cvpr09/index.html)
2. K. He, J. Sun, X. Tang. Guided Image Filtering. ECCV, 2010. 同上作者项目页提供资料。

批量求解、最小滤波和正则化是已有计算方法。本项目的贡献是对复现代码的实现优化、参数尺度修正、可复现实验和使用功能扩展，不声称提出全新的去雾理论。
