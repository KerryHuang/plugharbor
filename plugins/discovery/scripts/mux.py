#!/usr/bin/env python3
"""派工用的終端多工轉接：同一組動作，後端是 Herdr.app（hc）或 herdr TUI。

用法：mux.py <動作> ...，stdout 為 JSON（read 例外，輸出畫面純文字）。
  env                                  → {"backend":"hc|herdr|none","self":…,"window":bool[,"window_error":…]}
  spawn --name N --kind K --cwd D [--env K=V]... -- <CLI 參數>   → {"id":…,"visible":bool[,"pane":…]}
  send ID (--text T | --file F) [--wait] [--timeout 秒]          → {"status":S,"raw":…}
  wait ID [--timeout 秒]                                          → {"status":S,"raw":…}
  read ID [--lines N] | alive ID | session ID | close ID | attach-hint ID
  session：hc 讀不到 session id 時回 {"session":null,"hint":…}（hc 需 toolkit 的 SessionStart hook 記錄）。
  send（hc、worker 剛起 turn 0）：先 hc wait（至多 60 秒）再加 --if idle；status 仍不是 idle 時回 {"status":"blocked","hint":…}，不重試。
S：done|idle|working|blocked|error|timeout|gone（兩邊的原始值在這裡映射，原樣放 raw）。
錯誤：stdout 印 {"error":kind,"hint":…}；exit 2 用法、3 core_not_running、4 no_backend、1 其他。
環境變數：MUX_BACKEND 強制後端；MUX_CORE_SOCKET 覆寫 core socket 路徑；
MUX_LAYOUT_CMD 取代 TUI 版面腳本、MUX_APP_LAYOUT_CMD 取代 app 版面腳本（測試用）。

core 沒跑時不得呼叫任何 hc（hc 會以呼叫者環境自動啟動 core），所以先直接連 socket 判斷。
"""
import argparse, json, os, shlex, shutil, socket, subprocess, sys
from pathlib import Path

# Windows 預設 cp950：印中文會亂碼。腳本自己處理，不靠呼叫端設 PYTHONUTF8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

# core 以呼叫者環境啟動時會把這些帶進每個 hc 終端；worker 不能繼承（會蓋掉主 session 的回報、
# CLAUDE_CODE_CHILD_SESSION 還會讓 transcript 不落檔、HERDR_SOCKET_PATH 會讓 pi 向 TUI socket 回報）。
# 清單與 clis.mjs scrubEnv 的 CLAUDE_CODE_* 已知名稱及 HERDR_* 對齊。
# 不含 HC_*：那是 hc 替 worker 自己設的身分，unset 會讓 worker 內的 hc 失效（拋棄式 CLI 不經 hc，由 scrubEnv 另濾）。
POLLUTED_VARS = (
    "CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_EXECPATH", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_BRIDGE_SESSION_ID", "CLAUDE_CODE_SESSION_ATTENDED",
    "HERDR_ENV", "HERDR_PANE_ID", "HERDR_SOCKET_PATH", "HERDR_TAB_ID", "HERDR_WORKSPACE_ID",
)

MAX_WORKERS = 6  # 同 herdr_layout.py；TUI 主 tab 的 worker 上限
STATES = ("done", "idle", "working", "blocked", "error", "timeout", "gone")
KINDS = ("claude", "codex", "agy", "pi")
EXIT_CODES = {"core_not_running": 3, "no_backend": 4}


class MuxError(Exception):
    def __init__(self, kind, hint="", code=None):
        super().__init__(kind)
        self.kind, self.hint = kind, hint
        self.code = code or EXIT_CODES.get(kind, 1)


# ---------- 偵測 ----------

