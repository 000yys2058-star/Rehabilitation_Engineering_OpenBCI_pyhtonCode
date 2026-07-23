# OpenBCI BLED112 - Python BLE 드라이버

BLED112 Bluetooth LE 동글을 통해 **OpenBCI Cyton 보드**에서 실시간 신경신호(EEG)를 수집하는 Python 라이브러리 및 애플리케이션입니다.

**특징:**
- ✅ **비동기 BLE 클라이언트** (bleak) - 안정적인 실시간 통신
- ✅ **신호 처리** - Butterworth 필터, RMS, 파워 스펙트럼
- ✅ **데이터 저장** - CSV, NumPy 포맷
- ✅ **실시간 시각화** - 채널별 파형 및 스펙트럼
- ✅ **이벤트 감지** - 임계값 기반 활성/비활성 감지

---

## 설치

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

**주요 패키지:**
- `bleak` (0.20.2+) - BLE 통신
- `numpy`, `scipy` - 신호 처리
- `pandas` - 데이터 관리
- `matplotlib` - 시각화

### 2. BLED112 드라이버 설정 (Windows)

1. BLED112 동글을 USB 포트에 연결 (예: COM3)
2. Windows 드라이버는 자동 설치됨
3. 장치 관리자에서 "Silicon Labs CP210x USB to UART Bridge" 확인

---

## 빠른 시작

### 기본 사용법

```bash
# 60초 데이터 수집 (CSV 저장)
python src/main.py --record --duration 60

# 커스텀 장치명 사용
python src/main.py --device "OpenBCI-Cyton" --record --duration 120
```

### Python 코드에서 직접 사용

```python
import asyncio
from src.bled112_openbci import OpenBCIBLE

async def main():
    board = OpenBCIBLE(device_name="OpenBCI-Cyton")
    
    def on_data(sample):
        print(f"Ch1: {sample.channel_data[0]:.2f} µV")
    
    await board.connect()
    await board.start_stream(callback=on_data)
    
    await asyncio.sleep(10)  # 10초 수집
    
    await board.stop_stream()
    await board.disconnect()

asyncio.run(main())
```

---

## 모듈 설명

### 1. `bled112_openbci.py` - BLE 드라이버
OpenBCI 보드와의 Bluetooth Low Energy 통신을 담당합니다.

**주요 클래스:**
- `OpenBCIBLE` - BLE 클라이언트
  - `connect()` - 보드 연결
  - `start_stream(callback)` - 스트리밍 시작
  - `stop_stream()` - 스트리밍 중지
  - `send_command(cmd)` - 명령 송신

**데이터 구조:**
- `Sample` - 단일 샘플
  - `packet_id` (int) - 패킷 ID
  - `channel_data` (List[float]) - 8개 EEG 채널 (µV)
  - `aux_data` (List[float]) - 3개 AUX 채널 (가속도계)
  - `timestamp` (float) - 수집 시간 (초)

### 2. `signal_processor.py` - 신호 처리
실시간 신경신호 필터링 및 분석을 수행합니다.

**주요 클래스:**
- `SignalProcessor` - 신호 처리
  - `add_sample()` - 새 샘플 추가
  - `compute_rms()` - RMS 계산
  - `get_power_spectrum()` - 파워 스펙트럼
  - `get_band_power()` - 대역 파워 ('alpha', 'beta', 등)

- `ButterworthFilter` - IIR 필터
  - 5-50Hz 대역통과 (기본값)

- `ThresholdDetector` - 임계값 감지
  - RMS 기반 이벤트 감지

### 3. `data_recorder.py` - 데이터 저장
신호를 파일로 저장하고 시각화합니다.

**주요 클래스:**
- `DataRecorder` - 데이터 기록
  - `start_recording()` - 기록 시작
  - `add_sample()` - 샘플 추가
  - `stop_recording()` - 파일 저장
  - `save_numpy()` - NumPy 형식 저장

- `RealtimeVisualizer` - 시각화
  - `plot_channels()` - 채널 파형 플롯
  - `plot_spectrum()` - 파워 스펙트럼 플롯

### 4. `main.py` - 메인 애플리케이션
모든 기능을 통합한 완전한 데이터 수집 애플리케이션입니다.

---

## 데이터 포맷

### CSV 출력 예시

```
timestamp,packet_id,EEG_Ch1,EEG_Ch2,...,EEG_Ch8,AUX_1,AUX_2,AUX_3
0.00,0,12.34,45.67,...,-23.45,100,200,300
0.004,1,12.45,45.78,...,-23.56,101,201,301
...
```

### NumPy 출력 (shape: [samples, 8])
```python
data = np.load("OpenBCI_*.npy")
# data[i, j] = i번째 샘플의 j번째 채널 값 (µV)
```

---

## 트러블슈팅

### 1. "장치를 찾을 수 없습니다"

**원인:** BLED112이 OpenBCI와 페어링되지 않음

**해결:**
```bash
# Windows 설정에서 Bluetooth 페어링 수동 진행
# 또는 OpenBCI GUI에서 먼저 연결 테스트
```

### 2. "패킷 손실"

**원인:** 높은 시스템 부하

**해결:**
- 다른 애플리케이션 종료
- 샘플링 레이트 확인 (250Hz 유지)

### 3. 한글 텍스트 깨짐

**해결:** `matplotlib` 한글 폰트 설정
```python
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"  # Windows
```

---

## 신호 처리 팁

### Alpha 대역 파워 계산 (명상/휴식 상태)
```python
processor = SignalProcessor(fs=250)
for sample in samples:
    processor.add_sample(sample.channel_data)

alpha = processor.get_band_power(channel=0, band_name='alpha')
# alpha: 8-12Hz 대역 전력 (µV²)
```

### 실시간 RMS 기반 활성 감지
```python
detector = ThresholdDetector(threshold=15, min_duration=10)

rms = processor.compute_rms(channel=0)
event = detector.detect(rms)  # True: 시작, False: 종료, None: 상태 유지

if event is True:
    print("근육 활성!")
elif event is False:
    print("근육 이완")
```

---

## 향후 확장

- [ ] MATLAB LSL 호환성 (Lab Streaming Layer)
- [ ] 다중 채널 동시 분류 (머신러닝)
- [ ] WebSocket 실시간 대시보드
- [ ] 클라우드 데이터 업로드

---

## 참고

- [OpenBCI 공식 문서](https://docs.openbci.com/)
- [bleak 라이브러리](https://bleak.readthedocs.io/)
- [신호 처리 (scipy)](https://docs.scipy.org/doc/scipy/reference/signal.html)

---

**마지막 업데이트:** 2026-07-23  
**작성자:** Claude Code  
**라이센스:** MIT
