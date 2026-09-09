# Quantum Wordle

Wordleを題材に、Grover Algorithm(Oracle・Diffusion・振幅増幅)を直感的に学べる教育ゲーム。

これは「Wordleを解くゲーム」ではなく、**「Oracleを変えればGroverはどんな探索にも使える」ことを体験するためのゲーム**です。Groverは正解を知りません。フィードバックと整合する候補集合をOracleがマークし、その振幅が増幅される様子を観察します。

## Architecture

```
Frontend (React + TS + Tailwind)
        │ REST (JSON)
Backend (FastAPI)
  ├ API Layer        ルーティング / 入出力検証
  ├ Game Logic       Wordle判定・候補計算・状態管理 (Single Source of Truth)
  └ Quantum Engine   Oracle構築 / Grover実行 (Qiskit, Phase 3〜)
```

詳細は [docs/DESIGN.md](./docs/DESIGN.md) を参照。

## 画面構成

```
┌──────────────────────────────────────────────────────────┐
│ Quantum Wordle                        [使い方] [新しいゲーム] │
├────────────────────────────┬─────────────────────────────┤
│  Wordle 盤面 (6 × 5)         │  候補空間パネル               │
│  ■ ■ ■ ■ ■   ← 推測を入力     │   候補 294 / 2315 語         │
│  緑=一致 / 黄=位置違い / 灰=無  │   [logスケールメーター]       │
│  スクリーンキーボード          │                             │
│                            │  Grover Lab                 │
│                            │   反復 k スライダー (k* 表示)  │
│                            │   [Grover を実行] [測定]      │
│                            │   P(候補) スパークライン        │
│                            │   振幅チャート(上位状態)        │
│                            │   回路図を見る → Qiskit SVG   │
└────────────────────────────┴─────────────────────────────┘
```

初回起動時にチュートリアル（後述）が開きます。

## Requirements

- Python 3.12+
- Node.js 20+ (frontend)

## Quick Start

frontend と backend をまとめて起動できます(要 `make`。初回のみ各 Setup 参照)。

```bash
make dev        # frontend + backend を同時起動 (Ctrl+C で両方停止)
make backend    # backend のみ
make frontend   # frontend のみ
make install    # 依存関係をまとめてインストール
make test       # backend + frontend のテスト
```

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Run tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

### Frontend

バックエンド(port 8000)を起動した状態で:

```bash
cd frontend
pnpm install
pnpm dev   # http://localhost:5173 を開く
```

開発サーバーは `/api` へのリクエストを `127.0.0.1:8000` にプロキシします(`vite.config.ts`)。

```bash
pnpm test        # vitest
pnpm build       # TypeScript strict チェック + 本番ビルド
```

## API (v1)

| Method | Path | 説明 |
|--------|------|------|
| POST | `/api/v1/games` | 新規ゲーム作成 |
| GET | `/api/v1/games/{id}` | 状態取得(正解は含まれない) |
| POST | `/api/v1/games/{id}/guesses` | 推測 `{"word": "crane"}` |
| GET | `/api/v1/games/{id}/candidates?limit=&offset=` | 現在の候補一覧 |
| POST | `/api/v1/games/{id}/quantum/run` | Grover実行 `{"iterations": k}` — iteration 0〜k の確率分布スナップショットを返す |
| POST | `/api/v1/games/{id}/quantum/measure` | 測定 `{"iterations": k, "shots": n}` — 最終状態からサンプリング |
| GET | `/api/v1/games/{id}/quantum/circuit?iterations=k` | Grover回路図 (Qiskit生成SVG, 図は最大3反復分) |
| GET | `/api/v1/quantum/hardware` | 実機モードが使えるか（ネットワークアクセスなし・軽量） |
| POST | `/api/v1/games/{id}/quantum/hardware` | 縮約Groverを実機QPUへ投入。`202` でジョブIDを即返す |
| GET | `/api/v1/quantum/jobs/{job_id}` | 実機ジョブのポーリング。完了後はローカル記録から返す |

エラー形式: `{"error": {"code": "...", "message": "..."}}`

## チュートリアルと「よくある誤解」

初回起動時に 5 ステップのチュートリアルが自動表示され、ヘッダーの **使い方** ボタンでいつでも再表示できます（既読状態は `localStorage` に記憶）。狙いは Grover に対する誤概念の解消です。

- **Grover は正解を知らない。** Oracle は「正解の 1 語」ではなく、**これまでのフィードバックと矛盾しない候補すべて**に印（位相反転）を付ける条件判定関数です。
- **候補を絞るのはあなた。** Grover は候補を等しく持ち上げるだけで、測定で正解を引く確率はおよそ `1 / 候補数`。確率を上げる近道は良い推測で候補そのものを減らすことです。
- **回しすぎると下がる（over-rotation）。** 反復回数 `k` は多いほど良いのではなく、最適値 `k*` を超えると確率は再び下がります。Grover Lab のスライダーで体験できます。

