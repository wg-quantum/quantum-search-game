# Quantum Wordle — Design Document

Status: **Approved for implementation** (implementation starts only on explicit "実装開始")
Last updated: 2026-07-06

---

## 1. 確定した設計判断 (Decision Log)

| # | 項目 | 決定 |
|---|------|------|
| D1 | Oracleの意味論 | **候補集合マーク方式(案A)を基本**。「フィードバックと整合する全候補」をマークする。正解1語マーク(案B)は将来のLearning用デモとして分離可能な設計にするが、初期スコープ外 |
| D2 | 辞書 | 英語5文字、Wordle正解リスト相当(約2300語)。リポジトリに同梱する場合はライセンス表記を確認し、READMEに出典を明記 |
| D3 | Game Mode | 初期実装は**単一の基本モードのみ**。ただしモードを型として定義し(`GameMode` enum)、拡張点を残す |
| D4 | 実行バックエンド | **シミュレータ(qiskit-aer)を正**とする。IBM Quantum実機は「あれば嬉しい」扱いで、`QuantumBackend`抽象の差し替えで後付けできる構造にする |
| D5 | 利用規模 | 個人利用。セッションはインメモリ辞書で保持。DB/Redisは導入しない |
| D6 | Grover反復回数 | **ユーザーが操作可能**(スライダー)。最適値 ⌊π/4·√(N/M)⌋ をUIに表示しつつ、回しすぎ(over-rotation)で確率が下がる体験を意図的に許容する |
| D7 | デプロイ | localhostで完結することを引き続き保証する。加えてPhase 7で単一コンテナ化(FastAPIがAPI + ビルド済みフロントを同一オリジンで配信)し、無料のHugging Face Docker Spaceへ出せるようにした。詳細は docs/DEPLOY.md |

---

## 2. アーキテクチャ(統合版)

ARCHITECTURE.mdの2つの図を以下の1つに統合する。

```
┌─────────────────────────────────────────┐
│ Frontend (React + TypeScript + Tailwind)│
│  - 表示・入力のみ。ゲーム判定ロジックを持たない │
└───────────────┬─────────────────────────┘
                │ REST (JSON)
┌───────────────▼─────────────────────────┐
│ Backend (FastAPI)                        │
│  ├ API Layer        … ルーティング/入出力検証 │
│  ├ Game Logic       … 判定・候補計算・状態管理 │
│  └ Quantum Engine   … Oracle構築/Grover実行  │
│       ├ QuantumBackend (抽象)             │
│       │    └ AerStatevectorBackend        │
│       └ IBMHardwareRunner (縮約Grover専用) │
│            … SamplerV2で実機投入 + ジョブ登録 │
└─────────────────────────────────────────┘
```

実機は `QuantumBackend` の差し替えではなく**別経路**にした。理由は D4 の方針
(シミュレータを正とする) に加えて、実機では状態ベクトルが取れず `run_grover` の
スナップショットを実装できないこと、そしてゲーム本体の12量子ビットのオラクルが
実機では深すぎること。実機経路は問題を縮約したうえでノイズ観察に使う
(docs/DEPLOY.md, README「実機モード」)。

原則:

- **Single Source of Truth はバックエンド。** Wordle判定・候補フィルタはバックエンドのみに実装する。Phase1でフロントに書いた候補計算は表示用途を除き撤去・移植する。
- 正解の単語は**クライアントに一切送信しない**。
- Quantum EngineはGame Logicから候補インデックス集合を受け取るだけで、Wordleのルールを知らない(疎結合)。

---

## 3. ゲーム仕様の厳密化

### 3.1 Wordleフィードバック規則(本家準拠)

推測の各文字に `green / yellow / gray` を割り当てる。重複文字の扱い:

1. まず全位置についてgreen(位置一致)を確定させる。
2. 残りの文字について、正解側の未消費文字とマッチした分だけ左からyellowを付与する。
3. それ以外はgray。

例: 正解 `SPEED`、推測 `ERASE` → `E`は1つ目がyellow、2つ目もyellow(正解にEが2つ)、`R,A`はgray、`S`はyellow。この規則のテストケースを最初に固定する(golden tests)。

### 3.2 ターンと測定の関係

- 最大6ターン。**ターンを消費するのは単語の推測(guess)のみ。**
- Grover実行・測定は何度でも無料で行える。測定結果は「次の推測の提案」であり、ユーザーはそれを採用しても無視してもよい。
- 理由: 測定を試行錯誤できないと、over-rotation体験(D6)が成立しないため。

### 3.3 量子パート仕様

- **エンコーディング:** 候補辞書全体(N=2300語)にインデックスを振り、12量子ビット(2^12=4096状態)で表現する。
- **パディング状態:** インデックス ≥ N の状態はOracleが決してマークしない。初期状態は全4096状態の一様重ね合わせとし、「辞書外の状態はほぼ増幅されない」ことも可視化の一部とする(**決定済み: 全4096状態を採用。** 辞書外のパディング状態が増幅されず縮んでいく様子も教材とする)。
- **Oracle:** 現在のフィードバック履歴と整合する候補インデックス集合Mをマークする位相Oracle。実装は候補集合から直接構成する(教育UI上は「条件を満たすものに-1を掛ける関数」として説明する)。
- **Grover反復:** ユーザー指定の回数k(0〜上限、例: 最適値の3倍まで)を実行。
- **APIは全反復のスナップショットを一括返却する。** 反復ごとに再計算せず、1回の状態ベクトルシミュレーションで各反復後の確率分布を記録して返す(アニメーション用・レイテンシ対策)。
- **測定:** 最終状態から1サンプル(または指定shots)を返す。候補外インデックスを引いた場合もそのまま見せる(「量子測定は確率的」の教材になる)。

### 3.4 可視化

