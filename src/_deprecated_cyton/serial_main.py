"""
OpenBCI Serial (COM 포트) 드라이버 - 메인 실행 스크립트

BLED112 Serial 동글을 통해 OpenBCI 보드에서 신경신호를 수집합니다.
"""

import sys
import argparse
from pathlib import Path
from open_bci_v3 import OpenBCIBoard
from data_recorder import DataRecorder, RealtimeVisualizer
from signal_processor import SignalProcessor

class OpenBCISerialApp:
    """OpenBCI Serial 통신 애플리케이션"""

    def __init__(self, port=None, record=False, duration=60, baudrate=115200):
        """
        Args:
            port: COM 포트 (예: COM3)
            record: 데이터 저장 여부
            duration: 수집 시간 (초)
            baudrate: 통신 속도 (기본: 115200)
        """
        self.port = port
        self.baudrate = baudrate
        self.duration = duration
        self.sample_count = 0

        # OpenBCI 보드 연결
        try:
            if port:
                print(f"[*] {port}에 연결 중...")
                self.board = OpenBCIBoard(port=port, baud=baudrate)
            else:
                print("[*] OpenBCI 보드 자동 감지 중...")
                self.board = OpenBCIBoard(baud=baudrate)
        except Exception as e:
            print(f"[!] 연결 실패: {e}")
            raise

        # 신호 처리
        self.processor = SignalProcessor(fs=250)

        # 데이터 기록
        self.recorder = None
        if record:
            self.recorder = DataRecorder()
            self.recorder.start_recording()

        # 시각화
        self.visualizer = RealtimeVisualizer(channels=[0, 1, 2, 3])

    def on_sample(self, sample):
        """샘플 콜백"""
        self.sample_count += 1

        # 신호 처리
        self.processor.add_sample(sample.channel_data)

        # 데이터 기록
        if self.recorder:
            # OpenBCISample을 DataRecorder의 Sample 형식으로 변환
            from data_recorder import Sample
            converted_sample = Sample(
                packet_id=sample.id,
                channel_data=sample.channel_data,
                aux_data=sample.aux_data,
                timestamp=self.sample_count / 250
            )
            self.recorder.add_sample(converted_sample)

        # 시각화 데이터 추가
        viz_sample = type('Sample', (), {
            'channel_data': sample.channel_data,
            'aux_data': sample.aux_data,
            'packet_id': sample.id
        })()
        self.visualizer.add_sample(viz_sample)

        # 1초마다 출력
        if self.sample_count % 250 == 0:
            elapsed = self.sample_count / 250
            rms_all = self.processor.compute_rms_all()

            print(f"\n[{elapsed:.1f}s] 패킷 ID: {sample.id}")
            print(f"  EEG (µV):  {[f'{v:7.2f}' for v in sample.channel_data[:4]]}")
            print(f"  RMS (µV):  {[f'{rms_all[i]:7.2f}' for i in range(4)]}")

            # 채널 0의 Alpha 대역 파워
            try:
                alpha_power = self.processor.get_band_power(0, 'alpha')
                print(f"  Alpha Power (Ch0): {alpha_power:.2f} µV²")
            except:
                pass

    def run(self):
        """애플리케이션 실행"""
        print("=" * 60)
        print("OpenBCI Serial (COM) 데이터 수집 시작")
        print(f"포트: {self.board.port}")
        print(f"수집 시간: {self.duration}초")
        print(f"데이터 저장: {'켜짐' if self.recorder else '꺼짐'}")
        print("=" * 60)

        try:
            # 스트리밍 시작
            self.board.start_streaming(self.on_sample, self.duration)

        except KeyboardInterrupt:
            print("\n[*] 사용자 중단")
        except Exception as e:
            print(f"[!] 오류: {e}")
        finally:
            # 정리
            self.board.disconnect()

            if self.recorder:
                self.recorder.stop_recording()

            # 시각화
            print("\n[*] 시각화 생성 중...")
            try:
                self.visualizer.plot_channels(duration=10)
                self.visualizer.plot_spectrum()
            except Exception as e:
                print(f"[!] 시각화 실패: {e}")

            print("=" * 60)
            print(f"수집 완료: {self.sample_count} 샘플")
            if self.recorder:
                print(f"저장 위치: {self.recorder.filepath}")
            print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="OpenBCI Serial (COM) 신경신호 수집")
    parser.add_argument("--port", type=str, default=None,
                        help="COM 포트 (예: COM3, 생략 시 자동 감지)")
    parser.add_argument("--record", action="store_true",
                        help="CSV 파일로 데이터 저장")
    parser.add_argument("--duration", type=int, default=60,
                        help="수집 시간 (초, 기본값: 60)")
    parser.add_argument("--baudrate", type=int, default=115200,
                        help="통신 속도 (기본값: 115200)")

    args = parser.parse_args()

    app = OpenBCISerialApp(
        port=args.port,
        record=args.record,
        duration=args.duration,
        baudrate=args.baudrate
    )

    app.run()


if __name__ == "__main__":
    main()
