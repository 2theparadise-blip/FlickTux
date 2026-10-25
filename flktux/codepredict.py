#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.codepredict: Ubuntu / Linux / UNIX コマンド ＆ プログラミング言語特化 予測補完エンジン
Supports:
- Linux / UNIX System & CLI Commands (systemctl, apt, git, docker, ip, grep, pipes/redirects)
- Programming Languages (Python, Rust, Bash, JavaScript/TypeScript, C/C++)
- Smart snippet expansion (pairs for brackets, cursor back-step counts)
- Active window auto-detection via xdotool
"""

import re
import subprocess
from typing import List, Tuple, Dict, Optional


# =============================================================================
# 1. Prediction Dictionaries & Snippets
# =============================================================================

# (display_label, insert_text, cursor_back_steps)
# cursor_back_steps: 挿入後にカーソルを左に戻す文字数 (例: () の場合 1)

GENERAL_SNIPPETS: List[Tuple[str, str, int]] = [
    # 挨拶・返答
    ("お疲れ様です", "お疲れ様です", 0),
    ("ありがとうございます", "ありがとうございます", 0),
    ("よろしくお願いします", "よろしくお願いします", 0),
    ("こんにちは", "こんにちは", 0),
    ("了解しました", "了解しました", 0),
    ("承知いたしました", "承知いたしました", 0),
    ("確認します", "確認します", 0),
    ("助かりました", "助かりました", 0),
    ("問題ありません", "問題ありません", 0),
    ("大丈夫です", "大丈夫です", 0),
    ("失礼します", "失礼します", 0),
    ("すみません", "すみません", 0),
    ("ごめんなさい", "ごめんなさい", 0),
    ("どういたしまして", "どういたしまして", 0),
    ("なるほど", "なるほど", 0),
    ("確かに", "確かに", 0),
    # 記号・感嘆
    ("！？", "！？", 0),
    ("…", "…", 0),
    ("〜", "〜", 0),
    ("（笑）", "（笑）", 0),
    ("（汗）", "（汗）", 0),
]

BUSINESS_SNIPPETS: List[Tuple[str, str, int]] = [
    # 書き出し・挨拶
    ("いつもお世話になっております。", "いつもお世話になっております。", 0),
    ("平素は格別のご高配を賜り厚く御礼申し上げます。", "平素は格別のご高配を賜り厚く御礼申し上げます。", 0),
    ("お疲れ様です。", "お疲れ様です。", 0),
    ("ご無沙汰しております。", "ご無沙汰しております。", 0),
    ("突然のご連絡にて失礼いたします。", "突然のご連絡にて失礼いたします。", 0),
    ("拝啓", "拝啓\n\n", 0),
    # 依頼・確認・検討
    ("ご確認いただけますと幸いです。", "ご確認いただけますと幸いです。", 0),
    ("ご査収のほどよろしくお願い申し上げます。", "ご査収のほどよろしくお願い申し上げます。", 0),
    ("ご教示いただけますでしょうか。", "ご教示いただけますでしょうか。", 0),
    ("ご検討のほどよろしくお願いいたします。", "ご検討のほどよろしくお願いいたします。", 0),
    ("ご対応のほどお願い申し上げます。", "ご対応のほどお願い申し上げます。", 0),
    ("何卒よろしくお願い申し上げます。", "何卒よろしくお願い申し上げます。", 0),
    # 連絡・お詫び
    ("取り急ぎご連絡申し上げます。", "取り急ぎご連絡申し上げます。", 0),
    ("取り急ぎご報告まで。", "取り急ぎご報告まで。", 0),
    ("ご不便をおかけして申し訳ございません。", "ご不便をおかけして申し訳ございません。", 0),
    ("ご迷惑をおかけし深くお詫び申し上げます。", "ご迷惑をおかけし深くお詫び申し上げます。", 0),
    ("遅くなり申し訳ございません。", "遅くなり申し訳ございません。", 0),
    # 結び・ビジネス記号
    ("引き続きよろしくお願い申し上げます。", "引き続きよろしくお願い申し上げます。", 0),
    ("敬具", "\n敬具\n", 0),
    ("以上、よろしくお願いいたします。", "以上、よろしくお願いいたします。", 0),
    ("【重要】", "【重要】", 0),
    ("【共有】", "【共有】", 0),
    ("【ご報告】", "【ご報告】", 0),
    ("【相談】", "【相談】", 0),
    ("日時：", "日時：", 0),
    ("場所：", "場所：", 0),
    ("担当：", "担当：", 0),
    ("※", "※ ", 0),
    ("◆", "◆ ", 0),
]

NOVEL_SNIPPETS: List[Tuple[str, str, int]] = [
    # 会話カギ括弧（カーソル内側自動復帰）
    ("「」", "「」", 1),
    ("『』", "『』", 1),
    ("（）", "（）", 1),
    ("【】", "【】", 1),
    ("《》", "《》", 1),
    # 小説作法・約物記号
    ("……", "……", 0),
    ("――", "――", 0),
    ("！　", "！　", 0),
    ("？　", "？　", 0),
    ("！？　", "！？　", 0),
    ("｜", "｜", 0),
    ("　(全角空白)", "　", 0),
    # 台詞・情景スニペット
    ("「――」", "「――」", 1),
    ("「……」", "「……」", 1),
    ("（……）", "（……）", 1),
    ("――その時、", "――その時、", 0),
    ("……ふと、", "……ふと、", 0),
    ("息を呑んだ。", "息を呑んだ。", 0),
    ("静寂が満ちていた。", "静寂が満ちていた。", 0),
]

LINUX_COMMAND_SNIPPETS: List[Tuple[str, str, int]] = [
    # System Administration & Service Management
    ("sudo", "sudo ", 0),
    ("systemctl status", "systemctl status ", 0),
    ("systemctl restart", "systemctl restart ", 0),
    ("systemctl start", "systemctl start ", 0),
    ("systemctl stop", "systemctl stop ", 0),
    ("systemctl enable --now", "systemctl enable --now ", 0),
    ("journalctl -u -f", "journalctl -u  -f", 3),
    ("journalctl -xe", "journalctl -xe", 0),
    ("dmesg -T", "dmesg -T", 0),
    ("ps aux | grep", "ps aux | grep ", 0),
    ("top", "top", 0),
    ("htop", "htop", 0),
    ("kill -9", "kill -9 ", 0),

    # Package Management (APT / DPKG)
    ("sudo apt update", "sudo apt update && sudo apt upgrade -y", 0),
    ("sudo apt install", "sudo apt install -y ", 0),
    ("apt search", "apt search ", 0),
    ("sudo apt remove", "sudo apt remove --purge ", 0),
    ("dpkg -i", "dpkg -i ", 0),
    ("dpkg -l | grep", "dpkg -l | grep ", 0),

    # Git Operations
    ("git status", "git status", 0),
    ("git commit -m \"\"", "git commit -m \"\"", 1),
    ("git add .", "git add .", 0),
    ("git diff", "git diff", 0),
    ("git checkout -b", "git checkout -b ", 0),
    ("git pull", "git pull", 0),
    ("git push origin", "git push origin ", 0),
    ("git log --oneline -n 10", "git log --oneline -n 10", 0),

    # Docker & Containers
    ("docker ps", "docker ps", 0),
    ("docker compose up -d", "docker compose up -d", 0),
    ("docker compose down", "docker compose down", 0),
    ("docker logs -f", "docker logs -f ", 0),
    ("docker exec -it", "docker exec -it  bash", 5),
    ("docker build -t", "docker build -t  .", 2),

    # Network & Transfer
    ("ssh", "ssh ", 0),
    ("curl -sSL", "curl -sSL ", 0),
    ("curl -I", "curl -I ", 0),
    ("ping -c 4", "ping -c 4 ", 0),
    ("ip a", "ip a", 0),
    ("netstat -tuln", "netstat -tuln", 0),
    ("ss -tuln", "ss -tuln", 0),
    ("scp -r", "scp -r ", 0),
    ("wget", "wget ", 0),

    # File & Directory Operations
    ("ls -la", "ls -la", 0),
    ("cd ..", "cd ..", 0),
    ("mkdir -p", "mkdir -p ", 0),
    ("chmod +x", "chmod +x ", 0),
    ("chmod -R 755", "chmod -R 755 ", 0),
    ("chown -R", "chown -R ", 0),
    ("rm -rf", "rm -rf ", 0),
    ("cp -r", "cp -r ", 0),
    ("mv", "mv ", 0),
    ("find . -name \"\"", "find . -name \"\"", 1),
    ("grep -rnI \"\" .", "grep -rnI \"\" .", 3),
    ("tar -zxvf", "tar -zxvf ", 0),
    ("tar -zcvf", "tar -zcvf ", 0),
    ("df -h", "df -h", 0),
    ("du -sh *", "du -sh *", 0),
    ("cat", "cat ", 0),
    ("tail -f", "tail -f ", 0),
    ("head -n 20", "head -n 20 ", 0),

    # Pipes & Redirects
    ("| grep", " | grep ", 0),
    ("| less", " | less", 0),
    ("| head -n", " | head -n ", 0),
    ("| tail -n", " | tail -n ", 0),
    ("| awk '{print $1}'", " | awk '{print $1}'", 0),
    ("| xargs", " | xargs ", 0),
    ("| wc -l", " | wc -l", 0),
    ("| sort | uniq", " | sort | uniq", 0),
    ("2>&1 | tee", " 2>&1 | tee ", 0),
    ("> /dev/null 2>&1", " > /dev/null 2>&1", 0),
    ("&&", " && ", 0),
    ("||", " || ", 0),
]

PYTHON_SNIPPETS: List[Tuple[str, str, int]] = [
    ("def ():", "def ():", 3),
    ("def __init__(self):", "def __init__(self):\n    ", 0),
    ("class :", "class :", 1),
    ("import ", "import ", 0),
    ("from  import ", "from  import ", 8),
    ("print()", "print()", 1),
    ("self.", "self.", 0),
    ("return ", "return ", 0),
    ("if :", "if :", 1),
    ("elif :", "elif :", 1),
    ("else:", "else:\n    ", 0),
    ("for  in :", "for  in :", 5),
    ("while :", "while :", 1),
    ("try:\nexcept Exception as e:", "try:\n    \nexcept Exception as e:\n    ", 28),
    ("with open() as f:", "with open(\"\") as f:\n    ", 11),
    ("True", "True", 0),
    ("False", "False", 0),
    ("None", "None", 0),
    ("len()", "len()", 1),
    ("range()", "range()", 1),
    ("str()", "str()", 1),
    ("int()", "int()", 1),
    ("dict()", "dict()", 1),
    ("list()", "list()", 1),
    ("append()", "append()", 1),
    ("f\"\"", "f\"\"", 1),
    ("==", " == ", 0),
    ("!=", " != ", 0),
    ("->", " -> ", 0),
]

RUST_SNIPPETS: List[Tuple[str, str, int]] = [
    ("fn () -> {}", "fn () -> {\n    \n}", 8),
    ("pub fn ()", "pub fn ()", 1),
    ("let mut ", "let mut ", 0),
    ("let ", "let ", 0),
    ("match  {}", "match  {\n    \n}", 7),
    ("impl  {}", "impl  {\n    \n}", 7),
    ("struct  {}", "struct  {\n    \n}", 7),
    ("enum  {}", "enum  {\n    \n}", 7),
    ("println!()", "println!(\"{}\", );", 4),
    ("eprintln!()", "eprintln!(\"{}\", );", 4),
    ("Some()", "Some()", 1),
    ("None", "None", 0),
    ("Ok()", "Ok()", 1),
    ("Err()", "Err()", 1),
    ("Option<>", "Option<>", 1),
    ("Result<, >", "Result<, >", 3),
    ("Vec::new()", "Vec::new()", 0),
    ("String::from()", "String::from(\"\")", 2),
    ("&str", "&str", 0),
    ("&mut ", "&mut ", 0),
    ("use ", "use ", 0),
    ("pub ", "pub ", 0),
    ("return ", "return ", 0),
    ("=>", " => ", 0),
    ("->", " -> ", 0),
    ("::", "::", 0),
]

BASH_SNIPPETS: List[Tuple[str, str, int]] = [
    ("#!/usr/bin/env bash", "#!/usr/bin/env bash\nset -euo pipefail\n\n", 0),
    ("if [  ]; then", "if [  ]; then\n    \nfi", 12),
    ("for  in ; do", "for  in ; do\n    \ndone", 12),
    ("while [  ]; do", "while [  ]; do\n    \ndone", 13),
    ("echo \"\"", "echo \"\"", 1),
    ("read -r ", "read -r ", 0),
    ("case  in", "case \"$1\" in\n    *)\n        ;;\nesac", 17),
    ("function () {}", "() {\n    \n}", 8),
    ("${}", "${}", 1),
    ("$( )", "$( )", 2),
    ("exit 0", "exit 0", 0),
    ("exit 1", "exit 1", 0),
]

JS_SNIPPETS: List[Tuple[str, str, int]] = [
    ("const ", "const ", 0),
    ("let ", "let ", 0),
    ("function () {}", "function () {\n    \n}", 8),
    ("() => {}", "() => {\n    \n}", 4),
    ("console.log()", "console.log()", 1),
    ("return ", "return ", 0),
    ("async ", "async ", 0),
    ("await ", "await ", 0),
    ("export default ", "export default ", 0),
    ("import  from ''", "import  from '';", 9),
    ("if () {}", "if () {\n    \n}", 8),
    ("try {} catch (e) {}", "try {\n    \n} catch (e) {\n    \n}", 20),
    ("new Promise()", "new Promise((resolve, reject) => {\n    \n})", 4),
    ("===", " === ", 0),
    ("!==", " !== ", 0),
    ("=>", " => ", 0),
]

CPP_SNIPPETS: List[Tuple[str, str, int]] = [
    ("#include <>", "#include <>", 1),
    ("#include \"\"", "#include \"\"", 1),
    ("int main()", "int main(int argc, char *argv[]) {\n    \n    return 0;\n}", 18),
    ("std::cout <<  << std::endl;", "std::cout <<  << std::endl;", 16),
    ("std::vector<>", "std::vector<>", 1),
    ("std::string", "std::string ", 0),
    ("printf(\"\\n\");", "printf(\"\\n\");", 5),
    ("struct  {};", "struct  {\n    \n};", 8),
    ("class  {};", "class  {\npublic:\n    \n};", 8),
    ("nullptr", "nullptr", 0),
    ("->", "->", 0),
    ("::", "::", 0),
]

COMMON_SYMBOLS: List[Tuple[str, str, int]] = [
    ("()", "()", 1),
    ("{}", "{}", 1),
    ("[]", "[]", 1),
    ("\"\"", "\"\"", 1),
    ("''", "''", 1),
    ("==", " == ", 0),
    ("!=", " != ", 0),
    ("->", " -> ", 0),
    ("=>", " => ", 0),
    ("&&", " && ", 0),
    ("||", " || ", 0),
    ("::", "::", 0),
]

PRESET_DICT: Dict[str, List[Tuple[str, str, int]]] = {
    "general": GENERAL_SNIPPETS,
    "business": BUSINESS_SNIPPETS,
    "novel": NOVEL_SNIPPETS,
    "linux": LINUX_COMMAND_SNIPPETS,
    "python": PYTHON_SNIPPETS,
    "rust": RUST_SNIPPETS,
    "bash": BASH_SNIPPETS,
    "javascript": JS_SNIPPETS,
    "cpp": CPP_SNIPPETS,
}


# =============================================================================
# 2. Prediction Engine
# =============================================================================

class CodePredictor:
    """高速プレフィックス検索および言語別スニペット予測エンジン"""

    def __init__(self, mode: str = "general"):
        self.mode = mode
        self.custom_snippets: List[Tuple[str, str, int]] = []

    def set_mode(self, mode: str):
        if mode in PRESET_DICT:
            self.mode = mode

    def get_available_modes(self) -> List[Tuple[str, str]]:
        return [
            ("general", "通常 (日常・SNS)"),
            ("business", "ビジネス文書"),
            ("novel", "小説・創作"),
            ("linux", "Linuxコマンド"),
            ("python", "Python"),
            ("rust", "Rust"),
            ("bash", "Bash"),
            ("javascript", "JavaScript"),
            ("cpp", "C/C++"),
        ]

    def predict(self, prefix: str, max_results: int = 8) -> List[Tuple[str, str, int]]:
        """現在のプレフィックスに一致するスニペット・キーワードをスコアリング順に返す"""
        candidates = PRESET_DICT.get(self.mode, GENERAL_SNIPPETS) + self.custom_snippets

        prefix = prefix.strip()
        if not prefix:
            # プレフィックスなしの場合は頻出上位とシンボルを返す
            defaults = candidates[:max_results - 3] + COMMON_SYMBOLS[:3]
            return defaults[:max_results]

        lower_prefix = prefix.lower()
        exact_matches = []
        prefix_matches = []
        contain_matches = []

        for label, insert, back in candidates:
            lbl_lower = label.lower()
            if lbl_lower == lower_prefix:
                exact_matches.append((label, insert, back))
            elif lbl_lower.startswith(lower_prefix):
                prefix_matches.append((label, insert, back))
            elif lower_prefix in lbl_lower:
                contain_matches.append((label, insert, back))

        # 記号マッチの追加 (例: '=' ➔ '==', '!=')
        for label, insert, back in COMMON_SYMBOLS:
            if lower_prefix in label.lower() and (label, insert, back) not in exact_matches and (label, insert, back) not in prefix_matches:
                contain_matches.append((label, insert, back))

        results = exact_matches + prefix_matches + contain_matches
        seen = set()
        unique_results = []
        for item in results:
            if item[0] not in seen:
                seen.add(item[0])
                unique_results.append(item)
                if len(unique_results) >= max_results:
                    break

        return unique_results


# =============================================================================
# 3. Active Window Detection (xdotool)
# =============================================================================

def detect_active_window_mode() -> str:
    """現在アクティブなウィンドウ名・クラスから最適な入力予測モードを自動推定"""
    try:
        out = subprocess.check_output(
            ["xdotool", "getactivewindow", "getwindowname"],
            text=True,
            timeout=0.1
        ).strip().lower()

        # 1. ターミナルアプリ検知
        term_patterns = ["terminal", "bash", "tmux", "zsh", "alacritty", "kitty", "tilix", "konsole", "xterm"]
        if any(p in out for p in term_patterns):
            return "linux"

        # 2. 小説・創作系・テキストエディタ
        if any(w in out for w in ["novel", "小説", "シナリオ", "writer", "原稿"]):
            return "novel"

        # 3. ビジネス文書・オフィス
        if any(w in out for w in ["mail", "メール", "calc", "excel", "thunderbird", "slack", "chat"]):
            return "business"

        # 4. プログラミングファイル拡張子検知 (VS Code, Vim, Gedit, etc.)
        if re.search(r'\.(py|pyw)(\s|$|—|-)', out):
            return "python"
        elif re.search(r'\.(rs)(\s|$|—|-)', out):
            return "rust"
        elif re.search(r'\.(sh|bash|zsh)(\s|$|—|-)', out):
            return "bash"
        elif re.search(r'\.(js|ts|jsx|tsx|json|html|css)(\s|$|—|-)', out):
            return "javascript"
        elif re.search(r'\.(c|cpp|cc|cxx|h|hpp)(\s|$|—|-)', out):
            return "cpp"

    except Exception:
        pass

    return "general"
