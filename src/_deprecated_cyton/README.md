# ⚠️ 사용하지 않는 코드 (보관용)

이 폴더의 파일들은 **Ganglion 보드에서 동작하지 않습니다.** 참고용으로만 보관합니다.

## 왜 폐기되었나

| 파일 | 문제 |
| --- | --- |
| `open_bci_v3.py` | **Cyton 전용** 드라이버. Cyton의 시리얼 프로토콜(0xA0/0xC0, 33바이트 패킷)을 직접 파싱하는데, Ganglion은 BLE 기반이라 프로토콜이 완전히 다름 |
| `serial_main.py` | 위 드라이버를 사용 → Ganglion에서 동작 불가 |
| `bled112_openbci.py` | `bleak`(네이티브 BLE) 기반. BLED112는 네이티브 BLE가 아니라 동글 뒤의 가상 시리얼 포트이며, 해당 PC에는 내장 BLE 어댑터도 없음 |
| `main.py` | 위 BLE 드라이버를 사용 |
| `OpenBCI_Tutorial.ipynb` | 8채널 / 250Hz(Cyton 사양) 가정. Ganglion은 **4채널 / 200Hz** |
| `signal_processor.py` · `data_recorder.py` | 8채널 고정 가정, 위 드라이버들과 함께 동작하도록 작성됨 |

## 올바른 방법

**`../Ganglion_Tutorial.ipynb`** 를 사용하세요.

OpenBCI GUI v5도 내부적으로 쓰는 **BrainFlow** 라이브러리를 사용합니다.

```python
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

params = BrainFlowInputParams()
params.serial_port = 'COM3'   # BLED112 동글 포트 (필수)
params.mac_address = ''       # 특정 보드 지정 (선택, 비우면 자동탐색)

board = BoardShim(BoardIds.GANGLION_BOARD, params)
board.prepare_session()
```
