# Utralytics Sam3功能测试应用开发指南
_Exported on 02/03/2026 at 00:39:38 GMT+8 from Copilot Chat via WayLog_


**User**

要编写Utralytics Sam3的全部功能测试的应用。功能包含：
图片类
c)	基于文本的概念分割
d)	基于图像样本的分割
e)	重用图像特征进行多重查询
视频类
f)	使用边界框跨视频跟踪概念
g)	使用文本提示跟踪概念

应用Uralytics-Sam3-WebUI将部署在云服务器上运行。测试阶段，开放端口8002，访问Web UI：https://localhost:8002

项目目录frontend的提供了前端的网页界面。后端代码还没有。

本地仅仅编写代码，通过SFTP同步到云服务器。如需要访问远程服务器进行测试，请根据sftp.json的设置访问。
云服务器已经制作好虚拟环境：/mnt/cloud-disk/conda-envs/Utralytics-sam3。虚拟环境中已经安装好完全的Ultralytics 版本 8.3.237。
另外：
文字包与模型包已经保存在一个目录下
/mnt/cloud-disk/models/sam3/facebook/sam3/bpe_simple_vocab_16e6.txt.gz 
/mnt/cloud-disk/models/sam3/facebook/sam3/sam3.pt


---


**Copilot Chat**

我先让一个子代理快速勘察当前仓库（前端页面、现有配置、是否已有后端脚手架/依赖约定），以便给出可落地的后端+功能测试开发计划。
## Plan: SAM3 WebUI 后端与全功能测试应用

在现有仅有前端页面的基础上，用 Python FastAPI 在端口 8002 提供同源 Web UI + 推理 API + 长任务(job)机制，覆盖图片（文本概念分割/样本分割/特征复用多查询）与视频（bbox跨帧跟踪/文本提示跟踪）全功能测试流程。后端直接使用云端已装好的 Ultralytics 8.3.237，并显式配置模型与词表路径，便于 SFTP 同步后在云端即跑通。

### Steps {3–6 steps, 5–20 words each}
1. 梳理前端交互点，确定需要补齐的 API 端点与参数格式（参考 
）。
2. 新建 FastAPI 后端骨架：静态托管 `/` + 健康检查 `/health` + 统一错误返回。
3. 实现图片三类能力 API：文本分割、样本分割、`feature_id` 特征缓存与多次查询接口。
4. 实现视频两类能力 API：上传视频创建 `job_id`，后台执行跟踪并产出结果文件。
5. 增加 job 状态查询与进度推送（轮询 `GET /api/jobs/{id}`，可选 SSE/WS）。
6. 写“功能测试应用”流程：用脚本/页面按钮依次调用各 API，保存可视化结果与日志。

### Further Considerations {1–3, 5–25 words each}
1. `https://localhost:8002`：是否必须 HTTPS？A 反代证书；B 仅 HTTP；C SSH 端口转发模拟 HTTPS。
2. 特征复用缓存：A 进程内 LRU；B 磁盘缓存；C Redis（复杂度更高）。
3. 视频 job 执行：A 后台线程；B 多进程队列；C 外部队列（Celery/RQ）。

---


**User**

1：https://localhost:8002仅为示例，只要能实现快速简单的web UI访问即可。
2：特征复用缓存，选取简单，容易实现的方式
3：视频 job 执行：我不知道如何选择。

---


**Copilot Chat**

我会再快速做一次只读勘察：重点评估“视频 job 执行”在 FastAPI/uvicorn 下最简单可靠的实现选项与取舍，然后给出更新后的落地计划（包含明确选择）。
## Plan: SAM3 WebUI 后端与功能测试（简化版）

用 FastAPI（HTTP/8002）快速补齐后端：同源服务前端页面 + 图片分割 API + 视频跟踪 job API。特征复用缓存采用进程内 LRU（最简单），视频 job 执行采用“进程内队列 + 单 worker 后台线程”（最稳的最小实现，避免 GPU 显存被多进程/多并发打爆）。

### Steps {3–6 steps, 5–20 words each}
1. 固定运行形态：HTTP `0.0.0.0:8002`，静态托管 
。
2. 设计并实现图片 API：文本分割/样本分割/`feature_id` 查询三条主线。
3. 加入特征复用缓存：进程内 LRU（按 `feature_id` 存放 embedding）。
4. 设计并实现视频 job API：创建 job、查询状态、获取结果文件。
5. 选择 job 执行：单进程单 worker 队列，GPU 推理串行。
6. 补“功能测试应用”入口：按钮或脚本顺序跑完 c–g 并落盘结果。

### Further Considerations {1–3, 5–25 words each}
1. 视频 job 默认方案：进程内队列；后续需要可靠性再升级 Redis/RQ。
2. `uvicorn --workers` 建议固定为 1，避免多进程重复加载模型占满显存。
3. 结果产物建议按 `runs/{job_id}/` 组织，便于下载与清理。

---


**User**

Further Considerations {1–3, 5–25 words each}均同意你的建议

---


**Copilot Chat**

我再做一次只读梳理：把“同意的取舍”落到具体交付物（文件结构、接口清单、结果目录、SFTP同步注意点），然后给你一版可直接按步骤执行的最终计划。
## Plan: SAM3 WebUI 后端与全功能测试落地

在仓库根目录新增 FastAPI 后端（同源托管前端页面 + `/api/v1` 接口），用“进程内队列 + 单 worker 后台线程”跑视频长任务，embedding 复用用进程内 LRU。模型/词表路径通过环境变量配置，避免 SFTP 误传大模型与敏感文件；开发期先用脚本验证 API，再把前端按钮改为 fetch 对接，实现一套可快速访问的 Web UI 功能测试应用。

### Steps {3–6 steps, 5–20 words each}
1. 建立后端骨架与目录：新增 backend/app/main.py 并挂载 
。
2. 定义统一 API schema：实现 `/api/v1/health`、错误返回与静态结果下载 `/files/*`。
3. 实现图片三功能端点：文本分割、样本分割、embedding 创建与多次 query。
4. 实现视频两功能端点：`/video/track/bbox` 与 `/video/track/text` 仅创建 job。
5. 落地 job 系统：进程内 FIFO 队列、单 worker 执行、`status.json` 落盘、结果目录按 job_id 组织。
6. 做功能测试入口：先写 API 调用脚本回归，再把前端按钮改为创建 job + 轮询展示结果。

### Further Considerations {1–3, 5–25 words each}
1. 模型与词表用环境变量默认指向云端绝对路径。
2. `uvicorn` 固定 `--workers 1`，避免 GPU 重复加载模型。
3. `watcher.autoUpload=true` 注意避免生成目录触发海量上传。

---


**User**

1. 同意，采用绝对路径
2. 同意
3. 同意

---


**Copilot Chat**

我将再做一次只读核对：补齐“绝对路径配置”的落地方式与最小启动/部署约定，然后给出可直接执行的最终计划清单。

---
