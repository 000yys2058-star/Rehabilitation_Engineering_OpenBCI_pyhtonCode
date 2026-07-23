"""
OpenBCI BLED112 Bluetooth LE Driver

BLED112 동글을 통해 OpenBCI 보드에서 실시간 신경신호를 수집하는 드라이버.
비동기 BLE 클라이언트(bleak)를 사용하여 데이터를 스트리밍한다.

예제 사용법:
    board = OpenBCIBLE()
    board.connect()
    board.start_stream(callback=my_data_handler)
    # ...
    board.stop_stream()
    board.disconnect()
"""

import asyncio
import struct
import logging
from dataclasses import dataclass
from typing import Callable, Optional, List
from bleak import BleakClient, BleakScanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenBCI UUIDs (Cyton 보드)
GATT_CHARACTERISTICS = {
    "notify": "545a4030-4221-4da5-a2dd-4d42cb631f59",  # Notification characteristic
    "write": "545a4031-4221-4da5-a2dd-4d42cb631f59",   # Write characteristic
}

# 데이터 패킷 상수
START_BYTE = 0xA0
END_BYTE = 0xC0
SAMPLE_RATE = 250  # Hz
EEG_CHANNELS = 8
AUX_CHANNELS = 3


@dataclass
class Sample:
    """단일 샘플 데이터"""
    packet_id: int
    channel_data: List[float]  # 8 채널 EEG (uV)
    aux_data: List[float]      # 3 채널 AUX (가속도계)
    timestamp: float


