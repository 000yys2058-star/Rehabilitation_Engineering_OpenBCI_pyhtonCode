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
단, setuptools 83 에서도 `pkg_resources` 는 경고만 내고 아직 동작하므로,
노트북은 `import pkg_resources` 가 실패할 때만 다운그레이드한다.

### 🔴 버전을 바꿨으면 커널 재시작 — 디스크 버전만 봐선 안 된다

**DLL 은 한 번 프로세스에 로드되면 파일을 교체해도 메모리 안에서는 바뀌지 않는다.**

이것 때문에 실제로 오래 헤맸다. 상황:
- 디스크: 5.20.0 (pip 설치 완료)
- 커널: 5.22.2 를 메모리에 보유 (설치 전에 시작된 프로세스)
- `importlib.metadata.version('brainflow')` → **5.20.0** 이라고 답함 (디스크만 봄)
- 결과: "5.20.0 준비 완료" 라고 표시되면서 **0초 만에 연결 실패**

해결: **`BoardShim.get_version()`** 이 실제 로드된 네이티브 라이브러리 버전을 반환한다.

```python
from importlib.metadata import version as pkg_version
pkg_version('brainflow')     # 디스크에 설치된 버전
BoardShim.get_version()      # 실제 메모리에 로드된 DLL 버전  <- 이걸 봐야 함
```

노트북 1단계 셀은 두 값을 모두 확인하고, 불일치하면 커널 재시작을 안내하며 중단한다.
최종 출력에도 `(실제 로드된 버전)` 이라고 명시한다.

**진단 팁**: 프로세스 시작 시각과 pip 설치 시각을 비교하면 확실하다.
```powershell
Get-Process | Where-Object { $_.ProcessName -match 'python|javaw' } |
  Select-Object Id, ProcessName, @{N='시작';E={$_.StartTime.ToString('HH:mm:ss')}}
```
프로세스 시작이 설치보다 앞서면 그 커널은 옛 DLL 을 쓰고 있다.

또한 커널이 DLL 을 잡고 있으면 pip 가 파일을 지우지 못해
`WARNING: Failed to remove contents in a temporary directory '...\~rainflow'` 가 뜬다.
이 경고가 보이면 설치가 불완전할 수 있으니 커널을 끄고 재설치할 것.

### 🔴 mac_address 는 BLED112 경로에서 무시된다 (2026-07-24 실측)

**`params.mac_address` 를 지정해도 보드가 선택되지 않는다.** 값을 받아 로그에
`search for <MAC>` 을 찍지만 실제 필터링에 쓰지 않고, 먼저 응답한 보드에 연결한다.

보드 2대를 켜고 검증한 결과:

| 지정 MAC | 결과 |
| --- | --- |
| `f6:83:23:ca:c1:29` (실제 보드 A = Ganglion-3587) | 1.5초 연결 |
| `c5:cf:b4:83:e8:c6` (실제 보드 B = Ganglion-c57c) | 1.7초 연결 |
| `11:22:33:44:55:66` (**존재하지 않는 가짜**) | **1.5초 연결** ← 결정적 증거 |

**결정적 증거** — 주변에 실재하는 **청소기**의 MAC 을 요청했더니 Ganglion 에 연결되어
EEG 데이터까지 정상 수신됨:
```
[info] search for bc:10:2f:e3:eb:38   <- 청소기(vacuum) 의 MAC
[info] detected firmware version 2     <- Ganglion 에 연결
수신 데이터 (15, 309)
```

### 검증 시 주의 — 오판하기 쉬움

중간에 "MAC 필터링이 동작한다"고 잘못 결론냈다가 번복했다. 원인:
**Ganglion 이 일시적으로 응답하지 않으면 26초 타임아웃으로 실패**하는데,
이것을 "MAC 이 안 맞아서 거부됐다"고 오해하기 쉽다.

구분법:
- **1.5초 연결** = 아무 보드에나 붙음 (MAC 무시)
- **26초 실패** = 보드를 못 찾음 (MAC 과 무관, 보드 상태 문제)

