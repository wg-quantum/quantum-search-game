---
title: Quantum Wordle
emoji: 🎲
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
short_description: Grover探索でWordleの候補を絞る量子ゲーム
---

# Quantum Wordle

Wordle を解きながら Grover 探索を体験する教材です。オラクルは**答えを知りません** —
毎ターンのフィードバックから絞り込まれた「候補集合」の位相を反転するだけで、
候補を絞るのはプレイヤー自身です。

- **Grover Lab** — 反復回数 k を動かして振幅増幅と over-rotation を観察します（qiskit-aer）
- **実機モード** — 同じアルゴリズムを縮約して IBM Quantum の実機 QPU で走らせ、
  理想分布と並べてノイズを見ます（サーバに認証情報がある場合のみ表示）

ゲーム本体の 12 量子ビットのオラクルは、トランスパイルすると数万ゲートの深さになり
実機では結果がノイズに埋もれます。そのため実機モードでは候補の上位数語を 2〜4
量子ビットの空間に詰め直し、候補の割合を 1/4 にして k = 1 回で済む浅い回路に
してから投入します。理想成功確率がほぼ 100% になるので、実機との差分が
そのまま装置のノイズとして読めます。

ソース: <https://github.com/wg-quantum/quantum-search-game>
