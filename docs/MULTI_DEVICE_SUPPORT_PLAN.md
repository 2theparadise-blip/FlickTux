# FlickTux マルチデバイス対応実装計画書
## 他社製液タブ・自作/Arduino10キー・Weylus(iPad/iPad mini) 包括的統合仕様

## 1. 概要と背景

FlickTux はこれまで主に Wacom 製ペンタブレット（Bamboo / Intuos / Cintiq）および標準的なテンキー入力を前提として設計されていましたが、ユーザーのハードウェア環境の多様化に伴い、以下の3大プラットフォームへの本格対応が求められています：

1. **他社製液タブ・ペンタブへの包括的対応**:
   - Wacom 固有の `xsetwacom` に依存せず、**XP-Pen、Huion、Gaomon、UGEE、Xencelabs、Parblo、VEIKK** などの主要サードパーティ製液タブ・板タブをドライバ不問（`libinput` / カーネル標準 `evdev`）で自動検知し、筆圧・感度・作業エリアを完全制御する。
2. **Arduino / 自作10キー・プッシュフォン型デバイスの検索・バインド**:
   - **Arduino (Leonardo/Pro Micro)**、**Raspberry Pi Pico (RP2040)**、**Teensy**、**QMK/VIA 自作テンキー**、プッシュホン改造ダイヤルパッドなど、自作USB HID / シリアルデバイスを自動検索（スキャン）し、画面上のプッシュボタンやテンキー入力にワンクリックで紐付ける。
   - 通常のPCキーボードと干渉しないよう、**排他キャプチャ（`EVIOCGRAB`）** にも対応する。
3. **Weylus による iPad / iPad mini 液タブ化への完全対応**:
   - iPad / iPad mini を Linux PC の液タブとして利用できる **Weylus**（仮想 uinput ドライバ）を自動検知。
   - **Apple Pencil** の超高精度な筆圧・傾き、**iPad 特有の 4:3 アスペクト比補正**、手のひら誤爆を防ぐ **パームリジェクション**、iPad mini の小型画面に適したスケーリング表示を提供する。

---

## 2. 他社製液タブ・ペンタブの包括的対応設計 (Multi-Vendor Tablet Support)

### 2.1 対象メーカーおよび対応ドライバマトリックス

| メーカー / ブランド | 代表的シリーズ | Linux カーネルドライバ | X11 / Wayland レイヤ | FlickTux 制御方式 |
|:---|:---|:---|:---|:---|
| **Wacom** | Cintiq, Intuos, Bamboo, One | `hid-wacom` | `xf86-input-wacom` / `libinput` | `xsetwacom` + `evdev` ハイブリッド |
| **XP-Pen** | Artist 12〜24 Pro, Deco, Star | `hid-uclogic` / DIGImend | `libinput` | **汎用 `evdev` + `xinput/libinput`** |
| **Huion** | Kamvas 12〜24 Pro, Inspiroy | `hid-uclogic` / DIGImend | `libinput` | **汎用 `evdev` + `xinput/libinput`** |
| **Gaomon** | PD1161, PD1560, PD2200, M10K | `hid-uclogic` / DIGImend | `libinput` | **汎用 `evdev` + `xinput/libinput`** |
| **Xencelabs** | Pen Tablet Medium/Small | `hid-xencelabs` (Linux 5.18+) | `libinput` | **汎用 `evdev` + `xinput/libinput`** |
| **UGEE / Parblo / VEIKK** | 各種エントリー〜プロ液タブ | `hid-uclogic` | `libinput` | **汎用 `evdev` + `xinput/libinput`** |
| **汎用小型液晶** | Waveshare, Goodix, RaspberryPi | `ft5406`, `goodix`, `ads7846` | `libinput` | **タッチスクリーン `evdev`** |

---

### 2.2 カーネル `evdev` 能力ベース自動検出エンジン (Capability-Based Sniffing)

特定のベンダー名に依存する文字列マッチングを廃止し、Linux カーネルが公開する `/dev/input/event*` の **デバイス能力（Capabilities）** を直接解析して判定します。

