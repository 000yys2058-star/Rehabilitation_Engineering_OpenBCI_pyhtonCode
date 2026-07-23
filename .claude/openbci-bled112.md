# OpenBCI BLED112 Python 드라이버

## 프로젝트 개요

BLED112 Bluetooth LE 동글을 통해 OpenBCI Cyton 보드에서 **실시간 뇌파(EEG) 신호를 수집**하는 완전한 Python 애플리케이션입니다.

**목적:** MATLAB 대신 Python으로 신경신호를 빠르고 효율적으로 처리

---

## 기술 스택

| 계층 | 기술 | 역할 |
|------|------|------|
| **통신** | bleak (BLE) | OpenBCI ↔ PC 비동기 통신 |
| **신호 처리** | scipy, numpy | 필터링, 스펙트럼 분석, RMS |
| **데이터 관리** | pandas | CSV/NumPy 저장 |
| **시각화** | matplotlib | 실시간 파형 & 스펙트럼 플롯 |

---

## 아키텍처

```
OpenBCI (UART) ← BLED112 동글 ← PC (BLE)
                                  ↓
                        bled112_openbci.py (연결 & 패킷 파싱)
                                  ↓
                        signal_processor.py (필터 & 분석)
                                  ↓
                        data_recorder.py (저장 & 시각화)
                                  ↓
                          outputs/ (CSV, PNG, NPY)
```

---

## 데이터 흐름

### OpenBCI 패킷 구조 (33 바이트)

```
[0xA0] [PacketID] [Ch1:3B] ... [Ch8:3B] [AUX:3B] [0xC0]
 1B      1B       24B          24B      6B       1B
```

- **샘플링 레이트:** 250Hz
- **EEG 채널:** 8개
- **AUX 채널:** 3개 (가속도계)

### 신호 처리 파이프라인

```
Raw EEG (µV) 
    ↓
Butterworth Filter (5-50Hz)  [선택사항]
    ↓
RMS 계산 (10개 샘플 버퍼)
    ↓
Welch 파워 스펙트럼 (Delta/Theta/Alpha/Beta/Gamma)
    ↓
임계값 감지 (이벤트 생성)
```

---

## 파일 구조

```
openbci-bled112/
├── src/
│   ├── bled112_openbci.py      ← BLE 드라이버 (코어)
│   ├── signal_processor.py     ← 필터 & 분석
│   ├── data_recorder.py        ← 저장 & 시각화
│   └── main.py                 ← 통합 애플리케이션
├── outputs/                    ← 데이터 & 그래프 (git 제외)
├── README.md                   ← 사용자 가이드
├── requirements.txt            ← 의존성
└── .gitignore
```

---

## 핵심 클래스

### OpenBCIBLE
- **책임:** BLE 연결 및 패킷 파싱
- **주요 메서드:**
  - `connect()` - BLED112 찾기 & 연결
  - `start_stream(callback)` - 알림 수신 시작
  - `stop_stream()` - 스트리밍 중지

### SignalProcessor
- **책임:** 실시간 신호 처리
- **상태:**
  - `buffers[ch]`: 채널별 순환 버퍼 (250 샘플)
  - `filters[ch]`: 채널별 Butterworth IIR 필터
- **주요 메서드:**
  - `compute_rms()` - RMS 계산
  - `get_band_power()` - 대역 파워 ('alpha', 'beta' 등)

### DataRecorder
- **책임:** 데이터 저장
- **출력:** `outputs/OpenBCI_YYYYMMDD_HHMMSS.csv`

### RealtimeVisualizer
- **책임:** 시각화
- **출력:** 채널 파형 & 파워 스펙트럼 PNG

---

## 실행 예제

### 1. 기본 스트리밍 (60초)
```bash
python src/main.py --record --duration 60
```

### 2. 프로그래매틱 사용
```python
import asyncio
from src.bled112_openbci import OpenBCIBLE
from src.signal_processor import SignalProcessor

async def main():
    board = OpenBCIBLE()
    processor = SignalProcessor(fs=250)
    
    def on_sample(sample):
        processor.add_sample(sample.channel_data)
        rms = processor.compute_rms(channel=0)
        print(f"RMS: {rms:.2f} µV")
    
    await board.connect()
    await board.start_stream(callback=on_sample)
    await asyncio.sleep(10)
    await board.stop_stream()
    await board.disconnect()

asyncio.run(main())
```

---

## 중요 설계 결정

| 결정 | 이유 |
|------|------|
| **비동기 (async/await)** | 메인 스레드 블로킹 없이 실시간 통신 |
| **Butterworth IIR 필터** | MATLAB과 호환, 저지연 (대역통과 5-50Hz) |
| **순환 버퍼 (deque)** | 고정 메모리, 효율적인 슬라이딩 윈도우 |
| **상대 경로 (__file__)** | 다른 PC/디렉토리에서도 동일하게 동작 |

---

## 알려진 제한

1. **동글 페어링:** BLED112이 OpenBCI와 미리 페어링되어야 함
2. **패킷 손실:** 고부하 시 일부 패킷 손실 가능 (250Hz 샘플링 안정성 확보)
3. **MATLAB 호환성:** 아직 LSL(Lab Streaming Layer) 미지원

---

## 향후 개선

- [ ] LSL 스트림 추가 (MATLAB/Brainflow 호환)
- [ ] 머신러닝 분류 모듈 (손동작 인식)
- [ ] WebSocket 대시보드
- [ ] 멀티보드 동시 수집

---

## 환경

- **OS:** Windows 10/11
- **Python:** 3.7+
- **하드웨어:** BLED112 동글 + OpenBCI Cyton 보드

---

**작성일:** 2026-07-23  
**상태:** ✅ 완성 (기본 기능)
