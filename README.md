# ZiriZiriDTP (ジリジリDTP) 🖨️

ポータブルサーマルプリンタ「SWS-PT1」を Linux (Bluetooth / BLE) 経由で制御し、スマートフォンやPCのWebブラウザから直感的にレシート風メモや写真をデザイン・印刷できるWebアプリケーションです。

---

## 📸 スクリーンショット / 主な機能

- **TODO・買い物メモ印刷**: チェックボックス付きレシート、完了取り消し線、**アイテム別QRコード添付**（Web URL、Google Maps店舗検索、テキストメモ）
- **ドライブルート・旅程しおり印刷**: Google Mapsナビ起動・地点検索QRコード付きの旅程シート。ステップ番号（`[01]`）、経由地連結アロー（`↓`）、移動手段モード（車、自転車、徒歩、公共交通）に対応
- **フリーテキストメモ**: 文字サイズ（小〜特大）、配置（左/中央/右）、太字対応
- **写真・画像印刷**: Floyd-Steinberg（誤差拡散）ディザリングによる滑らかな網点階調表現、コントラスト調整
- **診断テストチャート**: フォントサイズラダー、0%〜100%濃度グラデーション、ピクセル解像度ルーラー
- **リアルタイム・感熱紙プレビュー**: 編集内容がそのままモノクロ感熱紙イメージで即座に反映
- **入力内容の自動保存 (LocalStorage)**: 入力したTODO、メモ、ルート設定をブラウザ内に自動保持。安心の元に戻す（アンドゥ）付き一括クリアボタン
- **プリンタ状態表示**: バッテリー残量（%）のグラフィカル表示、タップでの手動ステータス更新
- **印刷日時設定**: ヘッダーまたはフッターへの印字、ON/OFF切り替え
- **キリトリ線**: ハサミでまっすぐカットできる `✂ ----- キリトリ ----- ✂` の印字＆ON/OFF
- **印刷詳細設定**: 印字濃度（Darkness 1〜7、サーマルヘッド保護・省電力のためデフォルトを 1 に最適化）、余白送り量（feed 20〜80px）の調整

---

## 🛠️ 技術スタック

### バックエンド
- **Python 3.12+ / 3.13**
- **FastAPI** + **Uvicorn**: 非同期RESTful APIサーバー & 静的SPA配信
- **Bleak**: Linux BlueZ スタックを介した非同期 Bluetooth Low Energy (BLE) 通信
- **Pillow (PIL)**: 画像レンダリング、二値化、Floyd-Steinbergディザリング、ラスタライズ
- **Pydantic**: リクエストデータのバリデーション

### フロントエンド
- **HTML5 / CSS3 / Vanilla JavaScript**: フレームワーク不要の超軽量・高速SPA
- モバイルファーストのレスポンシブデザイン（ダークモード、感熱紙プレビューギミック）

### 通信プロトコル仕様 (Funny Print系列)
- **BLE Service**: `0000ffe6-0000-1000-8000-00805f9b34fb`
  - 送信 (Write without response): `0000ffe1-0000-1000-8000-00805f9b34fb`
  - 受信 (Notify): `0000ffe2-0000-1000-8000-00805f9b34fb`
- **独自認証ハンドシェイク**:
  接続直後に `5a 01` (ハードウェア情報取得) → プリンタからのChallenge (`5a 0a`) に対し、MACアドレスとCRC16 XMODEMから算出したResponse (`5a 0b`) を返答して印刷ロックを解除。
- **データパケット & フロー制御**:
  1パケットあたり2ライン分（96バイト = 48B × 2ライン）。プリンタからの通知パケット（`5a 05` 再送要求、`5a 08` バッファ満杯一時停止、`5a 06` 印刷完了）を監視するステートマシンによる安定したフロー制御を実装。

> 📖 **プロトコルの詳細・シーケンス図・リバースエンジニアリング記録**:  
> ESC/POSやCat-Printerとの違い、CRC16認証レスポンスの計算アルゴリズム、バッファ満杯時の巻き戻し再送ステートマシン図、全体データフロー図などは [docs/technical_notes.md](docs/technical_notes.md) に詳細を解説しています。ぜひご参照ください。

---

## 💻 開発・動作確認環境 (ハードウェア情報)

### 対象プリンタ実機
- **機種名**: SWS-PT1 (DOLEWA / Shenzhen Xiqi 系ポータブルサーマルプリンタ、スマートフォンアプリ「Funny Print」対応機種)
- **用紙規格**: 58mm幅 感熱ロール紙
- **印字仕様**: 印字有効幅 48mm / 384ドット (203 DPI)
- **ファームウェア**: `1.0.06`
- **BLE MACアドレス**: `AA:BB:CC:DE:04:EF` (実機固有アドレス)

### 開発ホストマシン
- **OS**: Arch Linux (Kernel 7.2.x, x86_64)
- **Bluetoothスタック**: BlueZ 5.x / 内蔵 Bluetooth 5.x コントローラー
- **日本語フォント**: Noto Sans CJK JP (`/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc`)

---

## 🚀 実行環境の構築 & セットアップ手順

別マシン（Ubuntu, Debian, Arch Linux, Raspberry Pi 等）に移行する場合も、以下の手順で完全に再現できます。

### 1. システム依存パッケージのインストール (Linux)