## Dictionary

`backend/data/words.txt` — [Stanford GraphBase](https://www-cs-faculty.stanford.edu/~knuth/sgb.html) (Donald E. Knuth) の5文字英単語リスト([five-letter-words](https://github.com/charlesreid1/five-letter-words) 経由)から、使用頻度上位2315語を採用。12量子ビット(4096状態)に収まるサイズ。

## 実機モード (IBM Quantum QPU)

サーバに `IBM_QUANTUM_TOKEN` があるときだけ、盤面の下に **実機モード** パネルが現れます。
無い場合は API が `available: false` を返し、パネルは描画されません（シミュレータのみで完動）。

**なぜ「縮約」するのか。** ゲーム本体のオラクルは 12 量子ビット・4096 位相の
`DiagonalGate` です。これをトランスパイルすると 2 量子ビットゲートが数万段になり、
現行の NISQ デバイスでは出力がほぼ一様分布 — つまり信号が残りません
（`docs/DESIGN.md` の D4 とリスク表に元々書かれていた通りです）。

そこで実機モードは**同じアルゴリズムを縮約**します。

- 候補列（辞書順 = 頻度順）の先頭から最大 4 語を取り、**2 の冪に丸めて** 2〜4 量子ビットの空間へ振り直す
- 候補の割合がちょうど 1/4 になるので、最適反復数は常に `k* = 1`、理想成功確率は**ちょうど 100%**
- したがって**実機との差分がそのまま装置のノイズ**として読める

**2 の冪に丸める理由（`ibm_marrakesh` 実測）。** マーク集合を `{0..m-1}` の整列ブロックに
すると、「`x < m`」は「上位 `n - log2(m)` 量子ビットが全部 0」と同義になり、**オラクル
全体が多重制御 Z 1 個**に潰れます。トランスパイラはこの恒等式を自力では見つけないので、
回路側で書く必要があります。効果は決定的でした:

| オラクルの組み方 | ISA深さ | 2Qゲート | 実機 P(候補) |
|---|---|---|---|
| 状態ごとに1個ずつ | 423 | 137 | **38.7%** — 増幅がノイズにほぼ埋もれる |
| 整列ブロックで1個 | 81 | 19 | **90.0%** |

（どちらも `shots=1024`, 理想 100%, 一様分布 25%。後者はマーク4状態が各 21〜23%、
残り12状態への漏れは各 0.2〜1.7%。QPU 課金時間はどちらも 2 秒）

オラクルは `DiagonalGate` ではなく多重制御 Z で組み直してありますが、同じユニタリです
（`tests/test_hardware.py` が分布とオペレータの一致、およびブロック形式が本当に
ゲート 1 個であることを検証しています）。ジョブは `SamplerV2` で投入し、`202` で
job_id を即返してフロントがポーリングします — 実機のキュー待ちは数分〜数十分に
なり得るため、HTTP リクエストを待たせません。

QPU 時間は Open Plan で月約 10 分（600 秒）で、実測で 1 ジョブ 2 秒です。公開デプロイでは
1 つのトークンを訪問者全員が共有するため、投入上限はプロセス全体で数えています
（既定 1 時間 3 件 / 1 日 6 件 ≒ 月 360 秒）。詳細と環境変数は
[docs/DEPLOY.md](./docs/DEPLOY.md)。

## デプロイ

FastAPI が API とビルド済みフロントエンドの両方を配信する単一コンテナ構成（`Dockerfile`）。
デプロイ先は **Render の無料プラン**で、`render.yaml` を Blueprint として置いてあります
（0.1 CPU / 512 MB に対して実測ピーク 156 MB）。ダッシュボードで New → Blueprint から
このリポジトリを選び、`IBM_QUANTUM_TOKEN` を入力するだけです。

Hugging Face の無料 Docker Space は 2026 年時点で廃止され PRO 契約が必要になったため、
`deploy/hf_space.py` は PRO 向けの選択肢として残してあります。候補の比較・環境変数・
QPU 枠の見積もり・スリープ対策は [docs/DEPLOY.md](./docs/DEPLOY.md)。

## Project Status

Phase 1〜6 完了 + 実機モードとデプロイを追加。バックエンド 72 テスト + フロント 24 テスト通過、
TypeScript strict ビルド・E2E 疎通確認済み。

進捗は [TODO.md](./TODO.md)。