```text
               /dev/input/event* を走査
                         |
           +-------------+-------------+
           |                           |
    [EV_ABS 軸検査]             [EV_KEY キー検査]
    ・ABS_X / ABS_Y             ・BTN_TOOL_PEN (ペン先)
    ・ABS_PRESSURE (筆圧)       ・BTN_STYLUS / STYLUS2 (サイドボタン)
    ・ABS_TILT_X / TILT_Y       ・BTN_TOUCH (画面接触)
           |                           |
           +-------------+-------------+
                         |
           [デバイス分類 (DeviceKind)]
       ・Stylus (電磁誘導ペン / 液タブ・板タブ)
       ・Touch (指タッチ / トラックパッド)
       ・Hybrid (ペン & タッチ両対応)
       ・Touchscreen (組込液晶タッチパネル)
```

#### 検出ロジック (`src/input/evdev_listener.rs` 強化):
1. **ペンタブレット (Stylus)**:
   - `BTN_TOOL_PEN` を持つ、または `BTN_TOUCH` かつ `ABS_PRESSURE` を持つデバイス。
   - ベンダー文字列（`wacom`, `xp-pen`, `huion`, `gaomon`, `ug-tablet`, `xencelabs`, `veikk`, `parblo`, `hanvon`, `weylus` 等）を補助的に照合。
2. **タッチスクリーン (Touchscreen)**:
   - `ABS_MT_POSITION_X/Y` を持ち、`BTN_TOOL_PEN` を持たないデバイス。
3. **ベンダー名スキャン**:
   - `dev.name()` から製造元ブランドを自動タグ付けし、設定GUIに `[XP-Pen Artist 15.6 Pro]` のように分かりやすく表示。

---

### 2.3 ソフトウェア筆圧ノーマライズ & カスタム筆圧カーブ補正

他社製液タブの中には、Wacom のような高度な X11 筆圧カーブツール（`xsetwacom set stylus PressureCurve`）が存在しないものがあります。
FlickTux では、**Flick エンジン内部で数学的に筆圧を再計算（ソフトウェア筆圧キャリブレーション）** することで、どのメーカーの液タブでも均一かつ自在な書き味を提供します。

```text
[Raw evdev 筆圧値] ---> [0.0〜1.0 に正規化] ---> [ベジェ/ガンマ変換] ---> [フリック判定 & 描画]
(0 〜 pressure_max)     (p = raw / max)          (P_out = f(p))          (太さ・感度・確定)
```

#### 筆圧変換式:
$$P_{\text{out}} = \begin{cases}
0 & (p < \text{Threshold}) \\
\left( \frac{p - \text{Threshold}}{1.0 - \text{Threshold}} \right)^\gamma & (p \ge \text{Threshold})
\end{cases}$$
- **柔らかめ ($\gamma < 1.0$)**: 軽い筆圧で素早く最大入力（手首が疲れにくい）
- **標準・リニア ($\gamma = 1.0$)**: 力加減に完全比例
- **硬め ($\gamma > 1.0$)**: しっかり押し込まないと強く反応しない（誤タップ防止）

---

### 2.4 X11 / Wayland でのエリアマッピング & 16:9 比率維持

液タブとメインモニターの解像度差（マルチディスプレイ環境）において、液タブ画面だけにポインタを限定（マッピング）する汎用機構を実装します。

- **X11 汎用制御 (`xinput`)**:
  ```bash
  # デバイス名から ID を取得して特定のディスプレイ出力 (例: HDMI-1) にバインド
  xinput map-to-output <DeviceID> HDMI-1
  
  # アスペクト比維持の座標変換マトリックス (Coordinate Transformation Matrix) 計算
  xinput set-prop <DeviceID> --type=float "Coordinate Transformation Matrix" c0 0 c1 0 c2 c3 0 0 1
  ```
- **Wacom デバイス接続時**: 既存の `xsetwacom` コマンドを最優先利用（下位互換性の完全担保）。

---

## 3. Arduino / 自作10キー・プッシュフォン型デバイスの検索・バインド

### 3.1 対象マイコン & ファームウェア仕様

自作キーボードや改造電話機で使われる以下のハードウェアを即座に利用可能にします：

| コントローラ / デバイス | 通信方式 | USB VID:PID 例 | 代表的ファームウェア |
|:---|:---|:---|:---|
| **ATmega32U4** (Leonardo / Pro Micro) | USB HID Keyboard | `2341:8036`, `1b4f:9205` | Arduino Keyboard.h, QMK |
| **Raspberry Pi Pico** (RP2040) | USB HID / CDC-ACM | `2e8a:0005`, `2e8a:000a` | CircuitPython, TinyUSB, QMK |
| **Teensy** (2.0 / 3.x / 4.x) | USB HID | `16c0:0482`, `16c0:0483` | PJRC Teensyduino |
| **ESP32-S2 / ESP32-S3** | USB HID | `303a:1001` | ESP-IDF, Arduino-ESP32 |
| **QMK / VIA / VIAL 対応テンキー** | USB HID | `feed:xxxx`, `4653:xxxx` | QMK Firmware |
| **シリアル型プッシュホン基板** | USB Serial (CDC) | `/dev/ttyACM*`, `/dev/ttyUSB*` | シリアル文字列通信 (`DTMF:1`) |

