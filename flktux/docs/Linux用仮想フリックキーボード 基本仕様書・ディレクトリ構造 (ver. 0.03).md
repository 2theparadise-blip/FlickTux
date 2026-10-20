# Linux用仮想フリックキーボード 基本仕様書（ver. 0.03）

## 改訂履歴
- **ver. 0.01**：初期仕様策定（Pythonベース暫定構成）
- **ver. 0.02**：
  - 開発言語を **Rust** に変更
  - 初期ターゲット環境を **Linux Mint（Cinnamon / MATE / Xfce：X11環境）** に最適化（将来のUbuntu / Wayland拡張性を維持）
  - 日本語変換連携を最速の **カーネル `uinput` ローマ字バースト送出方式（＋D-Bus直接送出ハイブリッド）** に決定
  - **ペンタブ・液タブのドライバ不安定対策（非依存フィルタリング＆Raw evdevバイパス機構）** を新規設計
- **ver. 0.03**：
  - **ペンタブ・液タブの「ペン＋タッチ（Pen & Touch）形式」への対応仕様** を追加
  - ペン操作中の手のひら誤接触を遮断する **アプリ内パームリジェクション（Pen Proximity / Cooldown Lock）** を追加
  - X11コアポインタ上でペン座標とタッチ座標が混線した際に主ストロークのみを分離追跡する **空間クラスタロック（Spatial Cluster Locking）** を追加
  - ペン入力と指タッチ入力の物理特性差に応じた **デュアルスタビライザ・プロファイル** と **マルチタッチ（2本指トラックパッド化）制御** を追加

<!-- ... existing code ... -->

## 3. ペンタブ・液タブ（ペン＋タッチ形式）のドライバ不安定対策仕様（重要）

Linux環境において、Wacom (`xf86-input-wacom`)、XP-Pen / Huion 等のベンダードライバ、あるいはOpenTabletDriverで「ペン＋タッチ対応モデル」を使用する際、以下の深刻な不安定事象が多発する。
* **ペンとタッチの座標綱引き（Cursor Ping-Pong）**：ペンで操作中に手のひらや指が画面・パッドに触れると、X11のポインタが「ペン先座標」と「手のひら座標」の間をミリ秒単位で往復し、巨大ベクトルの誤フリックが暴発する。
* **ドライバ側のパームリジェクション不全**：Linuxドライバの設定やX11マッピング不整合により、ペン着地中にタッチが自動無効化されないケースがある。
* **ペンと指タッチの物理特性の違い**：
  * **ペン（Stylus）**：着地時の微細なチャタリングや、離脱時のペン先傾きによる「逆跳ね（30〜35ms）」が顕著に発生する。
  * **タッチ（Finger）**：チャタリングは少ないが接触面積が広く、指を離す瞬間の「ロールオフ（10〜15msの転がり）」が発生する。また、2本指でのスワイプ操作や手のひらの大面積接触（パームタッチ）が入る。

これらを根本的に解決するため、本アプリでは **「ペン・タッチ調停＆空間クラスタ分離エンジン（`PenAndTouchArbitrator`）」** を備えた3段階の防護アーキテクチャを採用する。

### 3.1 防護策1：ペン・タッチ調停とアプリ内パームリジェクション（`PenAndTouchArbitrator`）
ドライバのパームリジェクション機能に依存せず、アプリ独自の調停器でペンとタッチを完全に制御する。
1. **ペン優先ロック＆クールダウン（Pen Priority & Cooldown Lockout）**：
   * ペンがホバー検知圏内（`pen_in_proximity == true`）にある間、ペンでストロークしている最中、およびペンが画面から離れた直後の **`150ms`（クールダウン期間）** は、`Touch` ソースからの入力をすべてパーム（手のひら誤接触）として遮断する。
2. **タッチ接触面積フィルタ（Palm Contact Area Rejection）**：
   * タッチ入力において、接触面積（`contact_major_px`）が閾値（デフォルト：`45.0px`）を超えるサンプルは、手のひらや側面接触とみなして即座に破棄する。
3. **混線ポインタの空間クラスタロック（Spatial Cluster Locking）**：
   * ドライバの仕様でペンとタッチが単一のX11マウスイベント（コアポインタ）に強制合成されてしまった場合でも、最初のPress着地点 $(x_0, y_0)$ を中心とする空間クラスタ（半径 `cluster_lock_radius_px`：デフォルト `140px`）を形成する。
   * ストローク途中に、離れた別地点（手のひら位置など）へ不連続にジャンプするサンプルが混入しても、主クラスタから外れた座標を「混線した別タッチのノイズ」として自動分離・破棄し、本来のペン（または第1指）の軌道だけを正確に追跡する。

### 3.2 防護策2：ペン／タッチ別デュアル・スタビライザプロファイル
入力ソースが `Pen` か `Touch` かに応じて、スタビライザの内部パラメータを動的に切り替える。