가짜 MAC 을 여러 번, 동글 하드리셋(BGAPI system_reset) + 새 프로세스로
반복 시험해야 확실하다. 한 프로세스 안에서 연속 시도하면 상태가 섞인다.

**따라서 강의실 다중 보드 문제는 MAC 으로 해결할 수 없다.**

실제로 통하는 대안 (노트북에 반영됨):
1. **내 보드만 켠다** — 가장 확실
2. **한 대씩 순서대로 연결** — BLE 보드는 연결되면 광고를 멈추므로 다음 사람에게 안 잡힘
   (동글이 1개뿐이라 "연결 시 광고 중단"은 직접 검증 못 함. BLE 표준 동작에 근거)
3. **연결 후 힘줘서 신호 반응 확인** — 남의 보드면 반응이 없다.
   2차시 5단계(실시간 신호 확인)가 이 역할을 겸함

### ✅ 채택한 해법: 안전 게이트 (노트북에 구현됨)

사용자 결정 (2026-07-24): **학생 전원에게 BLED112 동글 배부. 내장 BLE 는 쓰지 않는다**
(변수를 늘리지 않기 위해). 따라서 BLED112 만으로 해결해야 한다.

전략: **고를 수 없다면 고를 여지를 없앤다.**
연결 시점에 광고 중인 Ganglion 이 1대뿐이면 선착순이어도 반드시 그 보드에 연결된다.

노트북 「내 보드 확인」 셀이 스캔 후 판정:
- 1대 → `SAFE_TO_CONNECT=True`, `TARGET_BOARD=이름` 설정 후 통과
- 2대 이상 / 0대 → `SAFE_TO_CONNECT=False`, 안내 출력
- 연결 셀 첫머리에서 `SAFE_TO_CONNECT` 를 확인해 아니면 `raise SystemExit`

강의실 절차: 모든 보드 OFF → 한 명씩 자기 보드만 ON → 확인 → 연결 → 유지.
연결된 보드는 광고를 멈추므로 다음 사람에게 안 잡힘.

**실증** (2026-07-24): BrainFlow 는 평소 가까운 3587(-61dBm)을 골랐는데,
3587 을 BGAPI 로 점유해 광고를 멈추게 하니 먼 c57c(-73dBm)에 연결됨.
게이트 차단(2대)과 통과 후 연결(1대) 양쪽 모두 노트북 셀로 실행 검증 완료.

### 보드 선택이 정말 필요하면 — 남은 두 가지 길

**1) `GANGLION_NATIVE_BOARD` (내장 BLE) — 가장 유망, 미검증**
동글 없이 PC 내장 블루투스로 직접 연결하는 경로. 이쪽은 `mac_address` / `serial_number`
가 문서상 정식 파라미터이고, BLED112 의 레거시 GanglionLib 을 거치지 않는다.
- 이 PC 는 내장 BLE 가 없어 확인 불가 (bleak: "No Bluetooth adapter found")
- **요즘 노트북은 대부분 BLE 가 있으므로 학생 PC 에서는 시험해 볼 가치가 큼**
- 확인법: `python -c "import asyncio,bleak; asyncio.run(bleak.BleakScanner.discover())"`

**2) BGAPI 자체 드라이버 — 절반은 이미 검증됨**

`gap_connect_direct` 로 **특정 MAC 연결이 정확히 동작함을 확인했다** (2026-07-24):
```
connect_direct 응답: result=0x0000 handle=0
connection_status: flags=0x05 peer=f6:83:23:ca:c1:29   <- 요청한 바로 그 보드
```
점유하면 해당 보드가 광고를 멈추는 것도 확인 (스캔에서 사라짐).

**주의**: `gap_connect_direct` 의 supervision timeout 인자를 짧게 주면
연결이 곧바로 끊긴다. `0x0064`(=1초)로 했더니 1초 만에 끊겼고,
`0x0C80`(=32초)로 늘리니 20초 이상 안정 유지됨.
payload: `addr[6] + atype[1] + struct.pack('<HHHH', int_min, int_max, timeout, latency)`

남은 작업: GATT 특성 구독 + Ganglion 20바이트 델타압축 패킷 디코딩.