---

### 3.2 自作デバイス自動検索エンジン (`Device Scanner`)

システムに接続されている USB 入力デバイスをディープスキャンし、自作10キーやプッシュフォン型デバイスを自動検出します。

```text
+-----------------------------------------------------------------+
|                    FlickTux デバイススキャナー                   |
+-----------------------------------------------------------------+
| 1. /dev/input/by-id/* を列挙                                    |
| 2. /sys/class/input/event*/device/id/{vendor,product,name} を取得|
| 3. キーボード能力 (EV_KEY) をスキャン:                          |
|    - テンキーキー (KEY_KP0〜KP9, KEY_KPENTER, KEY_KPASTERISK等) |
|    - 数字キー (KEY_0〜KEY_9)                                    |
| 4. マイコン固有の VID (Arduino, Raspberry Pi, Teensy) を照合    |
+-----------------------------------------------------------------+
```

#### 検出結果の分類表示（GUI・Webエディタ）:
```text
[🔍 デバイス検索結果一覧]
----------------------------------------------------------------------
● [推奨] Arduino SA Leonardo (/dev/input/by-id/usb-Arduino...-event-kbd)
   種別: USB HID 10-KeyPad (VID: 2341, PID: 8036)
   状態: テンキーキー (0-9, *, #, Enter) を検知
   [このデバイスをバインド] [テスト入力]

● [推奨] Raspberry Pi Pico Keypad (/dev/input/by-id/usb-Raspberry...-kbd)
   種別: QMK / DIY Numpad (VID: 2e8a, PID: 0005)
   [このデバイスをバインド] [テスト入力]

○ 標準 USB Keyboard (/dev/input/by-id/usb-Logitech...-event-kbd)
   種別: フルサイズPCキーボード
----------------------------------------------------------------------
```

---

### 3.3 排他キャプチャ (`EVIOCGRAB`) による通常キーボードとの完全共存

- **課題**: 通常の PC キーボード（フルサイズキーボードのテンキー部）と自作プッシュフォン型テンキーを両方接続している場合、X11 全体でテンキーをフックすると、通常の PC 作業でのテンキー入力まで横取りされてしまう。
- **解決策**:
  - 自作デバイス専用の `/dev/input/eventX` ノードを直接オープンし、Linux カーネルの `ioctl(fd, EVIOCGRAB, 1)`（排他アクセス要求）を発行。
  - これにより、**自作テンキー・プッシュフォンからの入力だけを FlickTux が独占受信**し、通常の PC キーボードは一切影響を受けずにデスクトップ上で利用可能となる。

---

### 3.4 シリアル型（CDC-ACM）プッシュホン受話器フック連動

Arduino 等のシリアル通信型プッシュホンにおいて、ボーレート（既定: 115200 bps）でシリアルポート（`/dev/ttyACM0` 等）を監視：
- `HOOK:OFF` 受信 $\rightarrow$ 受話器 Off-hook（音声AIチャット起動、UIに `[📞]` 点灯）
- `HOOK:ON` 受信 $\rightarrow$ 受話器 On-hook（音声AI切断、UI `[📞]` 消灯）
- `KEY:1` 〜 `KEY:#` 受信 $\rightarrow$ プッシュ電話配列（12キー）の対応キーをトグル/フリック入力

---

## 4. Weylus による iPad / iPad mini 液タブ化への完全対応

### 4.1 Weylus の動作アーキテクチャと仮想 uinput

```text
+-----------------------+              Wi-Fi / USB              +------------------------+
|   iPad / iPad mini    |  WebSocket (座標/筆圧/傾き/タッチ)     |       Linux PC         |
|  (Safari / Chrome)    | ------------------------------------> |     Weylus Server      |
|  ・Apple Pencil       |                                       | (Port 1701 / uinput)   |
|  ・Multi-Touch        |                                       +-----------+------------+
+-----------------------+                                                   |
                                                                            v
                                                       +--------------------------------+
                                                       |   Linux Kernel /dev/uinput     |
                                                       |   ・"Weylus Stylus" (Pen)      |
                                                       |   ・"Weylus Touch" (MultiTouch)|
                                                       +----------------+---------------+
                                                                        |
                                                                        v
                                                       +--------------------------------+
                                                       |     FlickTux コアリスナー      |
                                                       |     (自動検知・パームリジェクション)|
                                                       +--------------------------------+
```

