# OpenBCI Ganglion 실습 프로젝트

*마지막 업데이트: 2026-07-23*

## 이 프로젝트가 뭔가

UNIST **재활재생개론** 수업의 신경신호 실습 코드.
학생들이 OpenBCI Ganglion 보드로 EEG/EMG를 직접 수집하고 처리해 보는 것이 목적.

기존 MATLAB Live Script 실습(`F:\matlab code\2024\rehabilitation_Matlab\Rehabilitation1.mlx`, `Rehabilitation2.mlx`)을
**파이썬 Jupyter Notebook**으로 옮긴 것. MATLAB이 느리고 쓸 수 있는 도구가 적다는 이유.

- GitHub: https://github.com/000yys2058-star/Rehabilitation_Engineering_OpenBCI_pyhtonCode
- 로컬: `C:\Users\000yy\OneDrive\UNIST\Python\openbci-bled112\`
- 원본 수업 자료: `C:\Users\000yy\OneDrive\UNIST\대학원\2024\재활재생개론\`

---

## ⚠️ 하드웨어 — 반드시 먼저 확인할 것

| 항목 | 값 |
| --- | --- |
| 보드 | **OpenBCI Ganglion** (Cyton 아님) |
| EEG 채널 | **4개** |
| 샘플링 레이트 | **200 Hz** |
| 연결 | **BLED112 USB 동글** → COM3 |
| 보드 식별 | BLE 광고 이름 `Ganglion-3587` 형태 |
| PC 내장 BLE | **없음** (bleak가 "No Bluetooth adapter found" 반환) |

> Cyton(8채널·250Hz)과 혼동하지 말 것. 사양이 다르면 필터 설계와 주파수 축이 전부 틀어짐.

---

## 유일하게 올바른 접근: BrainFlow

OpenBCI GUI v5도 내부적으로 BrainFlow를 사용한다 (GUI 화면의 `BRAINFLOW STREAMER` 항목).
직접 시리얼 프로토콜을 파싱하지 말고 BrainFlow에 맡길 것.

```python
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

params = BrainFlowInputParams()
params.serial_port = 'COM3'    # BLED112 동글 포트 — 필수
params.mac_address = ''        # 특정 보드 지정 — 선택, 비우면 자동탐색
params.timeout     = 20        # 기본 15초

board = BoardShim(BoardIds.GANGLION_BOARD, params)   # board_id = 1
board.prepare_session()
board.start_stream()
# ...
data = board.get_board_data()      # (행=채널, 열=시간)
board.stop_stream()
board.release_session()

