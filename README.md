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

エラー形式: `{"error": {"code": "...", "message": "..."}}`

## チュートリアルと「よくある誤解」

初回起動時に 5 ステップのチュートリアルが自動表示され、ヘッダーの **使い方** ボタンでいつでも再表示できます（既読状態は `localStorage` に記憶）。狙いは Grover に対する誤概念の解消です。

- **Grover は正解を知らない。** Oracle は「正解の 1 語」ではなく、**これまでのフィードバックと矛盾しない候補すべて**に印（位相反転）を付ける条件判定関数です。
- **候補を絞るのはあなた。** Grover は候補を等しく持ち上げるだけで、測定で正解を引く確率はおよそ `1 / 候補数`。確率を上げる近道は良い推測で候補そのものを減らすことです。
- **回しすぎると下がる（over-rotation）。** 反復回数 `k` は多いほど良いのではなく、最適値 `k*` を超えると確率は再び下がります。Grover Lab のスライダーで体験できます。

## Dictionary

`backend/data/words.txt` — [Stanford GraphBase](https://www-cs-faculty.stanford.edu/~knuth/sgb.html) (Donald E. Knuth) の5文字英単語リスト([five-letter-words](https://github.com/charlesreid1/five-letter-words) 経由)から、使用頻度上位2315語を採用。12量子ビット(4096状態)に収まるサイズ。

## Project Status

Phase 1〜6 完了。バックエンド 35 テスト + フロント 13 テスト通過、TypeScript strict ビルド・E2E 疎通確認済み。IBM Quantum 実機連携（下記）と Docker 化は任意扱いで未実装。

## IBM Quantum 実機について (future work)

実機連携は未実装ですが、接続点は用意済みです。`app/quantum/backend.py` の `QuantumBackend` Protocol (`run_grover` / `sample`) を実装するクラスを追加し、`create_app(quantum_backend=...)` に渡せば差し替わります。実装時の注意:

- `qiskit-ibm-runtime` を追加し、SamplerV2 で `sample` 相当を実装する (状態ベクトル取得は実機では不可のため、`run_grover` のスナップショットはシミュレータ専用のまま残す)
- 12量子ビットのDiagonalオラクルはトランスパイル後に非常に深い回路になり、現行NISQデバイスではノイズで結果がほぼ一様分布になる。これは「実機のノイズを観察する」教材として扱い、ゲーム進行には使わないこと (docs/DESIGN.md リスク表参照)。

進捗は [TODO.md](./TODO.md)。
