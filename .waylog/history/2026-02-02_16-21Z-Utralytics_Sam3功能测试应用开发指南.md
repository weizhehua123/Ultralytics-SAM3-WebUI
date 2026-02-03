# Utralytics Sam3功能测试应用开发指南
_Exported on 02/03/2026 at 00:21:38 GMT+8 from Copilot Chat via WayLog_


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

---