def detect_backend(env, ancestors=None, hc_pid=None, herdr_pid=None):
    forced = env.get("MUX_BACKEND")
    if forced in ("hc", "herdr", "none"):
        return forced
    has_hc = bool(env.get("HC_TERMINAL_ID"))
    has_herdr = env.get("HERDR_ENV") == "1" and bool(env.get("HERDR_PANE_ID"))
    if has_hc and not has_herdr:
        return "hc"
    if has_herdr and not has_hc:
        return "herdr"
    if not has_hc:
        return "none"
    # 兩組都在：離自己最近的祖先終端勝出，查不到就 hc
    chain = list(ancestors or [])
    pos = lambda pid: chain.index(pid) if pid is not None and pid in chain else None
    h, d = pos(hc_pid), pos(herdr_pid)
    if h is not None and d is not None:
        return "herdr" if d < h else "hc"
    if d is not None:
        return "herdr"
    if h is not None:
        return "hc"
    if chain and hc_pid is not None and herdr_pid is None:
        return "herdr"  # 知道 hc 終端的程序卻不是自己的祖先：自己不在 hc 終端內
    return "hc"


def socket_path(env=None):
    env = os.environ if env is None else env
    if env.get("MUX_CORE_SOCKET"):
        return env["MUX_CORE_SOCKET"]
    if env.get("HC_SOCKET"):
        return env["HC_SOCKET"]
    state = env.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return str(Path(state) / "herdr-core" / (env.get("HC_SESSION") or "default") / "default.sock")


def core_running():
    """以 connect 成功為準；檔案存在不算（stale socket 會 ConnectionRefused）。"""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect(socket_path())
        return True
    except OSError:
        return False
    finally:
        s.close()


def clean_env_prefix(extra):
    out = ["env"]
    for v in POLLUTED_VARS:
        out += ["-u", v]
    return out + [f"{k}={v}" for k, v in extra.items()]


def process_ancestors():
    chain, pid = [], os.getppid()
    while pid and pid > 1 and len(chain) < 64:
        chain.append(pid)
        r = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)], capture_output=True, text=True)
        try:
            pid = int(r.stdout.strip())
        except ValueError:
            break
    return chain


def find_key(data, *keys):
    """遞迴找第一個 key（依 keys 順序優先）；hc／herdr 的 JSON 層級不固定。"""
    for key in keys:
        stack = [data]
        while stack:
            cur = stack.pop(0)
            if isinstance(cur, dict):
                if key in cur:
                    return cur[key]
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
    return None


def to_status(value):
    if isinstance(value, dict):
        value = value.get("state") or value.get("status")
    if value in ("done", "idle", "working", "blocked", "error", "timeout", "gone"):
        return value
    if value in ("finished", "exited", "killed"):
        return "gone"
    return "error"


def run(argv, env=None):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", env=env)
    except FileNotFoundError:
        raise MuxError("command_not_found", f"找不到 {argv[0]}")
    return r.returncode, r.stdout, r.stderr


def parse_json(text):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def window_open(env):
    """Herdr.app 視窗開著嗎。只有 `herdr-app status` exit 2 且訊息含 no Herdr window 才算沒開（spike 第 9 項）；
    其他失敗（路徑過長、app 掛了…）回 window_error，不當成沒開。找不到 herdr-app 視為沒開。"""
    if not shutil.which("herdr-app", path=env.get("PATH")):
        return False
    code, out, err = run(["herdr-app", "status"], env=env)
    if code == 0:
        return True
    if code == 2 and "no Herdr window" in (err or out):
        return False
    raise MuxError("window_error", f"herdr-app status 失敗（exit {code}）：{(err or out).strip()[:300]}")


def fail_from(what, code, out, err):
    raise MuxError("backend_error", f"{what} 失敗（exit {code}）：{(err or out).strip()[:300]}")


# ---------- hc ----------

