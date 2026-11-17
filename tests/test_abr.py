import pytest

from media.abr import (
    target_duration,
    estimate_bandwidth,
    choose_variant,
    switch_allowed,
    seek_index
)


def test_target_duration_int():
    assert target_duration('#EXT-X-TARGETDURATION:4\n') == 4.0

def test_target_duration_float():
    assert target_duration('#EXT-X-TARGETDURATION:2.5\n') == 2.5

def test_target_duration_missing():
    with pytest.raises(ValueError):
        target_duration('#EXTM3U\n')

def test_estimate_all():
    assert estimate_bandwidth([1.0, 2.0, 3.0]) == 2.0

def test_estimate_window():
    assert estimate_bandwidth([1.0, 2.0, 3.0], 2) == 2.5

def test_choose_low():
    assert choose_variant([500, 1000, 2000], 10.0, 600.0, 0) == 0

def test_choose_high():
    assert choose_variant([500, 1000, 2000], 10.0, 3000.0, 0) == 2

def test_choose_hysteresis():
    assert choose_variant([500, 1000, 2000], 10.0, 900.0, 2) == 1

def test_choose_low_buffer():
    assert choose_variant([500, 1000, 2000], 1.0, 3000.0, 2) == 0

def test_choose_high_buffer():
    assert choose_variant([500, 1000, 2000], 10.0, 3000.0, 2) == 2

def test_switch_keyframe():
    assert switch_allowed(True, 5.0) is True

def test_switch_not_keyframe():
    assert switch_allowed(False, 5.0) is False

def test_seek_start():
    assert seek_index([4.0, 4.0, 4.0], 0.0) == 0

def test_seek_boundary():
    assert seek_index([4.0, 4.0, 4.0], 4.0) == 1

def test_seek_end():
    assert seek_index([4.0, 4.0, 4.0], 100.0) == 2
