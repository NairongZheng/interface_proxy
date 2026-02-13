

> 跟 LLM 交互完成的 coding
> 理论上应该分 repo 的，有点懒，不想 repo 太多，就都放一起了
> 把每个文件夹当作一个 repo 看待吧

1. data_transfer: with copilot. st 训练格式数据转回中间格式数据
2. homepage: with claudecode. 随便写了个 homepage
3. interface_proxy: with claudecode. 实现不同的 LLM 接口格式转发
4. rlhf_learning: with claudecode. 简单的 rlhf 例子，包括 sft 和 rl，可以 debug 仔细看过程
5. vlm_model_learning: wich codex and claudecode. 简单的 clip、扩散模型等。（没有仔细看过，不一定对）