class HcBackend:
    name = "hc"

    def __init__(self, env):
        self.env = env

    def hc(self, *args, strip_id=False):
        env = dict(self.env)
        if strip_id:
            # 不讓 hc 把訊息包成 <hc from=…>：hc 以呼叫端身分決定是否包裝
            env.pop("HC_TERMINAL_ID", None)
        return run(["hc", *args], env=env)

    def get(self, ident):
        code, out, err = self.hc("get", "--json", ident)
        return code, parse_json(out)

    def spawn(self, name, kind, cwd, env_pairs, cli_args):
        cli = shutil.which(kind, path=self.env.get("PATH"))
        if not cli:
            # hc run 的 argv 由 core 的 PATH 解析，不是呼叫者的；core 的 PATH 常缺 ~/.bun/bin 之類
            raise MuxError("cli_not_found", f"PATH 找不到 {kind}")
        window = window_open(self.env)  # 先判斷：window_error 時不留下沒人看得到的 worker
        argv = ["run", "--json", "--bg", "--no-notify", "--name", name, "--cwd", cwd,
                *clean_env_prefix(env_pairs), cli]
        if kind == "codex":
            argv.append("--no-daemon")
        code, out, err = self.hc(*argv, *cli_args)
        data = parse_json(out)
        ident = find_key(data, "address") if data is not None else None
        if code != 0 or not ident:
            fail_from("hc run", code, out, err)
        pane = self._place(ident) if window else None
        return {"id": ident, "visible": True, "pane": pane} if pane else {"id": ident, "visible": False}

    def _main_pane(self):
        """用自己的 HC_TERMINAL_ID 在 herdr-app ls 找主 session 的 pane id；不在視窗內回 None。"""
        me = self.env.get("HC_TERMINAL_ID")
        code, out, err = run(["herdr-app", "ls"], env=self.env)
        data = parse_json(out) if code == 0 else None
        stack = [data]
        while stack and me:
            cur = stack.pop(0)
            if isinstance(cur, dict):
                if cur.get("terminal") == me and cur.get("pane"):
                    return cur["pane"]
                stack.extend(cur.values())
            elif isinstance(cur, list):
                stack.extend(cur)
        return None

    def _place(self, ident):
        """把已在背景跑的 worker 放進主 session 所在 tab；任何一步失敗都回 None（worker 照跑，visible:false）。"""
        main = self._main_pane()
        if not main:
            return None
        cmd = os.environ.get("MUX_APP_LAYOUT_CMD")
        argv = shlex.split(cmd) if cmd else [sys.executable, str(Path(__file__).with_name("app_layout.py"))]
        if not (cmd or Path(argv[1]).exists()):
            return None
        code, out, err = run([*argv, "place", "--main", main, "--terminal", ident], env=self.env)
        data = parse_json(out)
        if code != 0 or not isinstance(data, dict) or not data.get("pane"):
            print(f"mux: 版面放置失敗（worker 仍在背景執行）：{(err or out).strip()[:200]}", file=sys.stderr)
            return None
        return data["pane"]

    def _status(self, code, out, err, what):
        data = parse_json(out)
        if data is None:
            fail_from(what, code, out, err)
        wait = data.get("wait") if isinstance(data, dict) else None
        info = wait if isinstance(wait, dict) else data
        if isinstance(info, dict) and info.get("ended") is False:
            out = {"status": "timeout", "raw": data}
            if info.get("reason"):
                out["reason"] = info["reason"]  # message＝有訊息打斷等待，不是逾時；呼叫端自行判讀
            return out
        status = info.get("status") if isinstance(info, dict) else None
        if status is None and isinstance(data, dict):
            status = data.get("status")
        if status is None and isinstance(info, dict) and info.get("ended") is True:
            return {"status": "gone", "raw": data}  # 已結束且沒有狀態：被 kill 或程序結束
        return {"status": to_status(status), "raw": data}

    def send(self, ident, text, wait, timeout):
        args = ["send", "--json"]
        # 剛起的 worker（turn 0）可能停在信任對話框，此時 status 是 null；send 的 Enter 會選預設項。
        # --if idle：只在 status 恰為 idle 才打字，否則 hc 回 status_mismatch（exit 10）
        _, info = self.get(ident)
        guarded = isinstance(info, dict) and info.get("turn") == 0
        if guarded:
            # spawn 剛回傳時 status 仍是 null（約 1 秒後才變 idle）：先等到就緒，逾時就照 --if idle 讓 hc 判斷
            self.hc("wait", "--json", "--timeout", str(min(timeout, 60) if timeout else 60), ident)
            args += ["--if", "idle"]
        if wait:
            args.append("--wait")
            if timeout:
                args += ["--timeout", str(timeout)]
        code, out, err = self.hc(*args, "--", ident, text, strip_id=True)
        sent = parse_json(out)
        if guarded and (code == 10 or (isinstance(sent, dict) and sent.get("started") is False)):
            return {"status": "blocked", "raw": sent if sent is not None else (err or out).strip(),
                    "hint": "worker 尚未就緒，可能停在啟動對話框；先 read 畫面，請使用者用 attach-hint 進去處理"}
        if not wait:
            data = parse_json(out)
            if code != 0 or data is None:
                fail_from("hc send", code, out, err)
            return {"status": "working", "raw": data}
        return self._status(code, out, err, "hc send --wait")

    def wait(self, ident, timeout):
        args = ["wait", "--json"]
        if timeout:
            args += ["--timeout", str(timeout)]
        return self._status(*self.hc(*args, ident), "hc wait")

    def read(self, ident, lines):
        args = ["read", ident]
        if lines is not None:
            args += ["--lines", str(lines)]
        code, out, err = self.hc(*args)
        if code != 0:
            fail_from("hc read", code, out, err)
        return out

    def alive(self, ident):
        code, data = self.get(ident)
        return code == 0 and isinstance(data, dict) and find_key(data, "state") == "live"

    session_hint = "hc 下需 toolkit 的 SessionStart hook 記錄 session id"

    def session(self, ident):
        # hc 不提供 agent session id；由 toolkit 的 SessionStart hook 記在 hc-sessions/<terminal id>
        code, data = self.get(ident)
        addr = find_key(data, "address") if code == 0 and data is not None else None
        if not addr or "/" in addr or addr.startswith("."):
            return None
        base = self.env.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
        try:
            text = Path(base, "plugharbor", "hc-sessions", addr).read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return text or None

    def close(self, ident):
        code, out, err = self.hc("kill", ident)
        if code != 0:
            fail_from("hc kill", code, out, err)
        self.hc("rm", ident)  # 只移除紀錄，視窗格 kill 後就消失；rm 失敗不影響收工
        return True

    def attach_hint(self, ident):
        return f"hc attach {ident}（或在 Herdr.app 內點該格）"