### ❌ 실패한 우회책: 원치 않는 보드를 미리 점유하기

"BrainFlow 가 MAC 을 무시하니, 다른 보드를 미리 점유해 광고를 멈추게 하면
내 보드만 남는다"는 전략을 시험했으나 **실패**했다.

```
[1] 3587 점유 성공 -> 광고중: ['Ganglion-c57c'] 만 남음   (여기까지는 성공)
[2] BrainFlow 연결 시도 -> 26.9초 실패
[3] 확인 -> 3587 이 다시 광고 중 = 점유가 풀렸음
```

**원인**: BrainFlow 의 GanglionLib 이 포트를 열 때 동글을 리셋해 기존 연결을 모두 끊는다.
따라서 BrainFlow 를 쓰는 한, 미리 만들어 둔 어떤 상태도 유지되지 않는다.

### 이 PC 의 제약
`Get-PnpDevice -Class Bluetooth` 결과 **블루투스 라디오가 아예 없음**.
`GANGLION_NATIVE_BOARD` 경로는 이 PC 에서 검증 불가.

- GUI에 보이는 `Ganglion-3587`은 **BLE 광고 이름**이고, `mac_address`는 **MAC 주소**(`f6:83:23:ca:c1:29` 형태). 서로 다름.
- 이름은 스캔으로 확인 가능하지만 **연결 대상 선택에는 쓸 수 없다.**
- BrainFlow 소스(`ganglion.cpp`)는 이 문자열을 검증 없이 GanglionLib에 그대로 전달함.

### ⚠️ BrainFlow 로그에는 MAC 이 찍히지 않는다 (2026-07-24 확인)

한때 "5-A 진단 셀이 로그에서 MAC 을 정규식으로 추출한다"고 만들었으나 **틀렸다.**
BrainFlow 는 발견한 장치의 MAC 을 로그에 남기지 않는다. 실제 로그는 이게 전부다:
```
[info] mac address is not specified, try to find ganglion without it
[info] detected firmware version 2      <- 보드를 찾아도 MAC 은 안 나옴
```
해당 셀은 시간 기반 진단으로 교체했다.

### ✅ 해결: 동글에 BGAPI 를 직접 보내 스캔 (노트북 「내 보드 찾기」 셀)

BLED112 는 Bluegiga BGAPI 를 쓰는 시리얼 장치다. pyserial 로 직접 명령을 보내면
주변 BLE 장치의 **MAC + 이름 + RSSI** 를 얻을 수 있다. 외부 도구 불필요.

BGAPI 패킷: 헤더 4바이트 `[type|tech|len_hi][len_lo][class][method]` + payload
- `type`: 0x00 = command, 0x80 = event
- GAP class = 0x06
  - `gap_set_scan_parameters` method 0x07, payload 5B (interval2, window2, active1)
  - `gap_discover` method 0x02, payload 1B (mode: 2 = observation)
  - `gap_end_procedure` method 0x04, payload 없음
  - `gap_scan_response` (event) method 0x00
    payload: rssi(1) type(1) sender(6, **little-endian MAC**) addr_type(1) bond(1) data_len(1) data(가변)
- 이름은 data 안의 AD 구조에서 타입 `0x08`(단축) / `0x09`(완전) 로 파싱

**주의**: BrainFlow 세션이 열려 있으면 동글이 점유되어 스캔 실패. 연결 해제 후 실행할 것.

**스캐너의 용도**: 주변에 Ganglion 이 몇 대 켜져 있는지 파악하는 것.
1대면 자동 탐색이 안전, 여러 대면 순차 연결 절차를 따르라고 안내한다.
**MAC 을 얻어도 연결 대상 선택에는 쓸 수 없다** (위 참조).

검증 (2026-07-24, 보드 2대 ON):
```
  -58 dBm   f6:83:23:ca:c1:29   'Ganglion-3587'
  -69 dBm   c5:cf:b4:83:e8:c6   'Ganglion-c57c'
```
이름·MAC·RSSI 모두 정상 수집. 이름 필터(`'gang' in name.lower()`)도 정확히 동작.
주변 BLE 장치 총 28개 중 Ganglion 2개를 정확히 골라냄.