class OpenBCIBLE:
    """OpenBCI BLED112 드라이버"""

    def __init__(self, device_name: str = "OpenBCI-Cyton"):
        """
        Args:
            device_name: BLE 스캔에서 찾을 OpenBCI 보드 이름
        """
        self.device_name = device_name
        self.client: Optional[BleakClient] = None
        self.is_streaming = False
        self._buffer = bytearray()
        self._packet_count = 0

    async def _find_device(self):
        """BLE 스캔으로 OpenBCI 보드 찾기"""
        logger.info(f"스캔 중: {self.device_name}...")
        devices = await BleakScanner.discover()

        for device in devices:
            if self.device_name.lower() in device.name.lower():
                logger.info(f"발견: {device.name} ({device.address})")
                return device.address

        raise RuntimeError(f"{self.device_name} 장치를 찾을 수 없습니다")

    async def connect(self):
        """OpenBCI 보드에 연결"""
        if self.client and self.client.is_connected:
            logger.warning("이미 연결되어 있습니다")
            return

        device_address = await self._find_device()
        self.client = BleakClient(device_address)

        try:
            await self.client.connect()
            logger.info(f"{device_address}에 연결됨")

            # 사용 가능한 서비스 확인
            for service in self.client.services:
                logger.debug(f"서비스: {service.uuid}")
        except Exception as e:
            logger.error(f"연결 실패: {e}")
            raise

    async def disconnect(self):
        """연결 해제"""
        if self.client:
            self.is_streaming = False
            await self.client.disconnect()
            logger.info("연결 해제됨")

    def _parse_packet(self, data: bytes) -> Optional[Sample]:
        """OpenBCI 데이터 패킷 파싱

        패킷 구조 (33 바이트):
        [0xA0][패킷ID][8채널×3바이트][3×AUX바이트][0xC0]
        """
        if len(data) < 33:
            return None

        if data[0] != START_BYTE or data[32] != END_BYTE:
            return None

        packet_id = data[1]

        # EEG 채널 데이터 파싱 (24-bit signed, little-endian)
        channel_data = []
        for i in range(EEG_CHANNELS):
            offset = 2 + i * 3
            # 24-bit 값을 32-bit signed integer로 변환
            raw = int.from_bytes(data[offset:offset+3], byteorder='big', signed=False)

            # 24-bit signed로 변환
            if raw & 0x800000:
                raw = raw - 0x1000000

            # uV로 변환 (OpenBCI Cyton: 4.5V / (2^24) / 24 * 1e6)
            uv = raw * 0.00000427246
            channel_data.append(uv)

        # AUX 데이터 (가속도계 또는 다른 센서)
        aux_data = []
        for i in range(AUX_CHANNELS):
            offset = 2 + EEG_CHANNELS * 3 + i * 2
            raw = int.from_bytes(data[offset:offset+2], byteorder='big', signed=True)
            aux_data.append(float(raw))

        self._packet_count += 1

        return Sample(
            packet_id=packet_id,
            channel_data=channel_data,
            aux_data=aux_data,
            timestamp=self._packet_count / SAMPLE_RATE
        )

    async def _notification_handler(self, characteristic, data: bytes, callback: Callable):
        """BLE 알림 콜백"""
        self._buffer.extend(data)

        # 완전한 패킷 찾기
        while len(self._buffer) >= 33:
            # START_BYTE 찾기
            start_idx = None
            for i in range(len(self._buffer) - 32):
                if self._buffer[i] == START_BYTE and self._buffer[i + 32] == END_BYTE:
                    start_idx = i
                    break

            if start_idx is None:
                break

            # 패킷 추출
            packet = bytes(self._buffer[start_idx:start_idx + 33])
            self._buffer = self._buffer[start_idx + 33:]

            # 파싱 및 콜백
            sample = self._parse_packet(packet)
            if sample and callback:
                try:
                    callback(sample)
                except Exception as e:
                    logger.error(f"콜백 에러: {e}")

    async def start_stream(self, callback: Callable[[Sample], None]):
        """데이터 스트리밍 시작

        Args:
            callback: Sample 객체를 받는 콜백 함수
        """
        if not self.client or not self.client.is_connected:
            raise RuntimeError("먼저 연결해야 합니다")

        self.is_streaming = True

        try:
            # Notify characteristic에서 알림 수신 시작
            await self.client.start_notify(
                GATT_CHARACTERISTICS["notify"],
                lambda char, data: asyncio.create_task(
                    self._notification_handler(char, data, callback)
                )
            )
            logger.info("스트리밍 시작")
        except Exception as e:
            logger.error(f"스트리밍 시작 실패: {e}")
            self.is_streaming = False
            raise

    async def stop_stream(self):
        """데이터 스트리밍 중지"""
        if self.client and self.client.is_connected:
            try:
                await self.client.stop_notify(GATT_CHARACTERISTICS["notify"])
                self.is_streaming = False
                logger.info("스트리밍 중지")
            except Exception as e:
                logger.error(f"스트리밍 중지 실패: {e}")

    async def send_command(self, command: str):
        """OpenBCI 명령 송신

        Args:
            command: 1문자 명령 ('s': 시작, 'x': 중지 등)
        """
        if not self.client or not self.client.is_connected:
            raise RuntimeError("먼저 연결해야 합니다")

        try:
            await self.client.write_gatt_char(
                GATT_CHARACTERISTICS["write"],
                command.encode()
            )
            logger.info(f"명령 송신: {command}")
        except Exception as e:
            logger.error(f"명령 송신 실패: {e}")
            raise


async def main_example():
    """사용 예제"""
    board = OpenBCIBLE(device_name="OpenBCI-Cyton")

    sample_count = 0

    def on_sample(sample: Sample):
        nonlocal sample_count
        sample_count += 1
        if sample_count % 250 == 0:  # 1초마다 출력
            print(f"[{sample.packet_id}] {sample.timestamp:.2f}s - "
                  f"Ch1: {sample.channel_data[0]:8.2f}uV | "
                  f"Accel: ({sample.aux_data[0]:6.0f}, {sample.aux_data[1]:6.0f}, {sample.aux_data[2]:6.0f})")

    try:
        await board.connect()
        await board.start_stream(callback=on_sample)

        # 10초 스트리밍
        await asyncio.sleep(10)

    except KeyboardInterrupt:
        logger.info("사용자 중단")
    finally:
        await board.stop_stream()
        await board.disconnect()


if __name__ == "__main__":
    asyncio.run(main_example())
