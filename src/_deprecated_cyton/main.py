"""
OpenBCI BLED112 메인 실행 스크립트

실시간 신경신호 수집, 신호 처리, 데이터 저장을 통합한 예제
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# 상대 경로 import
from bled112_openbci import OpenBCIBLE, Sample
from signal_processor import SignalProcessor, ThresholdDetector
from data_recorder import DataRecorder, RealtimeVisualizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OpenBCIApp:
    """OpenBCI 애플리케이션"""

    def __init__(self, device_name: str = "OpenBCI-Cyton",
                 record: bool = False,
                 duration: int = 60):
        """
        Args:
            device_name: BLE 장치명
            record: 데이터 저장 여부
            duration: 수집 시간 (초)
        """
        self.board = OpenBCIBLE(device_name=device_name)
        self.processor = SignalProcessor(fs=250)
        self.detectors = {ch: ThresholdDetector(threshold=15) for ch in range(8)}
        self.visualizer = RealtimeVisualizer(channels=[0, 1, 2, 3])

        self.recorder = None
        if record:
            self.recorder = DataRecorder()

        self.duration = duration
        self.sample_count = 0
        self.start_time = None

    async def on_sample(self, sample: Sample):
        """샘플 콜백"""
        self.sample_count += 1

        # 신호 처리
        self.processor.add_sample(sample.channel_data)

        # 데이터 기록
        if self.recorder:
            self.recorder.add_sample(sample)

        # 시각화 데이터 추가
        self.visualizer.add_sample(sample)

        # 1초마다 출력
        if self.sample_count % 250 == 0:
            elapsed = self.sample_count / 250
            rms_all = self.processor.compute_rms_all()

            print(f"\n[{elapsed:.1f}s] 패킷 ID: {sample.packet_id}")
            print(f"  EEG (µV):  {[f'{v:7.2f}' for v in sample.channel_data[:4]]}")
            print(f"  RMS (µV):  {[f'{rms_all[i]:7.2f}' for i in range(4)]}")

            # 채널 0의 Alpha 대역 파워
            alpha_power = self.processor.get_band_power(0, 'alpha')
            print(f"  Alpha Power (Ch0): {alpha_power:.2f} µV²")

            # 임계값 감지 (채널 0)
            rms = rms_all[0]
            if rms > 15:
                print(f"  ⚠️ 활성: RMS {rms:.2f} > 임계값 15")

    async def run(self):
        """애플리케이션 실행"""
        try:
            logger.info("=" * 60)
            logger.info("OpenBCI BLED112 데이터 수집 시작")
            logger.info(f"수집 시간: {self.duration}초")
            logger.info(f"데이터 저장: {'켜짐' if self.recorder else '꺼짐'}")
            logger.info("=" * 60)

            # 연결
            await self.board.connect()

            # 기록 시작
            if self.recorder:
                self.recorder.start_recording()

            # 스트리밍 시작
            await self.board.start_stream(callback=self.on_sample)

            # 지정된 시간만큼 수집
            await asyncio.sleep(self.duration)

        except KeyboardInterrupt:
            logger.info("사용자 중단")
        except Exception as e:
            logger.error(f"오류 발생: {e}")
            raise
        finally:
            # 정리
            await self.board.stop_stream()
            await self.board.disconnect()

            if self.recorder:
                self.recorder.stop_recording()

            # 시각화
            logger.info("\n시각화 생성 중...")
            self.visualizer.plot_channels(duration=10)
            self.visualizer.plot_spectrum()

            logger.info("=" * 60)
            logger.info(f"수집 완료: {self.sample_count} 샘플")
            logger.info(f"저장 위치: {self.recorder.filepath if self.recorder else 'N/A'}")
            logger.info("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="OpenBCI BLED112 신경신호 수집")
    parser.add_argument("--device", type=str, default="OpenBCI-Cyton",
                        help="BLE 장치명 (기본값: OpenBCI-Cyton)")
    parser.add_argument("--record", action="store_true",
                        help="CSV 파일로 데이터 저장")
    parser.add_argument("--duration", type=int, default=60,
                        help="수집 시간 (초, 기본값: 60)")

    args = parser.parse_args()

    app = OpenBCIApp(
        device_name=args.device,
        record=args.record,
        duration=args.duration
    )

    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