# ---------- herdr ----------

class HerdrBackend:
    name = "herdr"

    def __init__(self, env):
        self.env = env

    def herdr(self, *args):
        return run(["herdr", *args], env=self.env)

    def _worker_count(self):
        """主 pane 所在 tab 的 worker 數（pane layout 看得到的 pane 扣掉主 pane）；查不到回 0。"""
        main = self.env.get("HERDR_PANE_ID")
        if not main:
            return 0
        code, out, _ = self.herdr("pane", "layout", "--pane", main)
        panes = find_key(parse_json(out), "panes") if code == 0 else None
        if not isinstance(panes, list):
            return 0
        return len([p for p in panes if isinstance(p, dict) and p.get("pane_id") != main])

    def spawn(self, name, kind, cwd, env_pairs, cli_args):
        envs = [x for k, v in env_pairs.items() for x in ("--env", f"{k}={v}")]
        if self._worker_count() >= MAX_WORKERS:
            # 主 tab 滿了：開新 tab，不切主 session、不重排
            code, out, err = self.herdr("tab", "create", "--cwd", cwd, "--label", name, "--no-focus", *envs)
            data = parse_json(out)
            root = find_key(data, "root_pane") if data is not None else None
            pane = root.get("pane_id") if isinstance(root, dict) else None
            if code != 0 or not pane:
                fail_from("herdr tab create", code, out, err)
        else:
            code, out, err = self.herdr("pane", "split", "--current", "--direction", "right", "--cwd", cwd,
                                        "--no-focus", *envs)
            data = parse_json(out)
            pane = find_key(data, "pane_id") if data is not None else None
            if code != 0 or not pane:
                fail_from("herdr pane split", code, out, err)
            self._layout()
        code, out, err = self.herdr("agent", "start", name, "--kind", kind, "--pane", pane, "--", *cli_args)
        if code != 0:
            screen = self.herdr("pane", "read", pane)[1].strip()[-300:]
            self.herdr("pane", "close", pane)
            raise MuxError("spawn_failed", f"herdr agent start 失敗：{(err or out).strip()[:200]}；畫面：{screen}")
        self.herdr("pane", "rename", pane, name)
        return {"id": pane, "visible": True}

    def _layout(self):
        cmd = os.environ.get("MUX_LAYOUT_CMD")
        argv = shlex.split(cmd) if cmd else [sys.executable, str(Path(__file__).with_name("herdr_layout.py"))]
        main = self.env.get("HERDR_PANE_ID")
        if not main or not (cmd or Path(argv[1]).exists()):
            return
        code, out, err = run([*argv, "--main", main], env=self.env)
        if code != 0:
            print(f"mux: 版面重排失敗（不影響 worker）：{(err or out).strip()[:200]}", file=sys.stderr)

    def _status(self, code, out, err, what):
        data = parse_json(out)
        if code != 0:
            e = parse_json(err) or parse_json(out) or {}
            raw = e.get("error", e) if isinstance(e, dict) else e
            blob = json.dumps(raw).lower()
            if "timeout" in blob:
                return {"status": "timeout", "raw": e}
            if "not_found" in blob:
                return {"status": "gone", "raw": e}
            if "agent_blocked" in blob:
                return {"status": "blocked", "raw": e}
            return {"status": "error", "raw": e or (err or out).strip()}
        if data is None:
            fail_from(what, code, out, err)
        return {"status": to_status(find_key(data, "agent_status", "status", "state")), "raw": data}

    def send(self, ident, text, wait, timeout):
        args = ["agent", "prompt", ident, text]
        if wait:
            args.append("--wait")
            if timeout:
                args += ["--timeout", str(int(timeout) * 1000)]
        code, out, err = self.herdr(*args)
        if not wait:
            if code != 0:
                return self._status(code, out, err, "herdr agent prompt")
            return {"status": "working", "raw": parse_json(out)}
        return self._status(code, out, err, "herdr agent prompt --wait")

    def wait(self, ident, timeout):
        args = ["agent", "wait", ident]
        if timeout:
            args += ["--timeout", str(int(timeout) * 1000)]
        return self._status(*self.herdr(*args), "herdr agent wait")

    def read(self, ident, lines):
        args = ["agent", "read", ident]
        if lines is not None:
            args += ["--lines", str(lines)]
        code, out, err = self.herdr(*args)
        if code != 0:
            fail_from("herdr agent read", code, out, err)
        return out

    def alive(self, ident):
        return self.herdr("agent", "get", ident)[0] == 0

    def session(self, ident):
        code, out, err = self.herdr("agent", "get", ident)
        data = parse_json(out) if code == 0 else None
        sess = find_key(data, "agent_session") if data is not None else None
        return sess.get("value") if isinstance(sess, dict) else None

    def close(self, ident):
        code, out, err = self.herdr("pane", "close", ident)
        if code != 0:
            fail_from("herdr pane close", code, out, err)
        return True

    def attach_hint(self, ident):
        return f"herdr agent attach {ident}"


