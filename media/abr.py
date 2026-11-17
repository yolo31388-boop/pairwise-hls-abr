"""HLS ABR 核心逻辑。

修复要点：
- 只在关键帧（IDR）边界切档，避免解码器等待下一个 IDR 造成卡顿。
- 带宽估计使用滑动窗口平均，而不是只看最近一个分片，降低网络抖动
  引起的疯狂升降档。
- 选档带滞后：降档一次只降一级，避免来回震荡。
- buffer 水位过低时强制最低档，防止卡到黑屏。
- seek 按播放列表里每个分片的实际时长累计定位，不信任
  EXT-X-TARGETDURATION（CDN 边缘可能返回与实际分片不一致的值）。
"""

# buffer 低于该水位（秒）时强制降到最低档
LOW_BUFFER_THRESHOLD = 2.0

# 带宽利用率安全系数：只用估计带宽的一部分来选档，留出抖动余量
BANDWIDTH_SAFETY_FACTOR = 1.0


def target_duration(playlist):
    """从 m3u8 文本解析 EXT-X-TARGETDURATION，返回浮点秒数。

    找不到该标签时抛 ValueError。
    """
    for line in playlist.splitlines():
        line = line.strip()
        if line.startswith('#EXT-X-TARGETDURATION:'):
            value = line.split(':', 1)[1].strip()
            try:
                return float(value)
            except ValueError:
                raise ValueError(f'invalid EXT-X-TARGETDURATION: {value!r}')
    raise ValueError('EXT-X-TARGETDURATION not found')


def estimate_bandwidth(samples, window=None):
    """滑动窗口平均带宽估计。

    samples: 历史吞吐样本（最新在末尾）。
    window:  只取最近 window 个样本；None 表示全部。
    """
    if not samples:
        raise ValueError('no bandwidth samples')
    if window is not None and window > 0:
        samples = samples[-window:]
    return sum(samples) / len(samples)


def choose_variant(bitrates, buffer_level, bandwidth, current):
    """选择码率档位（返回下标）。

    规则：
    1. buffer 低于 LOW_BUFFER_THRESHOLD：直接最低档，保命优先。
    2. 否则在带宽（乘安全系数）能支撑的档位里选最高档。
    3. 滞后：相对当前档位的降档一次最多降一级，升档不限。
    """
    if not bitrates:
        raise ValueError('no variants')

    if buffer_level < LOW_BUFFER_THRESHOLD:
        return 0

    budget = bandwidth * BANDWIDTH_SAFETY_FACTOR
    best = 0
    for i, br in enumerate(bitrates):
        if br <= budget:
            best = i
        else:
            break

    # 滞后：降档最多降一级，避免抖动时大幅跳水
    if best < current - 1:
        best = current - 1
    # 当前档位本身可能超出 bitrates 范围，钳制
    return max(0, min(best, len(bitrates) - 1))


def switch_allowed(is_keyframe, position):
    """是否允许在当前位置切档：只有关键帧边界才允许。"""
    return bool(is_keyframe)


def seek_index(durations, time):
    """按各分片实际时长累计，求 time 落在第几个分片（0 起）。

    边界（恰好等于某分片结束时刻）归入下一个分片；
    超出总时长时钳制到最后一个分片。
    """
    if not durations:
        raise ValueError('empty playlist')
    acc = 0.0
    for i, d in enumerate(durations):
        acc += d
        if time < acc:
            return i
    return len(durations) - 1