외부 도구 대안: Bluetooth LE Explorer(Windows Store),
nRF Connect(**안드로이드만** — iOS 는 개인정보 정책상 무작위 UUID 만 표시).

---

## 파일 구조

```
openbci-bled112/
├── src/
│   ├── Ganglion_Tutorial.ipynb    ← ⭐ 실습의 전부. 이것만 쓰면 됨
│   └── _deprecated_cyton/         ← 폐기 (Cyton/BLE 기반, 동작 안 함)
│       └── README.md              ← 각 파일이 왜 폐기됐는지
├── outputs/                       ← CSV·그림 (git 제외)
├── README.md                      ← 학생/사용자용 문서
├── requirements.txt               ← brainflow==5.20.0 고정 (이유 주석 포함)
├── .gitignore                     ← outputs/, brainflow_debug.log 제외
└── .claude/openbci-bled112.md     ← 이 문서
```

두 노트북 모두 **자체 완결형**. 다른 .py 모듈에 의존하지 않는다.
학생이 노트북 하나만 열면 끝나도록 의도한 설계.

## 2차시: 실시간 손동작 분류 (Ganglion_Tutorial_2_Classification.ipynb)

원본: MATLAB `F:\matlab code\2024\rehabilitation_Matlab\Randomforest_code.m`,
`Rehabilitation2.mlx`. 실시간 EMG → epoching → Random Forest → 가위/바위/보.

### 파이프라인
```
팔 EMG 4채널 → 60Hz 노치 + 30-95Hz 대역통과 → 포락선 평균(|hilbert|) = 특징 4개
  → 캘리브레이션(동작 × 40회, 100샘플 창) → RandomForest(100 trees)
  → joblib 저장 → 실시간 판정(최근 5회 다수결)
```

### 원본에서 의도적으로 바꾼 것
1. **30-100Hz → 30-95Hz**: 200Hz 샘플링의 나이퀴스트가 정확히 100Hz라
   scipy `butter` 는 `Wn=1.0` 에서 에러. MATLAB 은 관대해서 통과했을 뿐.
   100Hz 성분은 어차피 없어 손실 없음.
2. **randperm → 시간순 분할**: 연속 수집한 이웃 샘플이 학습/시험에 나뉘면
   데이터 누수로 정확도 과대평가. 각 동작 앞 80% 학습 / 뒤 20% 시험.
3. **매 프레임 예측 → 다수결 안정화**: deque(maxlen=5) 최빈값. 손떨림 방지.
4. **filtfilt 통일**: 원본은 filter/filtfilt 혼용. 창 단위 오프라인 처리라 영위상이 맞음.
5. **joblib 모델 저장 추가**: MATLAB 엔 없던 것. 모델+메타데이터(fs/필터/동작/정확도/날짜)
   를 dict 로 묶어 저장. 사용자 요구는 "캘리브레이션은 매번, 모델 저장도 중요".
   활용: 지난주 모델 vs 오늘, 친구 모델로 내 신호 판정 → BCI calibration transfer 교육.

### 사용자가 확정한 범위 (2026-07-24)
- 서보 제어는 **제외** (분류 화면 출력까지만). 아두이노는 3차시/과제로.
- 동작은 가위/바위/보 3종 유지.
- 캘리브레이션은 매번 수행하되 **학습된 모델은 저장**.
- 평가는 시간순 분할.

### 교육 설계 - 관문 2개
- **5단계 실시간 신호 확인**: 힘줬을 때 파형이 커지나 → 전극 문제를 40×3회 수집 전에 잡음
- **8단계 근육 활성 지문**(polarplot 3개): 세 동작이 구분되나 → 안 되면 전극 재부착

### 추가 의존성
`scikit-learn>=1.4.0`, `joblib>=1.3.0` (requirements.txt 에 있음).
1단계 셀이 brainflow 5.20.0 확인과 함께 sklearn/joblib 도 없으면 설치.