# ---------- CLI ----------

def resolve_backend(env):
    both = bool(env.get("HC_TERMINAL_ID")) and env.get("HERDR_ENV") == "1" and bool(env.get("HERDR_PANE_ID"))
    if not both or env.get("MUX_BACKEND"):
        return detect_backend(env)
    hc_pid = None
    if core_running():
        code, out, _ = run(["hc", "get", "--json", env["HC_TERMINAL_ID"]], env=env)
        pid = find_key(parse_json(out), "pid") if code == 0 else None
        hc_pid = pid if isinstance(pid, int) else None
    return detect_backend(env, process_ancestors(), hc_pid, None)


def get_backend(env):
    name = resolve_backend(env)
    if name == "none":
        raise MuxError("no_backend", "不在 herdr 或 Herdr.app 的終端內")
    if name == "hc" and not core_running():
        raise MuxError("core_not_running", "從 Dock 開 Herdr.app")
    return HcBackend(env) if name == "hc" else HerdrBackend(env)


def cmd_env(env):
    name = resolve_backend(env)
    window, extra = False, {}
    if name == "hc" and core_running():
        try:
            window = window_open(env)
        except MuxError as e:  # 判斷不出來不讓整個 env 失敗；spawn 才硬擋
            extra["window_error"] = e.hint
    me = {"hc": env.get("HC_TERMINAL_ID"), "herdr": env.get("HERDR_PANE_ID")}.get(name)
    return {"backend": name, "self": me, "window": window, **extra}


