"""
신호 처리 모듈

실시간 신경신호 필터링, RMS 계산, 스펙트럼 분석 등
"""

import numpy as np
from scipy import signal as scipy_signal
from collections import deque
from typing import List


class ButterworthFilter:
    """Butterworth 필터 (IIR)"""

    def __init__(self, lowcut: float, highcut: float, fs: float = 250, order: int = 2):
        """
        Args:
            lowcut: 저주파 컷오프 (Hz)
            highcut: 고주파 컷오프 (Hz)
            fs: 샘플링 레이트 (Hz)
            order: 필터 차수
        """
        nyquist = fs / 2
        low = lowcut / nyquist
        high = highcut / nyquist

        self.b, self.a = scipy_signal.butter(order, [low, high], btype='band')
        self.zi = np.zeros(max(len(self.b), len(self.a)) - 1)

    def filter(self, data: np.ndarray) -> np.ndarray:
        """데이터 필터링 (실시간)"""
        filtered, self.zi = scipy_signal.lfilter(self.b, self.a, data, zi=self.zi)
        return filtered


class SignalProcessor:
    """신호 처리 클래스"""

    def __init__(self, fs: float = 250, window_size: int = 250):
        """
        Args:
            fs: 샘플링 레이트 (Hz)
            window_size: 데이터 버퍼 크기 (샘플 수)
        """
        self.fs = fs
        self.window_size = window_size

        # 채널별 버퍼
        self.buffers = {i: deque(maxlen=window_size) for i in range(8)}

        # 필터 (8 채널)
        self.filters = {i: ButterworthFilter(5, 50, fs=fs) for i in range(8)}

    def add_sample(self, channel_data: List[float]):
        """새 샘플 추가"""
        for ch, value in enumerate(channel_data):
            self.buffers[ch].append(value)

    def get_buffer(self, channel: int) -> np.ndarray:
        """채널 버퍼 반환"""
        return np.array(self.buffers[channel])

    def compute_rms(self, channel: int) -> float:
        """채널 RMS 계산"""
        data = self.get_buffer(channel)
        if len(data) == 0:
            return 0.0
        return np.sqrt(np.mean(data ** 2))

    def compute_rms_all(self) -> dict:
        """모든 채널 RMS 계산"""
        return {ch: self.compute_rms(ch) for ch in range(8)}

    def apply_filter(self, channel: int, data: np.ndarray) -> np.ndarray:
        """채널 필터 적용"""
        return self.filters[channel].filter(data)

    def get_power_spectrum(self, channel: int, nperseg: int = 256) -> tuple:
        """파워 스펙트럼 (Welch 방법)

        Returns:
            (frequency, power)
        """
        data = self.get_buffer(channel)
        if len(data) < nperseg:
            return np.array([]), np.array([])

        freqs, pxx = scipy_signal.welch(
            data, self.fs, nperseg=nperseg, scaling='spectrum'
        )
        return freqs, pxx

    def get_band_power(self, channel: int, band_name: str) -> float:
        """대역별 파워 계산

        Args:
            channel: 채널 번호 (0-7)
            band_name: 'delta', 'theta', 'alpha', 'beta', 'gamma'

        Returns:
            해당 대역의 전력 (uV^2)
        """
        bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 12),
            'beta': (12, 30),
            'gamma': (30, 100),
        }

        if band_name not in bands:
            raise ValueError(f"알 수 없는 대역: {band_name}")

        low, high = bands[band_name]
        freqs, pxx = self.get_power_spectrum(channel)

        if len(freqs) == 0:
            return 0.0

        mask = (freqs >= low) & (freqs <= high)
        return np.sum(pxx[mask])


class ThresholdDetector:
    """임계값 기반 이벤트 감지"""

    def __init__(self, threshold: float, min_duration: int = 10):
        """
        Args:
            threshold: RMS 임계값
            min_duration: 이벤트 지속 최소 샘플 수
        """
        self.threshold = threshold
        self.min_duration = min_duration
        self.event_counter = 0
        self.is_active = False

    def detect(self, rms: float) -> bool:
        """임계값 초과 감지"""
        if rms > self.threshold:
            self.event_counter += 1
            if self.event_counter >= self.min_duration and not self.is_active:
                self.is_active = True
                return True  # 이벤트 시작
        else:
            if self.event_counter > 0 and self.is_active:
                self.is_active = False
                return False  # 이벤트 종료
            self.event_counter = 0

        return None  # 상태 변화 없음


if __name__ == "__main__":
    # 테스트
    processor = SignalProcessor(fs=250)

    # 테스트 신호 (1초, 10Hz 사인파)
    t = np.linspace(0, 1, 250)
    signal_data = 50 * np.sin(2 * np.pi * 10 * t)

    for val in signal_data:
        processor.add_sample([val] * 8)

    print(f"RMS (Ch0): {processor.compute_rms(0):.2f} uV")
    print(f"Alpha 파워: {processor.get_band_power(0, 'alpha'):.2f} uV^2")
