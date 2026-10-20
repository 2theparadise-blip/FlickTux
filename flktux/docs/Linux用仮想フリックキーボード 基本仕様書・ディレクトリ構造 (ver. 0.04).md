# Linux用仮想フリックキーボード 基本仕様書（ver. 0.04）

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
- **ver. 0.04**：
  - **ルーン（Rune）ジェスチャー入力機構**（一筆書きの多段折れ線・図形軌跡によるコマンド実行・定型文入力・モード切替）を追加
  - **3本指タップ（Three-Finger Tap）によるキーボード起動・召喚（表示/非表示トグル）仕様** を追加
  - **ルーン描画によるキーボード起動（Summon by Rune）仕様**（待機中に特定の一筆書きルーンを描いた座標へキーボードを召喚）を追加

<!-- ... existing code ... -->

### 3.3 防護策3：マルチタッチ（2本指・3本指ジェスチャー）とRaw `evdev` バイパス
* **2本指タッチによる即座のトラックパッド化**：
  * 液タブやタッチ画面・トラックパッド上で **2本指（2スロット同時タッチ）** を検知してスライドした場合、文字入力をキャンセルして即座に「カーソル移動（トラックパッド）モード」または「変換候補スクロール」へ遷移する。
* **3本指タップによるキーボード起動・召喚（Three-Finger Tap Summon）**：
  * **3本指（3スロット同時タッチ）** が着地し、短時間（デフォルト `250ms` 以内）かつ微小移動距離（各指 `25px` 以内）で同時にリリースされた場合、**「3本指タップ（起動・表示トグル）」** として判定する。
  * キーボード非表示（バックグラウンド待機）時は、3本指の重心座標 $(x_c, y_c)$ に即座に仮想キーボードを召喚（表示）する。表示中は非表示（格納）へトグルする（設定により位置再移動のみに変更可能）。
* **Raw `evdev` ノンブロッキング・バイパスモード（オプション）**：
  * `/dev/input/event*` からスタイラス（`BTN_TOOL_PEN`）とマルチタッチ（`ABS_MT_SLOT`, `ABS_MT_POSITION_X/Y`, `ABS_MT_TOUCH_MAJOR`）を非排他（Read-Only）で並列監視し、X11ドライバの座標変換バグを完全にバイパスする。

---

## 3.4 ルーン（Rune）ジェスチャー入力およびルーン起動仕様（ver. 0.04 新規）

ペン・指タッチ・マウスによる「一筆書きの折れ線・図形ストローク（ルーン）」をリアルタイム解析し、通常の単一方向フリックと区別して高速にアクションを実行・起動する。

### (1) 単一フリックとルーン（多段ストローク）の自動判別アルゴリズム
* ストローク軌道をセグメント分割器（`RuneRecognizer`）で追跡し、最小セグメント長（デフォルト：`32.0px`）以上移動するごとに進行方向ベクトル（4方向または8方向）を確定する。
* **方向遷移（折れ曲がり）の抽出**：
  * 始点から終点まで方向変化がない（セグメント数が1）場合は、通常の **「単一フリック（Flick）」** として処理する。
  * ストローク途中で方向が切り替わり、**2セグメント以上の方向シーケンス（例：`Down -> Right` で「L字」、`Down -> Up` で「V字」、`Right -> Down -> Right` で「Z字 / 稲妻型」など）** が形成された場合は、**「ルーンジェスチャー（Rune）」** として判定する。

### (2) ルーンによるキーボード起動（Summon by Rune）
* キーボードが非表示（待機状態）のとき、画面（タッチパネル・液タブ）またはペンタブ・トラックパッド上で **「起動用ルーン（デフォルト：`Down -> Up` のV字ストローク、または `Down -> Right -> Down` の稲妻ストローク）」** を描くと、`SummonKeyboard` イベントが発火し、ルーンを描き始めた座標 $(x_0, y_0)$ に仮想キーボードが即座に出現する。

