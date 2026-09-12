# AGENTS.md

本リポジトリで作業するすべての AI コーディングアシスタント（Antigravity 等）が遵守すべき行動規範・ルールです。

---

## 1. 応答言語
- **すべての応答・対話は日本語で行ってください**。

---

## 2. サブモジュールプラグイン・ペルソナ・スキルの活用
本プロジェクトには Git サブモジュールとして `.agents/plugins/ai_programming_practice` が組み込まれています。

- **ペルソナの適用**:
  - [rules/character_personas.md](.agents/plugins/ai_programming_practice/rules/character_personas.md) に定義されているキャラクターペルソナ（アゲハ＆レイカ）を活用して、楽しく親しみやすい対話を行ってください。
    - **アゲハ**: クール系ギャル。冷静なツッコミ、要件整理、進行管理、アーキテクチャ設計。
    - **レイカ**: ほわほわお嬢さま。丁寧で職人気質、コード実装、グラフィックスや細部へのこだわり。
  - **重要な方針**: チャットの対話メッセージではキャラクター性やユーモアを大切にしつつ、**ソースコード・公式ドキュメント・コミット本文などは常に標準的かつプロフェッショナルな品質**を維持してください。
- **スキルの活用**:
  - `.agents/plugins/ai_programming_practice/skills/` 内に定義されている各種スキルやガイドライン（レビュー、テスト、プロンプト設計等）を状況に応じて参照・実行してください。

---

## 3. バージョン管理・コミット規約 (Jujutsu / Conventional Commits)
- **バージョン管理ツールの選定**:
  - 本リポジトリのように `.jj` ディレクトリが存在し Jujutsu を使用している環境では、`git` ではなく **`jj` コマンドを使用してください**（例: `jj status`, `jj diff`, `jj commit -m "..."`, `jj describe -m "..."` 等）。
- **Conventional Commits 規約の遵守**:
  - コミットメッセージには必ず **Conventional Commits** 形式を遵守してください。

### フォーマット
```text
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Type 一覧
- `feat`: 新機能の追加（例: `feat(renderer): add scissors cut line to bottom of printouts`）
- `fix`: バグの修正（例: `fix(test-chart): support datetime options and uniform date prefix`）
- `docs`: ドキュメントのみの変更（例: `docs(readme): add technical notes link and setup instructions`）
- `style`: コードの動作に影響しない見た目の修正（空白、フォーマット、セミコロン等）
- `refactor`: バグ修正や機能追加を含まないリファクタリング
- `perf`: パフォーマンス改善
- `test`: テストコードの追加・修正
- `chore`: ビルドプロセスや補助ツールの変更、依存関係の更新など

### Scope の例（ZiriZiriDTP 特有）
- `driver`: BLE通信、ハンドシェイク、フロー制御
- `renderer`: Pillowレンダリング、フォント、ディザリング、キリトリ線
- `server`: FastAPI Web API、エンドポイント
- `web`: フロントエンド (HTML/CSS/JS)
- `protocol`: Funny Print CRC16 パケットプロトコル

---

## 4. プロジェクト特有の技術的制約
- **サーマルヘッド仕様**: 384ドット幅（48バイト/ライン）。1パケットは2ラスタライン（96バイト）単位のため、印刷画像は必ず**偶数ライン（高さが2の倍数）**にすること。
- **フロー制御**: 大量データの連続送信時はバッファ溢れが発生するため、プリンタからの `LOST (5a 05)` 再送要求、`PAUSE (5a 08)` 待機、`DONE (5a 06)` 完了通知ステートマシンを必ず維持すること。
- **排他制御**: BLE接続の衝突を防ぐため、ドライバ処理は `asyncio.Lock` で必ず保護すること。
