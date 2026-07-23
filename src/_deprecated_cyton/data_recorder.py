"""
데이터 기록 모듈

OpenBCI 신호를 파일(CSV, NPY)로 저장
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from bled112_openbci import Sample


class DataRecorder:
    """OpenBCI 데이터 레코더"""

    def __init__(self, output_dir: Optional[Path] = None, filename: Optional[str] = None):
        """
        Args:
            output_dir: 저장할 디렉토리 (기본값: outputs/)
            filename: 파일명 (기본값: OpenBCI_YYYYMMDD_HHMMSS.csv)
        """
        if output_dir is None:
            # 프로젝트 루트 기준으로 outputs 디렉토리
            self.output_dir = Path(__file__).resolve().parent.parent / "outputs"
        else:
            self.output_dir = Path(output_dir)

        self.output_dir.mkdir(exist_ok=True, parents=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"OpenBCI_{timestamp}.csv"

        self.filepath = self.output_dir / filename
        self.data = []
        self.is_recording = False

    def start_recording(self):
        """기록 시작"""
        self.data = []
        self.is_recording = True
        print(f"기록 시작: {self.filepath}")

    def add_sample(self, sample: Sample):
        """샘플 추가"""
        if not self.is_recording:
            return

        row = {
            'timestamp': sample.timestamp,
            'packet_id': sample.packet_id,
        }

        # EEG 채널 데이터
        for i, value in enumerate(sample.channel_data):
            row[f'EEG_Ch{i+1}'] = value

        # AUX 데이터
        for i, value in enumerate(sample.aux_data):
            row[f'AUX_{i+1}'] = value

        self.data.append(row)

    def stop_recording(self) -> Path:
        """기록 중지 및 파일 저장"""
        if not self.is_recording:
            print("기록 중이 아닙니다")
            return None

        self.is_recording = False

        if len(self.data) == 0:
            print("저장할 데이터가 없습니다")
            return None

        # DataFrame 변환
        df = pd.DataFrame(self.data)

        # CSV 저장
        df.to_csv(self.filepath, index=False)
        print(f"저장됨: {self.filepath} ({len(df)} samples)")

        return self.filepath

    def get_dataframe(self) -> pd.DataFrame:
        """현재 데이터를 DataFrame으로 반환"""
        if len(self.data) == 0:
            return pd.DataFrame()
        return pd.DataFrame(self.data)

    def save_numpy(self, suffix: str = "_raw") -> Path:
        """데이터를 NumPy 형식으로 저장

        Args:
            suffix: 파일명 suffix (예: _raw, _filtered)

        Returns:
            저장된 파일 경로
        """
        if len(self.data) == 0:
            print("저장할 데이터가 없습니다")
            return None

        df = pd.DataFrame(self.data)

        # EEG 데이터만 추출 (shape: [samples, 8])
        eeg_data = df[[f'EEG_Ch{i+1}' for i in range(8)]].values

        filepath = self.filepath.with_stem(self.filepath.stem + suffix)
        np.save(filepath.with_suffix('.npy'), eeg_data)
        print(f"NumPy 저장됨: {filepath}")

        return filepath


class RealtimeVisualizer:
    """실시간 신호 시각화"""

    def __init__(self, channels: List[int] = None, fs: float = 250):
        """
        Args:
            channels: 표시할 채널 (기본값: [0, 1, 2, 3])
            fs: 샘플링 레이트
        """
        self.channels = channels or [0, 1, 2, 3]
        self.fs = fs
        self.data = {ch: [] for ch in self.channels}

    def add_sample(self, sample: Sample):
        """샘플 추가"""
        for ch in self.channels:
            self.data[ch].append(sample.channel_data[ch])

    def plot_channels(self, duration: float = 10) -> Path:
        """채널들을 시계열로 플롯

        Args:
            duration: 표시할 시간 범위 (초)

        Returns:
            저장된 그림 경로
        """
        import matplotlib.pyplot as plt

        # 한글 폰트 설정
        plt.rcParams["font.family"] = "Malgun Gothic"

        fig, axes = plt.subplots(len(self.channels), 1, figsize=(12, 3*len(self.channels)))
        if len(self.channels) == 1:
            axes = [axes]

        samples_to_show = int(duration * self.fs)

        for idx, ch in enumerate(self.channels):
            data = self.data[ch][-samples_to_show:]
            time = np.arange(len(data)) / self.fs

            axes[idx].plot(time, data, 'b-', linewidth=0.5)
            axes[idx].set_xlabel('시간 (초)')
            axes[idx].set_ylabel('진폭 (µV)')
            axes[idx].set_title(f'채널 {ch+1}')
            axes[idx].grid(True, alpha=0.3)

        plt.tight_layout()

        output_dir = Path(__file__).resolve().parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / f"channels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filepath, dpi=100)
        plt.close()

        print(f"그림 저장됨: {filepath}")
        return filepath

    def plot_spectrum(self) -> Path:
        """각 채널의 파워 스펙트럼 플롯"""
        from scipy import signal as scipy_signal
        import matplotlib.pyplot as plt

        plt.rcParams["font.family"] = "Malgun Gothic"

        fig, axes = plt.subplots(len(self.channels), 1, figsize=(12, 3*len(self.channels)))
        if len(self.channels) == 1:
            axes = [axes]

        for idx, ch in enumerate(self.channels):
            data = np.array(self.data[ch])
            freqs, pxx = scipy_signal.welch(data, self.fs, nperseg=256)

            axes[idx].semilogy(freqs, pxx, 'b-', linewidth=1)
            axes[idx].set_xlabel('주파수 (Hz)')
            axes[idx].set_ylabel('파워 (µV²/Hz)')
            axes[idx].set_title(f'채널 {ch+1} - 파워 스펙트럼')
            axes[idx].grid(True, alpha=0.3)
            axes[idx].set_xlim([0, 100])

        plt.tight_layout()

        output_dir = Path(__file__).resolve().parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / f"spectrum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filepath, dpi=100)
        plt.close()

        print(f"스펙트럼 저장됨: {filepath}")
        return filepath


if __name__ == "__main__":
    # 테스트
    recorder = DataRecorder()
    recorder.start_recording()

    # 테스트 데이터 추가
    for i in range(500):
        sample = Sample(
            packet_id=i,
            channel_data=[50 * np.sin(2 * np.pi * 10 * i / 250)] * 8,
            aux_data=[100, 200, 300],
            timestamp=i / 250
        )
        recorder.add_sample(sample)

    recorder.stop_recording()
    recorder.save_numpy("_test")
