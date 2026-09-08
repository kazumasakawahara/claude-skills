# claude-skills

Claude 用の自作 Agent Skills を 3 本、公開しています。「決める」「調べる」「AI の完了報告を疑う」の 3 つの場面に 1 本ずつです。日本語で書かれており、Claude の応答も日本語になります。

| スキル | 一行で言うと | 使う場面 | 使わない場面 |
|---|---|---|---|
| **deliberation-sim** | 決める道具。課題から賛成・反対・折衷・不在の当事者・裁定者の人格を生成し、確信度の変化を追跡しながら議論させて結論を導く熟議シミュレータ | 「やるべきか」「A か B か」「反対意見も潰しておきたい」「会議で結論を出す必要がある」 | 単なる情報質問、選択肢が 1 つしかない場面、決定済みで実行手順だけが要る場面、**決定権者が本人で本人の希望を聞くべき意思決定支援の場面**（本人の意思を人格の議論で代替してはいけない） |
| **hypothesis-arena** | 調べる道具。問いから相互排他的な仮説群と擁護者を生成し、文献予測と自滅条件を宣言させて競争させ、決着に最も効く判別読書課題を導く仮説競争シミュレータ | 「なぜ〜なのか」「どの説が有力か」「対立する学説を整理したい」「どの文献を読めば決着するか」 | 「〜すべきか」の意思決定（それは deliberation-sim）、単発の事実確認、文献の取得・変換そのもの |
| **acceptance-inspector** | AI の完了報告を疑う道具。「完了しました」と主張する成果物を、作業者と独立した立場で受入基準に照らして検品し、合否ではなく検証項目ごとの根拠と未検証の明示を返す | サブエージェントや Claude Code が「完了」「テスト通過」と報告した直後、本番反映の前、他者に成果物を渡す前 | 読んで論評する「レビュー」、作業者自身が自分の成果物を自己検品する用途（独立性が満たせない） |

各スキルの詳しい手順は `skills/<name>/SKILL.md` と、同じフォルダの `PROTOCOL.md`・`reference/`・`examples/`・`templates/` にあります。

## 入れ方（claude.ai / Claude Desktop）

**カスタムスキルの利用には Pro 以上のプランが必要です**（Free では設定項目が出ません）。

1. [Releases](https://github.com/kazumasakawahara/claude-skills/releases) から使いたいスキルの ZIP（`deliberation-sim.zip` 等）をダウンロードする
2. claude.ai の **設定 → カスタマイズ → スキル** を開く
3. **アップロード** を押し、ダウンロードした ZIP を選ぶ
4. 新しい会話を始めて、上の表の「使う場面」の言い方で頼む。スキルは自動で選ばれます（選ばれないときは「deliberation-sim を使って」のようにスキル名を言えば起動します）

ZIP は 1 スキル 1 本です。3 本とも使うなら 3 回アップロードしてください。更新するときは同じ手順で置き換えます。

## 入れ方（Claude Code）

```
/plugin marketplace add kazumasakawahara/claude-skills
/plugin install deliberation-sim@kawahara-skills
/plugin install hypothesis-arena@kawahara-skills
/plugin install acceptance-inspector@kawahara-skills
```

marketplace 名は `kawahara-skills` です。プラグイン名はスキル名と同じです。

## 環境固有の設定と `local.md.example`

3 本とも、既定は **claude.ai だけで動く形**になっています。台帳や報告はダウンロードできる Markdown ファイルとして返し、立論は 1 つの会話で順に行い、継続の観測点は本文に期日を書いて人間に渡します。

各スキルの `local.md.example` は、**Claude Code でサブエージェント並列や期日管理ツールとの連携などの拡張を使う人向け**の設定例です。スキルと同じディレクトリに `local.md` という名前で置くと、SKILL.md の「環境固有の設定」節の既定を上書きします。**claude.ai だけで使う場合は無視してかまいません。**

## 個人の情報を扱うとき

個人の情報を入れて使う場合は各自の責任でお願いします。台帳・報告ファイルに実名を残さないことを勧めます（イニシャルや役割名に置き換える）。

## 較正について

これらのスキルの当たり（deliberation-sim・hypothesis-arena の確信度の当たり、acceptance-inspector の欠陥検出率）は、まだ体系的に測っていません。acceptance-inspector には自己較正の手順（`references/canary.md`）を同梱していますが、著者の環境でも初回較正は未実施です。出力は判断材料であって判定ではない、と考えて使ってください。

## English

Three Japanese-language Agent Skills for Claude: **deliberation-sim** (a multi-persona deliberation simulator for "should we / which one" decisions), **hypothesis-arena** (a competing-hypotheses simulator for "why / which theory" questions that ends with a discriminating reading list), and **acceptance-inspector** (an independent acceptance-inspection role that checks an AI's "done" claim against explicit criteria and reports evidence per item, including what it could not verify). Install on claude.ai / Claude Desktop (Pro or higher) by uploading a ZIP from [Releases](https://github.com/kazumasakawahara/claude-skills/releases) under Settings → Customize → Skills, or in Claude Code with `/plugin marketplace add kazumasakawahara/claude-skills` and `/plugin install <skill>@kawahara-skills`. The skills' prompts and outputs are in Japanese.

## 配布物の作り方（メンテナ向け）

```
scripts/check-parity.sh          # 固有語の混入・LEDGER 写しのずれ・local.md の混入を検査（0 終了で合格）
scripts/build-release.sh v0.1.0  # git archive から dist/<name>.zip を 3 本生成（追跡外ファイルは構造的に入らない）
```

## ライセンス

MIT License. 詳細は [LICENSE](LICENSE)。