FS  = BoardShim.get_sampling_rate(BoardIds.GANGLION_BOARD)   # 200
CHS = BoardShim.get_eeg_channels(BoardIds.GANGLION_BOARD)    # EEG 행 인덱스
```

### BoardIds 선택 기준

| BoardIds | 연결 방식 | 이 환경에서 |
| --- | --- | --- |
| `GANGLION_BOARD` (1) | BLED112 동글 + `serial_port` | ✅ **이걸 사용** |
| `GANGLION_NATIVE_BOARD` (46) | PC 내장 BLE + `mac_address`/`serial_number` | ❌ 내장 BLE 없음 |

### 🔴 brainflow 버전을 5.20.0 으로 고정할 것 (가장 중요)

**최신 brainflow 를 설치하면 연결이 안 된다.** 2026-07-23 실측 결과:

| brainflow | 결과 |
| --- | --- |
| **5.20.0** | ✅ **연결 성공** (2.3초), 200Hz 정상 수집 |
| 5.22.2 | ❌ 0.0초 만에 실패. 스캔조차 시작하지 못함 |

5.22.2 로그:
```
[info]  Setting firmware version to 3
[warning] BoardIds::GANGLION_BOARD uses deprecated BLED112/bglib support
[info]  mac address is not specified, try to find ganglion without it
[error] failed to Open Ganglion Device 13      <- 즉시 실패
```

5.20.0 로그 (보드를 실제로 찾음):
```
[info]  mac address is not specified, try to find ganglion without it
[info]  detected firmware version 2            <- 31.8초 스캔 후 보드 발견
```

핵심 차이:
- 5.22.2 는 **0.0초**에 실패 → BLE 스캔 자체를 안 함. BLED112 경로가 사실상 죽어 있음.
  (존재하지 않는 포트 COM99 로 시도해도 **똑같이 에러 13** → 포트를 보지도 않는다는 뜻)
- 5.20.0 은 정상적으로 스캔하고 **보드의 펌웨어 버전 2를 읽어냄**

`other_info='fw:2'` 로 펌웨어를 강제해도 5.22.2 에서는 해결되지 않음 (확인함).

**부수 조건**: 5.20.0 은 `pkg_resources` 를 쓰므로 `setuptools<81` 이 함께 필요하다
(setuptools 81 에서 `pkg_resources` 제거됨). requirements.txt 에 명시되어 있음.

노트북 1단계 셀이 버전을 확인해 자동으로 맞춰 설치한다.

### mac_address 관련

- 비우면 → BrainFlow가 자동 탐색. **주변에 Ganglion이 하나일 때만 안전.**
- **강의실처럼 여러 보드가 켜져 있으면 반드시 지정.** 안 그러면 옆 사람 보드에 붙음.
- GUI에 보이는 `Ganglion-3587`은 **BLE 광고 이름**이고, `mac_address`는 **MAC 주소**(`d2:b4:11:81:48:ad` 형태). 서로 다름.
- MAC 찾는 법 (Windows): Microsoft Store의 **Bluetooth LE Explorer** 앱으로 스캔.
- BrainFlow 소스(`ganglion.cpp`)는 이 문자열을 검증 없이 GanglionLib에 그대로 전달함.

---

## 파일 구조

```
openbci-bled112/
├── src/
│   ├── Ganglion_Tutorial.ipynb    ← ⭐ 실습의 전부. 이것만 쓰면 됨
│   └── _deprecated_cyton/         ← 폐기 (Cyton/BLE 기반, 동작 안 함)
├── outputs/                       ← CSV·그림 (git 제외)
├── requirements.txt
└── .claude/openbci-bled112.md     ← 이 문서
```

`Ganglion_Tutorial.ipynb`는 **자체 완결형**. 다른 .py 모듈에 의존하지 않는다.
학생이 노트북 하나만 열면 끝나도록 의도한 설계.

---

## 노트북 구성 (14단계)

| 단계 | 내용 |
| --- | --- |
| 1 | 라이브러리 (brainflow 자동 설치 포함) |
| 2 | COM 포트 탐색 |
| 3 | **설정 — 학생이 고치는 유일한 셀** (`COM_PORT`, `BOARD_MAC`, `DURATION_SEC`) |
| 4 | 보드 사양 확인 (연결 없이) + MAC 찾는 법 안내 |
| 5 | `prepare_session()` 연결 |
| 6 | 스트리밍 + 진행 표시 |
| 7 | DataFrame 변환 |
| 8 | 원본 신호 플롯 (필터가 왜 필요한지 보여줌) |
| 9 | 대역통과 + 60Hz 노치 필터 |
| 10 | 필터 전후 비교 플롯 |
| 11 | 구간별 RMS + 임계값 (MATLAB 실습의 서보 제어와 연결) |
| 12 | Welch 파워 스펙트럼 + 대역별 비율 |
| 13 | CSV 저장 |
| 14 | `release_session()` — **안 하면 동글이 계속 점유됨** |

교육 설계 원칙:
- markdown 셀로 "왜 이걸 하는지" 먼저 설명 → 코드 셀
- 학생이 값을 바꿔 재실행하도록 유도 (`🧪 해 볼 것` 블록)
- 에러 메시지에 점검 목록을 함께 출력

---

## 실행 방법

```powershell
cd "C:\Users\000yy\OneDrive\UNIST\Python\openbci-bled112"
pip install -r requirements.txt
jupyter notebook src/Ganglion_Tutorial.ipynb
```

> **PowerShell 명령줄 방식은 교육용으로 부적합하다**는 것이 사용자의 명확한 요구.
> 학생 대상 인터페이스는 Jupyter Notebook 하나로 통일할 것.

---

## 자주 겪는 문제

| 증상 | 원인 |
| --- | --- |
| 연결 실패 | **OpenBCI GUI가 동글을 점유 중** — 압도적으로 흔한 원인 |
| 샘플 0개 | 보드 전원 / 배터리 / 전극 |
| 엉뚱한 보드 연결 | `BOARD_MAC` 미지정 상태에서 여러 보드가 켜져 있음 |
| 다음 실행이 안 됨 | 14단계 `release_session()` 누락 → 커널 재시작으로 해결 |

### 환경 이슈 (해결됨)

Microsoft Store 版 Python 3.13에서 `pip install`이 `Cannot import 'setuptools.build_meta'`로 실패.
- 원인: requirements.txt에 고정된 구버전(`numpy==1.24.3` 등)이 3.13용 휠이 없어 소스 빌드를 시도
- 해결: 버전 고정을 `>=`로 완화. 필요시 `pip install --no-build-isolation -r requirements.txt`

---

## 시행착오 기록 (같은 실수 반복 금지)

1. **Cyton 드라이버를 Ganglion에 적용하려 함** — `open_bci_v3.py`(OpenBCI_LSL 소속)는 Cyton 전용 시리얼 파서. Ganglion은 BLE라 프로토콜 자체가 다름. 폐기함.
2. **`bleak`로 네이티브 BLE 시도** — PC에 BLE 어댑터가 없고, 애초에 BLED112는 네이티브 BLE가 아니라 동글 뒤의 가상 시리얼 포트. 폐기함.
3. **8채널·250Hz로 가정** — Ganglion은 4채널·200Hz.
4. **brainflow 최신 버전 사용** — 5.22.2 는 BLED112 지원이 죽어 있어 연결 불가. 5.20.0 고정 필수.
5. **"MAC 주소를 몰라서 연결이 안 된다"고 판단** — 실제 원인은 라이브러리 버전이었음.
   BLED112 방식은 MAC 이 원래 선택 사항이라, 자동 탐색 실패는 대개 다른 원인이다.
6. **노트북 편집 스크립트에서 `source` 를 리스트로 가정** — nbformat 의 `source` 는
   리스트일 수도 문자열일 수도 있다. 문자열을 for 로 돌리면 글자 단위로 쪼개져 파일이 깨진다.
   반드시 `''.join(s) if isinstance(s, list) else s` 로 정규화할 것.

교훈:
- 보드 모델을 먼저 확정하고, 채널 수와 샘플링 레이트는 `BoardShim.get_*()`로 조회. 하드코딩 금지.
- 연결 실패는 **실패까지 걸린 시간**이 가장 중요한 단서다.
  0초 실패 = 라이브러리/포트 문제, 타임아웃까지 걸림 = 실제로 스캔했으나 못 찾음.
- 가설을 세웠으면 **버전을 바꿔가며 실제로 돌려서** 확인할 것.

## 진단 도구

노트북 **5-A단계** 셀: BrainFlow 내부 로그를 파일로 받아
- 발견된 BLE 장치의 MAC 주소를 정규식으로 추출
- 로그 마지막 30줄 출력 (에러 코드로 원인 특정)

수동 진단 명령:
```powershell
# COM 포트 점유 여부
python -c "import serial; s=serial.Serial('COM3',115200,timeout=1); print('비어있음'); s.close()"

# OpenBCI GUI(javaw) 가 살아있는지
Get-Process | Where-Object { $_.ProcessName -match 'javaw|openbci' }
```

BLED112 동글의 하드웨어 ID: `USB VID:PID=2458:0001` (2458 = Bluegiga)

---

## 다음에 할 만한 것

- [ ] EMG + 아두이노 서보 제어 (MATLAB `파이썬 코드.txt` 실습의 파이썬 이식)
- [ ] 실시간 스트리밍 버전 (현재는 수집 후 일괄 처리)
- [ ] 손동작 분류 (머신러닝)
- [ ] 보드별 MAC 주소 대조표를 노트북에 내장
