# pairwise-hls-abr

多媒体播放器播 HLS 时，ABR 一切码率就卡顿：切换点不在关键帧，解码器要等下一个 IDR；带宽估计只看最近一个分片，网络抖动时疯狂升降档；buffer 快空了还切到高码率，卡到黑屏；discontinuity 序列没有重置时间轴，字幕和音频对不上；码率切换后旧的音频轨道没有 flush，声音重复一小段；CDN 边缘返回的 m3u8 里 EXT-X-TARGETDURATION 和实际分片长度不一致，seek 落到错误位置。media/abr.py 是核心，tests/test_abr.py 15个红。要修的是：只在关键帧切；带宽估计加滑动窗口和滞后；按 buffer 水位限制档位；discontinuity 重置时间轴；切档 flush 音频；按实际分片时长修正 seek。

## 运行

```bash
python -m pytest tests -q
```

初始状态：15 个用例失败。修复实现使全部用例通过，不要修改 `tests/` 下的测试。

语言/框架：Python 3, pytest；环境可复现等级：无外部依赖。