### (3) キーボード上のルーンジェスチャー入力（カスタム可能）
キーボード表示中にルーンを描いた場合、設定ファイル（JSON）で定義された以下のアクションを実行できる。
* **システム・編集操作**：`Undo`（例：`Left -> Down`）、`Redo`（例：`Right -> Down`）、`Copy`、`Paste`、`SelectAll`、行頭/行末移動
* **IME・テキスト操作**：全確定（`Enter`）、文節一括削除、定型文・メールアドレス等の直接バースト入力
* **キーボード制御**：入力プリセットの即時切替（Google ⇔ ガラケー等）、キーボードの格納（非表示化）

<!-- ... existing code ... -->

## 5. GitHubリポジトリ ディレクトリ構造（ver. 0.04 / Rust構成）

```text
linux-virtual-flick-keyboard/
├── Cargo.toml                        # Rustパッケージ・依存クレート定義 (ver. 0.04)
├── README.md                         # セットアップ手順（Linux Mint / uinput権限設定含む）
├── LICENSE
├── .gitignore
│
├── udev/
│   └── 99-vfk-input.rules            # /dev/uinput および /dev/input 権限設定用udevルール
│
├── docs/
│   ├── specification_v0.02.md        # 本仕様書 (ver. 0.04)
│   └── antigravity_tasks/            # Google Antigravity エージェント用タスク指示書
│       ├── task_01_stabilizer_and_flick.md
│       ├── task_02_keymap_and_modes.md
│       ├── task_03_uinput_romaji_burst.md
│       ├── task_04_numpad_evdev_hook.md
│       └── task_05_x11_nofocus_overlay.md
│
├── configs/
│   ├── settings.json                 # 全体設定（ペン＋タッチ調停、3本指起動、ルーン定義）
│   └── keymaps/
│       ├── presets/
│       │   ├── google_ja.json        # Google (Gboard) 形式
│       │   ├── galaxy_ja.json        # Galaxy 形式
│       │   ├── iphone_ja.json        # iPhone (iOS) 形式
│       │   ├── garakei_ja.json       # ガラケー（トグル）形式
│       │   └── tenkey_modern_ja.json # 10キー（現代型2タッチ/物理テンキー）形式
│       └── custom/
│           └── user_custom.json      # ユーザーカスタムキーマップ（カスタムルーン含む）
│
└── src/
    ├── main.rs                       # エントリーポイント・非同期ランタイムとGUIの統合
    ├── lib.rs                        # ライブラリルート（ペン＋タッチ・ルーン・3本指起動コア ver. 0.04）
    │
    ├── core/
    │   ├── mod.rs
    │   ├── events.rs                 # 内部イベント・入力ソース・ルーン/起動イベント定義
    │   ├── keymap.rs                 # JSONキーマップ＆ルーン定義スキーマ構造体 (serde)
    │   └── config.rs                 # アプリ設定ロード・ホットリロード管理
    │
    ├── input/
    │   ├── mod.rs
    │   ├── arbitrator.rs             # ペン＋タッチ調停・3本指タップ検知・2本指トラックパッド
    │   ├── stabilizer.rs             # Pen/Touchデュアルプロファイル・3段スタビライザ
    │   ├── rune_recognizer.rs        # ルーン（一筆書き多段ジェスチャー）認識エンジン
    │   ├── flick_calc.rs             # 4方向/8方向ベクトル角度計算
    │   └── numpad_evdev.rs           # 外付け10キー＆Rawタブレット evdev 非同期キャプチャ
    │
    ├── engine/
    │   ├── mod.rs
    │   ├── state_machine.rs          # 5方式統合ステートマシン（Flick/Toggle/2-Touch/Rune）
    │   └── kana_modifier.rs          # 濁点・半濁点・小文字の動的変換＆ローマ字展開テーブル
    │
    ├── output/
    │   ├── mod.rs
    │   └── fast_uinput.rs            # uinput ローマ字バースト送出・Backspace書き換えエンジン
    │
    └── ui/
        ├── mod.rs
        ├── x11_helper.rs             # Linux Mint (X11) 非フォーカス奪取・最前面固定制御
        ├── overlay_window.rs         # GTK4 オーバーレイ・ルーン軌跡エフェクト・フリックガイド
        └── keymap_editor.rs          # GUIカスタムキーマップ＆ルーン登録エディタ
```