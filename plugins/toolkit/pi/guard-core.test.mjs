import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { judge, toClaude } from "./guard-core.mjs";

const cwd = mkdtempSync(join(tmpdir(), "pi-guard-"));

test("pi 工具對應到 Claude 形狀", () => {
  assert.deepEqual(toClaude("bash", { command: "ls" }), { tool_name: "Bash", tool_input: { command: "ls" } });
  assert.deepEqual(toClaude("powershell", { command: "ls" }).tool_name, "Bash");
  assert.deepEqual(toClaude("write", { path: "a", content: "x" }), { tool_name: "Write", tool_input: { content: "x" } });
  assert.deepEqual(toClaude("edit", { path: "a", edits: [{ oldText: "o", newText: "n" }] }).tool_input, { edits: [{ new_string: "n" }] });
  assert.equal(toClaude("read", { path: "a" }), undefined);
});

test("git add -A 擋下（deny）", async () => {
  const v = await judge("bash", { command: "git add -A --dry-run" }, cwd);
  assert.equal(v?.action, "deny");
  assert.match(v.reason, /git-add-all/);
});

test("破壞性 git 要確認（ask）", async () => {
  assert.equal((await judge("bash", { command: "git reset --hard HEAD~1" }, cwd))?.action, "ask");
});

test("一般指令與非判定工具放行", async () => {
  assert.equal(await judge("bash", { command: "git status" }, cwd), undefined);
  assert.equal(await judge("read", { path: "git add -A" }, cwd), undefined);
});

test("找不到 python 時 fail-open", async () => {
  assert.equal(await judge("bash", { command: "git add -A" }, cwd, { pythons: ["no-such-python-xyz"] }), undefined);
});