Bluetoothスタック（BlueZ）および日本語フォントが必要です。

#### Arch Linux の場合:
```bash
sudo pacman -S bluez bluez-utils noto-fonts noto-fonts-cjk python uv
sudo systemctl enable --now bluetooth
```

#### Ubuntu / Debian / Raspberry Pi OS の場合:
```bash
sudo apt update
sudo apt install -y bluez fonts-noto-cjk python3-venv python3-pip
sudo systemctl enable --now bluetooth
```

### 2. リポジトリのクローン & 設定確認

```bash
git clone https://github.com/your-username/ZiriZiriDTP.git
cd ZiriZiriDTP
```

お使いの SWS-PT1 の MAC アドレスに合わせて、`ziriziri/config.py` 内の `PRINTER_MAC` または環境変数を設定してください。
```python
# ziriziri/config.py
PRINTER_MAC = os.getenv("PRINTER_MAC", "AA:BB:CC:DE:04:EF")
```

※ 周囲のプリンタをスキャンしてアドレスを調べる場合:
```bash
bluetoothctl scan on
# 「SWS-PT1」や「GB01」「FunnyPrint」と表示されるデバイスのMACアドレスを確認
```

### 3. Python 仮想環境の構築 & 依存ライブラリの導入

`uv` を使用する場合（推奨・高速）:
```bash
uv venv
uv pip install -r requirements.txt
```

標準の `venv` / `pip` を使用する場合:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🏃 実行方法

### サーバーの起動

```bash
# 仮想環境のPythonでサーバー起動 (0.0.0.0:8080 でリッスン)
.venv/bin/python run_server.py
```

### Web UI へのアクセス

- **同じWi-Fiネットワーク上のスマホから**:
  ホストマシンのローカルIPアドレス（例: `http://192.168.11.39:8080`）にブラウザでアクセスします。
- **ホストPC自身から**:
  `http://localhost:8080` にアクセスします。

※ ポート番号を変更したい場合は、`run_server.py` 内の `port=8080` を書き換えてください。

---

## 🔌 Web API エンドポイント

FastAPI による REST API を提供しており、ブラウザUI以外のスクリプトや外部システムからも印刷を実行できます。

| メソッド | エンドポイント | 説明 |
| :--- | :--- | :--- |
| `GET` | `/api/status` | プリンタのBLE接続状態・バッテリー残量（%）の取得 |
| `POST` | `/api/preview/todo` | TODO / 買い物メモのリアルタイムプレビュー画像（Base64 PNG）生成 |
| `POST` | `/api/print/todo` | TODO / 買い物メモの印刷実行（QRコード添付対応） |
| `POST` | `/api/preview/route` | ドライブルート / 旅程しおりのリアルタイムプレビュー画像生成 |
| `POST` | `/api/print/route` | ドライブルート / 旅程しおりの印刷実行（Google Maps QR連動） |
| `POST` | `/api/preview/text` | フリーテキストメモのプレビュー画像生成 |
| `POST` | `/api/print/text` | フリーテキストメモの印刷実行 |
| `POST` | `/api/preview/image` | 写真・画像のディザリングプレビュー画像生成 |
| `POST` | `/api/print/image` | 写真・画像のディザリング印刷実行 |
| `POST` | `/api/preview/test` | 診断テストチャートのプレビュー画像生成 |
| `POST` | `/api/print/test` | 診断テストチャートの印刷実行 |

---

## 📂 ディレクトリ構成

```text
ZiriZiriDTP/
├── docs/                  # 技術仕様書 & リバースエンジニアリング記録
│   └── technical_notes.md # プロトコル詳細、認証ハンドシェイク、フロー制御図
├── ziriziri/              # バックエンドコアパッケージ
│   ├── config.py          # 定数、フォントパス、MACアドレス、UUID等
│   ├── protocol.py        # Funny Print CRC16認証、パケット生成
│   ├── driver.py          # BleakClient BLE通信、フロー制御ステートマシン
│   ├── renderer.py        # PIL画像レンダリング、ディザリング、キリトリ線
│   └── server.py          # FastAPI エンドポイント & ルーティング
├── static/                # フロントエンド静的ファイル
│   ├── index.html         # モバイル特化型 SPA HTML
│   ├── css/style.css      # スタイリング (レシート風UI、ダークテーマ)
│   └── js/app.js          # クライアント側ロジック & API通信
├── run_server.py          # サーバー起動エントリーポイント
├── requirements.txt       # Python依存パッケージ一覧
├── PLAN.md                # 開発記録・プロトコル解析ログ
├── README.md              # 本ドキュメント
└── AGENTS.md              # AIアシスタント向け行動規範・コミット規約
```

---

## 💡 便利な運用のヒント

### Linux 起動時に自動起動させる (systemd サービス化)
常時起動のプリントサーバー（Raspberry Pi など）にする場合、systemd ユニットファイルを作成すると便利です。

`/etc/systemd/system/ziriziri.service`:
```ini
[Unit]
Description=ZiriZiriDTP Thermal Printer Server
After=bluetooth.target network.target

[Service]
Type=simple
User=minamo
WorkingDirectory=/home/minamo/repository/ZiriZiriDTP
ExecStart=/home/minamo/repository/ZiriZiriDTP/.venv/bin/python run_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ziriziri
```

---

## 📄 ライセンス
MIT License