### 검증 상태 (2026-07-24, 합성 EMG)
하드웨어 불필요 셀(1,3,5,8,9,10,12) 전부 실행 통과.
필터·특징추출·시간순분할·joblib 저장/불러오기·다수결 확인.
**미검증: 실제 EMG 로 세 동작이 구분되는지** (근육 없이는 확인 불가.
원본이 검증한 설정 30-95Hz/40회/100샘플 그대로 사용).

---

## 노트북 구성 (14단계)

| 단계 | 내용 |
| --- | --- |
| 1 | 라이브러리 + **brainflow 버전 확인/자동 설치 + 커널 재시작 감지** |
| 2 | COM 포트 탐색 |
| 3 | **설정 — 학생이 고치는 유일한 셀** (`COM_PORT`, `BOARD_MAC`, `DURATION_SEC`) |
| 4 | 보드 사양 확인 (연결 없이) + MAC 찾는 법 안내 |
| 5 | `prepare_session()` 연결 — **최대 3회 자동 재시도, timeout 40초** |
| **5-A** | **연결 진단 (실패 시에만)** — 로그에서 MAC 추출 + 원인 파악 |
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
| **0초 만에** 연결 실패 | brainflow 버전 문제. 디스크 5.20.0 이어도 **커널 재시작 안 했으면 동일 증상** |
| 오래 기다리다 실패 | 실제로 스캔했으나 못 찾음 → 보드 전원 / 배터리 |
| 연결 실패 | **OpenBCI GUI가 동글을 점유 중** — 압도적으로 흔한 원인 |
| 샘플 0개 | 보드 전원 / 배터리 / 전극 |
| 엉뚱한 보드 연결 | `BOARD_MAC` 미지정 상태에서 여러 보드가 켜져 있음 |
| 다음 실행이 안 됨 | 14단계 `release_session()` 누락 → 커널 재시작으로 해결 |
| 노트북 수정이 안 보임 | Jupyter 는 디스크 변경을 자동 반영하지 않음 → 탭 닫았다 다시 열기 |

> ⚠️ 외부에서 .ipynb 를 수정한 뒤 사용자가 브라우저에서 저장하면 그 수정이 덮어써진다.
> 파일을 고쳤으면 **반드시 "닫았다 다시 열라"고 안내할 것.**

### 환경 이슈 (해결됨)

**1) Microsoft Store 版 Python 3.13 에서 pip 실패**
`Cannot import 'setuptools.build_meta'` 로 설치 불가.
- 원인: 구버전 고정(`numpy==1.24.3` 등)이 3.13용 휠이 없어 소스 빌드를 시도
- 해결: 일반 패키지는 `>=` 로 완화. 필요시 `pip install --no-build-isolation -r requirements.txt`
- 단, **brainflow 만은 `==5.20.0` 으로 고정 유지** (위 참조)

**2) 구버전 brainflow 는 Python 3.13 에서 설치 불가**
5.12.1 이하는 `nptyping` 에 의존하고, `nptyping` 은 `np.compat`(numpy 2.x 에서 제거됨)을 쓴다.
numpy 1.x 는 Python 3.13 휠이 없어 우회도 불가.
→ **5.20.0 이 Python 3.13 + BLED112 조합에서 쓸 수 있는 하한선.**

**3) 콘솔 인코딩**
`µ` 기호가 Windows cp949 콘솔에서 `UnicodeEncodeError` 를 낸다.
노트북 1단계에서 `sys.stdout.reconfigure(encoding='utf-8')` 로 해결
(워크스페이스 `conventions.md` 규칙).

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
   (문법 검사는 통과하므로 눈치채기 어렵다. 파일 크기가 2배로 뛰는 것이 신호.)
7. **디스크 버전만 확인하고 "고쳤다"고 판단** — 커널에 로드된 DLL 이 그대로였다.
   `BoardShim.get_version()` 으로 실제 로드된 버전을 봐야 한다.
8. **`GANGLION_BOARD` deprecated 경고를 "경고일 뿐 동작은 정상"으로 해석** — 실제로는
   기능이 죽어 있었다. deprecated 표시는 실제 동작 여부와 별개이므로 **직접 돌려서 확인**할 것.

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
