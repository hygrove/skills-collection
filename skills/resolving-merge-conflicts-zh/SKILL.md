---
name: resolving-merge-conflicts-zh
description: "当你需要解决一个进行中的 git merge/rebase 冲突（merge conflict / rebase conflict / 解决冲突）时使用。"
---

1. **看清 merge/rebase 的当前状态。** 检查 git 历史，以及冲突的文件。

2. **为每个冲突找到一手来源。** 深入理解每处改动为什么做、最初的意图是什么。读提交信息、查 PR、查原始的 issue/工单。

3. **逐 hunk 解决。** 在可能的地方保留双方意图。在不可兼容处，选与 merge 既定目标相符的那个，并记下取舍。**不要**发明新行为。永远要解决；绝不 `--abort`。

4. 找出项目的**自动化检查**并运行，通常是先 typecheck，再 tests，再 format。修好 merge 弄坏的任何东西。

5. **完成 merge/rebase。** 暂存所有内容并提交。如果是 rebase，继续 rebase 过程直到所有 commit 都 rebase 完。