| パラメータ | ペン用プロファイル (`Pen`) | タッチ用プロファイル (`Touch`) | 目的・理由 |
| :--- | :---: | :---: | :--- |
| **チャタリング結合 (`contact_debounce_ms`)** | `25 ms` | `10 ms` | ペン先の微細なバウンスを強力に結合し、指の高速連打は阻害しない |
| **リリース跳ね切り捨て (`release_lookback_ms`)** | `35 ms` | `12 ms` | ペン離脱時の大きな傾き跳ねを除去し、指タッチのロールオフを軽微に補正 |
| **最大許容速度 (`max_velocity_px_per_ms`)** | `120.0 px/ms` | `160.0 px/ms` | ドライバのスパイク飛びを除去しつつ、素早い指スワイプに追従 |
| **最小フリック閾値 (`flick_threshold_px`)** | `24.0 px` | `28.0 px` | 指先の着地ブレでタップがフリックに化けるのを防止 |

### 3.3 防護策3：マルチタッチ（2本指ジェスチャー）とRaw `evdev` バイパス
* **2本指タッチによる即座のトラックパッド化**：
  * 液タブやタッチ画面・トラックパッド上で **2本指（2スロット同時タッチ）** を検知した場合、文字入力をキャンセルして即座に「カーソル移動（トラックパッド）モード」または「変換候補スクロール」へ遷移する。
* **Raw `evdev` ノンブロッキング・バイパスモード（オプション）**：
  * `/dev/input/event*` からスタイラス（`BTN_TOOL_PEN`）とマルチタッチ（`ABS_MT_SLOT`, `ABS_MT_POSITION_X/Y`, `ABS_MT_TOUCH_MAJOR`）を非排他（Read-Only）で並列監視し、X11ドライバの座標変換バグを完全にバイパスする。

<!-- ... existing code ... -->

## 5. GitHubリポジトリ ディレクトリ構造（ver. 0.03 / Rust構成）

```text
linux-virtual-flick-keyboard/
├── Cargo.toml                        # Rustパッケージ・依存クレート定義 (ver. 0.03)
├── README.md                         # セットアップ手順（Linux Mint / uinput権限設定含む）
├── LICENSE
├── .gitignore
│
├── udev/
│   └── 99-vfk-input.rules            # /dev/uinput および /dev/input 権限設定用udevルール
│
├── docs/
│   ├── specification_v0.02.md        # 本仕様書 (ver. 0.03)
│   └── antigravity_tasks/            # Google Antigravity エージェント用タスク指示書
│       ├── task_01_stabilizer_and_flick.md
│       ├── task_02_keymap_and_modes.md
│       ├── task_03_uinput_romaji_burst.md
│       ├── task_04_numpad_evdev_hook.md
│       └── task_05_x11_nofocus_overlay.md
│
├── configs/
│   ├── settings.json                 # 全体設定（ペン＋タッチ調停閾値、対象デバイス、テーマ）
│   └── keymaps/
│       ├── presets/
│       │   ├── google_ja.json        # Google (Gboard) 形式
│       │   ├── galaxy_ja.json        # Galaxy 形式
│       │   ├── iphone_ja.json        # iPhone (iOS) 形式
│       │   ├── garakei_ja.json       # ガラケー（トグル）形式
│       │   └── tenkey_modern_ja.json # 10キー（現代型2タッチ/物理テンキー）形式
│       └── custom/
│           └── user_custom.json      # ユーザーカスタムキーマップ
│
└── src/
    ├── main.rs                       # エントリーポイント・非同期ランタイムとGUIの統合
    ├── lib.rs                        # ライブラリルート（ペン＋タッチ安定化・コア実装 ver. 0.03）
    │
    ├── core/
    │   ├── mod.rs
    │   ├── events.rs                 # 内部イベント・入力ソース(Pen/Touch/Mouse)・方向定義
    │   ├── keymap.rs                 # JSONキーマップスキーマ構造体 (serde)
    │   └── config.rs                 # アプリ設定ロード・ホットリロード管理
    │
    ├── input/
    │   ├── mod.rs
    │   ├── arbitrator.rs             # ペン＋タッチ調停・パームリジェクション・クラスタ分離
    │   ├── stabilizer.rs             # Pen/Touchデュアルプロファイル・3段スタビライザ
    │   ├── flick_calc.rs             # 4方向/8方向ベクトル角度計算・2本指トラックパッド算出
    │   └── numpad_evdev.rs           # 外付け10キー＆Rawタブレット evdev 非同期キャプチャ
    │
    ├── engine/
    │   ├── mod.rs
    │   ├── state_machine.rs          # 5方式統合ステートマシン（Flick/Toggle/2-Touch/Trackpad）
    │   └── kana_modifier.rs          # 濁点・半濁点・小文字の動的変換＆ローマ字展開テーブル
    │
    ├── output/
    │   ├── mod.rs
    │   └── fast_uinput.rs            # uinput ローマ字バースト送出・Backspace書き換えエンジン
    │
    └── ui/
        ├── mod.rs
        ├── x11_helper.rs             # Linux Mint (X11) 非フォーカス奪取・最前面固定制御
        ├── overlay_window.rs         # GTK4 オーバーレイウィンドウ＆フリックガイドポップアップ
        └── keymap_editor.rs          # GUIカスタムキーマップ編集画面
```