def parse_args(argv):
    p = argparse.ArgumentParser(prog="mux.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("env")
    s = sub.add_parser("spawn")
    s.add_argument("--name", required=True)
    s.add_argument("--kind", required=True, choices=KINDS)
    s.add_argument("--cwd", required=True)
    s.add_argument("--env", action="append", default=[], metavar="K=V")
    s = sub.add_parser("send")
    s.add_argument("id")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--file")
    s.add_argument("--wait", action="store_true")
    s.add_argument("--timeout", type=int)
    s = sub.add_parser("wait")
    s.add_argument("id")
    s.add_argument("--timeout", type=int)
    s = sub.add_parser("read")
    s.add_argument("id")
    s.add_argument("--lines", type=int)
    for n in ("alive", "session", "close", "attach-hint"):
        sub.add_parser(n).add_argument("id")
    rest = []
    if "--" in argv:  # 「--」之後整段是 CLI 參數，不給 argparse 看
        i = argv.index("--")
        argv, rest = argv[:i], argv[i + 1:]
    args = p.parse_args(argv)
    args.cli_args = rest
    return args


def dispatch(args, env):
    if args.cmd == "env":
        return cmd_env(env)
    b = get_backend(env)
    if args.cmd == "spawn":
        pairs = {}
        for item in args.env:
            if "=" not in item:
                raise MuxError("usage", f"--env 要 K=V：{item}", code=2)
            k, v = item.split("=", 1)
            pairs[k] = v
        return b.spawn(args.name, args.kind, args.cwd, pairs, args.cli_args)
    if args.cmd == "send":
        text = args.text if args.text is not None else Path(args.file).read_text(encoding="utf-8")
        return b.send(args.id, text, args.wait, args.timeout)
    if args.cmd == "wait":
        return b.wait(args.id, args.timeout)
    if args.cmd == "read":
        return b.read(args.id, args.lines)
    if args.cmd == "alive":
        return {"alive": b.alive(args.id)}
    if args.cmd == "session":
        sess = b.session(args.id)
        if sess is None and b.name == "hc":
            return {"session": None, "hint": b.session_hint}
        return {"session": sess}
    if args.cmd == "close":
        return {"closed": b.close(args.id)}
    return {"hint": b.attach_hint(args.id)}


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = dispatch(args, dict(os.environ))
    except MuxError as e:
        print(json.dumps({"error": e.kind, "hint": e.hint}, ensure_ascii=False))
        return e.code
    except OSError as e:
        print(json.dumps({"error": "io_error", "hint": str(e)}, ensure_ascii=False))
        return 1
    if args.cmd == "read":
        sys.stdout.write(result)
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