- 確率分布は**上位20候補+「その他(合計)」**の棒グラフを基本とする。2300本のバーは描画しない。
- 表示要素: 候補数M、全状態数N、現在の反復k、最適反復数k*、正解を引く理論確率、回路図(Qiskit生成のものをPhase5で)。

---

## 4. API契約 (v1)

Base: `/api/v1`。エラーは統一形式 `{ "error": { "code": string, "message": string } }`、HTTPステータスは400/404/422/500を使用。

### POST /games
新規ゲーム作成。
- Res: `{ "game_id": "uuid", "max_turns": 6, "word_length": 5, "dictionary_size": 2300 }`

### GET /games/{game_id}
現在の状態(正解は含まない)。
- Res: `{ "status": "playing|won|lost", "turn": int, "guesses": [{ "word": str, "feedback": ["green"|"yellow"|"gray"] x5 }], "candidate_count": int }`

### POST /games/{game_id}/guesses
- Req: `{ "word": "crane" }`
- 422: 辞書外の単語 / 5文字でない / ゲーム終了済み
- Res: `{ "feedback": [...], "status": ..., "turn": int, "candidate_count": int }`

### GET /games/{game_id}/candidates?limit=50&offset=0
現在の候補一覧(ページング)。
- Res: `{ "total": int, "words": ["..."] }`

### POST /games/{game_id}/quantum/run
- Req: `{ "iterations": int }`(上限をサーバ側で検証)
- Res:
```json
{
  "n_qubits": 12,
  "candidate_count": 42,
  "optimal_iterations": 7,
  "snapshots": [
    { "iteration": 0, "top": [{ "index": 913, "word": "crane", "probability": 0.0102 }], "others_probability": 0.95 },
    { "iteration": 1, "top": [...], "others_probability": ... }
  ]
}
```
- snapshotsは iteration 0(初期一様状態)から k まで。`top` は確率上位20件。

### POST /games/{game_id}/quantum/measure
- Req: `{ "iterations": int, "shots": 1 }`
- Res: `{ "results": [{ "index": int, "word": "crane" | null, "count": 1 }] }`(`word: null` = 辞書外状態)

将来拡張(スコープ外だが壊さない設計にする): `mode` フィールド、`backend: "aer" | "ibm"` パラメータ、Oracleデモ切替。

---

## 5. 状態管理

- `dict[game_id: UUID, GameState]` のインメモリストア。プロセス再起動で消える(個人利用のため許容)。
- `GameState`: answer(サーバ内のみ), guesses, feedback履歴, candidate_indices(キャッシュ), status, created_at。
- 古いゲームはTTL(例: 24h)で掃除する軽量な仕組みを入れる(dict + タイムスタンプで十分)。
- ストアはinterface(Protocol)越しに触り、将来Redis等へ差し替え可能にしておく。

---

## 6. 技術リスクと対策(確定版)

| リスク | 対策 |
|--------|------|
| Qiskit APIの破壊的変更 | `qiskit`, `qiskit-aer` をrequirementsでバージョン固定。IBM実機用 `qiskit-ibm-runtime` はPhase5まで導入しない |
| 案AのGroverは「候補の一様増幅」でしかない | UI文言で正直に伝える:「Groverは候補を等しく持ち上げる。候補を絞るのはあなたの推測」。正解確率 = M中1 を明示 |
| 実機はノイズで結果が潰れる | 実機は「ノイズを見る」オプションデモと位置付け、ゲーム進行には使わない(D4) |
| フロント/バック二重ロジック | 判定・候補計算はバックエンドのみ(§2)。Phase2でフロント側実装を削除するタスクを明記 |
| シミュレーション遅延 | スナップショット一括返却(§3.3)。12qubit状態ベクトルは数ms〜数十msで問題なし |

---

## 7. テスト方針

- **Feedback golden tests:** 重複文字を含む既知ケース(SPEED/ERASE等)を網羅。
- **Candidate filter:** フィードバック履歴→候補集合の一致をプロパティ的に検証(候補は必ず全履歴と整合する)。
- **Oracle:** マークされる状態集合が候補インデックス集合と一致することを状態ベクトルで検証。
- **Grover:** 既知の小規模ケース(例: N=16, M=1)で最適反復時に確率が理論値と一致すること。over-rotationで確率が下がることも1ケース検証。
- **API:** FastAPI TestClientでハッピーパス+エラー(辞書外単語、終了済みゲーム等)。

---

## 8. フェーズ計画(TODO.md改訂案)

- **Phase 2 — Backend基盤:** FastAPI雛形 / 判定・候補ロジックをバックエンドに実装(golden tests先行)/ ゲームAPI(games, guesses, candidates)/ インメモリState / フロントをAPI接続に切替え、フロント側判定ロジック削除
- **Phase 3 — Quantum Engine(シミュレータ):** インデックスエンコーディング / 候補集合Oracle / QuantumBackend抽象 + Aer実装 / quantum/run(snapshots)
- **Phase 4 — Grover体験:** Diffusion含む完全なGroverループ / 反復スライダー / 確率分布アニメーション / quantum/measure / over-rotation体験
- **Phase 5 — 発展:** 回路図表示 / IBM Quantumバックエンド(任意)/ 演出強化
- **Phase 6 — 仕上げ:** チュートリアル文言(誤概念対策を含む)/ README整備(clone→起動手順、辞書出典、スクリーンショット)/ Docker(任意)

---

## 9. README要件(D7対応)

READMEには最低限以下を含める: プロジェクト目的(1段落)、スクリーンショット、必要環境(Node/Pythonバージョン)、セットアップ手順(backend: venv + pip install + uvicorn、frontend: npm install + npm run dev)、テスト実行方法、辞書の出典とライセンス、アーキテクチャ概略図。