---

### 4.2 iPad / iPad mini 特有の 4:3 アスペクト比補正と画面スケーリング

1. **アスペクト比補正 (4:3 vs 16:9)**:
   - iPad のディスプレイは伝統的な **4:3（または約 1.43:1）** です。PC側の 16:9 画面をそのままミラーリングすると、円を描いたつもりが横長の楕円に歪んでしまいます。
   - FlickTux に **「📱 iPad (4:3 アスペクト比維持)」** モードを搭載。座標変換時にピラーボックス（左右余白）またはレターボックスを自動計算し、**正円が常に正円として入力される** 幾何補正を適用します。
2. **iPad mini (8.3" / 7.9") 小型画面向けスケーリング**:
   - iPad mini のようなコンパクトなタブレット画面上でもフリック入力しやすいよう、UI スケーリング（1.0x / 1.25x / 1.5x / 1.8x）をワンクリックで切り替え可能にします。

---

### 4.3 Apple Pencil 最適化 & パームリジェクション (手のひら誤爆防止)

1. **Apple Pencil 高解像度筆圧追従**:
   - Apple Pencil の極めて滑らかな筆圧変化に対応するため、指数平滑化（Exponential Moving Average: EMA）フィルタを適用し、ジッター（微小な手の震え）を除去しつつ遅延ゼロで追従。
2. **完全パームリジェクション**:
   - iPad に手首や手のひらを乗せて Apple Pencil で文字を書く際、`Weylus Touch` から大量の指接触イベントが同時発生します。
   - FlickTux は **`Weylus Stylus` がホバー（近接）または接触している間、`Weylus Touch` からのイベントを 100% 破棄** します。
   - ペン先が離れた時のみ、2本指スクロールやピンチ操作を受け付けます。

---

### 4.4 Weylus サービス連携UI

FlickTux の設定画面に「📱 iPad / iPad mini (Weylus)」連携カードを配置：
- Weylus サーバプロセスの常駐確認（ポート 1701 またはプロセス `weylus`）
- 接続用ローカル IP アドレスと QR コードの自動生成表示（iPad のカメラで読み取るだけで接続画面が開く）
- 仮想デバイス `"Weylus Stylus"` の接続状態インジケーター（🟢 接続中 / ⚪ 未接続）

---

## 5. UI / 設定画面（GUI & Webエディタ）の改修設計

### 5.1 設定ダイアログ (`SettingsDialog`) のタブ構成拡張

既存の `flktux/settings_gui.py` をリファクタリングし、以下の3タブ構成に拡張します：

```text
+-------------------------------------------------------------------+
|                  ⚙ FlickTux デバイス＆環境設定                    |
+-------------------------------------------------------------------+
| [ 🖊️ ペンタブ・液タブ ]  [ 🔌 外部10キー・自作機 ]  [ 📱 iPad / Weylus ] |
+-------------------------------------------------------------------+
|  (タブ1: ペンタブ・液タブ)                                        |
|  ・検出デバイス: [ XP-Pen Artist 15.6 Pro ▼ ] (Wacom/他社自動認識) |
|  ・筆圧カーブスライダー: [----●---------] (柔らかめ 〜 硬め)      |
|  ・アスペクト比維持 (16:9 正円): [✔] 有効                         |
|  ・手ブレ補正 (スムージング): [------●---] 4                      |
|  ・リアルタイム試し書き広場 (Canvas)                              |
+-------------------------------------------------------------------+
|  (タブ2: 外部10キー・自作機)                                      |
|  ・接続機器スキャン: [ 🔍 デバイスを検索 ]                         |
|  ・ターゲットデバイス: [ Arduino SA Leonardo (usb-001) ▼ ]        |
|  ・排他モード (EVIOCGRAB): [✔] 他アプリへの入力干渉を防止         |
|  ・リアルタイム入力テスト:                                        |
|     [ 1 ] [ 2 ] [ 3 ]  <- キーを押すと画面上で緑色に点灯          |
|     [ 4 ] [ 5 ] [ 6 ]                                             |
|     [ 7 ] [ 8 ] [ 9 ]                                             |
|     [ * ] [ 0 ] [ # ]                                             |
+-------------------------------------------------------------------+
|  (タブ3: iPad / iPad mini / Weylus)                               |
|  ・Weylus 接続状態: 🟢 稼働中 (http://192.168.2.6:1701)           |
|  ・機種プロファイル: (o) iPad (10.2"/10.9")  ( ) iPad mini (8.3") |
|  ・4:3 アスペクト比補正: [✔] 有効                                 |
|  ・Apple Pencil パームリジェクション: [✔] 有効                    |
|  ・UI 表示倍率: [ 1.25x ▼ ]                                       |
+-------------------------------------------------------------------+
|                                                 [ 保存 ] [ 閉じる ] |
+-------------------------------------------------------------------+
```

---

### 5.2 設定スキーマ (`~/.config/flktux/config.json`)

```json
{
  "tablet": {
    "device_name": "auto",
    "vendor": "xp-pen",
    "pressure_curve_level": 3,
    "threshold": 12,
    "smoothing": 4,
    "aspect_ratio_correction": true
  },
  "numpad_device": {
    "enabled": true,
    "device_path": "/dev/input/by-id/usb-Arduino_LLC_Arduino_Leonardo-event-kbd",
    "exclusive_grab": true,
    "mapping_preset": "push_phone"
  },
  "weylus": {
    "enabled": true,
    "target_device": "Weylus Stylus",
    "model": "ipad_mini",
    "aspect_ratio_4_3": true,
    "palm_rejection": true,
    "ui_scale": 1.25
  }
}
```

---

## 6. 実装フェーズとタスク一覧

| フェーズ | モジュール | 実装内容 | ステータス |
|:---|:---|:---|:---:|
| **Phase A: 他社製液タブ対応** | `src/input/evdev_listener.rs`<br>`flktux/wacom.py` | ・能力ベース検出 (`ABS_PRESSURE`, `BTN_TOOL_PEN`)<br>・XP-Pen/Huion/Gaomon/Xencelabs タグ認識<br>・ソフトウェア筆圧ノーマライズ＆カーブ補正 | **設計完了** |
| **Phase B: 自作10キー検索エンジン** | `src/input/device_scanner.rs`<br>`flktux/device_scanner.py` | ・`/dev/input/by-id/*` および VID/PID 走査エンジン<br>・Arduino/RP2040/Teensy 自動認識<br>・`EVIOCGRAB` 排他キャプチャ実装 | **設計完了** |
| **Phase C: Weylus / iPad 最適化** | `src/input/evdev_listener.rs`<br>`flktux/weylus.py` | ・`Weylus Stylus` / `Touch` 仮想デバイス認識<br>・4:3 アスペクト比正円補正<br>・Apple Pencil パームリジェクション | **設計完了** |
| **Phase D: 設定 GUI 統合** | `flktux/settings_gui.py`<br>`web/index.html` | ・設定画面の3タブ化（ペンタブ・自作機・iPad）<br>・リアルタイムキー入力テストモニター<br>・Weylus 接続状態＆QRコード表示 | **設計完了** |
| **Phase E: 実機テスト & 配備** | Linux Mint 実機 (`192.168.2.6`) | ・各種 evdev 入力テスト、排他 grab 検証<br>・GitHub コミット & プッシュ | **計画済** |

---

## 7. 実機検証チェックリスト（Linux Mint `192.168.2.6`）

- [ ] `flktux-devscan` または設定画面のデバイス検索で、接続された USB 10キー / Arduino が一覧表示されること
- [ ] 自作 10キーデバイスをバインドした状態でキーを押すと、画面上のプッシュボタン（1〜9, 0, *, #）が反応すること
- [ ] 排他モード（`EVIOCGRAB`）有効時、自作テンキーの入力が他のテキストエディタに漏れず FlickTux のみに渡ること
- [ ] XP-Pen / Huion 等の液タブまたはペンタブを接続した際、筆圧（線の太さ変化）が正常に認識されること
- [ ] Weylus を起動して iPad / iPad mini から接続した際、Apple Pencil でのフリック入力が追従すること
- [ ] iPad の手首接触（パーム）でキーが誤爆しないこと（パームリジェクション機能）
- [ ] 4:3 比率の iPad 上で描いた円が楕円に歪まないこと（アスペクト比維持補正）
