#!/usr/bin/env python3
"""
FoxPro APP/PRG 檔案解析工具 v2

核心改進：
1. 使用 cp950 解碼（正確支援中文）
2. 先提取 PROCEDURE...ENDPROC 結構化區塊
3. 僅在業務邏輯區塊內提取驗證規則（避免 UI 屬性誤判）
4. 完整提取 MESSAGEBOX 中文訊息
5. 識別 SQL 語句與相關資料表

用法:
    python parse_foxpro.py <file_path> [--output json|markdown|procedures]
    python parse_foxpro.py <file_path> --list           # 列出所有 PROCEDURE
    python parse_foxpro.py <file_path> --proc <name>    # 顯示指定 PROCEDURE 內容

範例:
    python parse_foxpro.py C:\\legacy-app\\ORDERS.APP
    python parse_foxpro.py C:\\legacy-app\\ORDERS.APP --list
    python parse_foxpro.py C:\\legacy-app\\ORDERS.APP --proc CMDSAVE.Click
"""

import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class ProcedureBlock:
    """一個 PROCEDURE...ENDPROC 區塊"""
    name: str
    offset: int
    size: int
    source: str
    category: str = ""  # button_event, validation, business_logic, ui_helper, etc.


@dataclass
class ValidationRule:
    """驗證規則"""
    rule_id: str
    field: str
    rule_type: str  # required, unique, range, sum, conditional_required, delete_restriction
    description: str
    message: str
    procedure: str  # 所屬 PROCEDURE 名稱
    timing: str = ""  # add, edit, delete, save


@dataclass
class SqlOperation:
    """SQL 操作"""
    operation: str  # SELECT, INSERT, UPDATE, DELETE
    table: str
    procedure: str
    context: str = ""  # 摘要


@dataclass
class MessageBoxEntry:
    """MESSAGEBOX 訊息"""
    message: str
    procedure: str
    msg_type: str = ""  # error, warning, info


# ============================================================
# Phase 1: 讀取與結構提取
# ============================================================

def read_binary_file(file_path: str) -> bytes:
    """讀取檔案為 bytes"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"檔案不存在: {file_path}")
    with open(path, 'rb') as f:
        return f.read()


def extract_procedures(raw: bytes) -> List[ProcedureBlock]:
    """從二進位資料中提取所有 PROCEDURE...ENDPROC 區塊"""
    procedures = []
    # 匹配 PROCEDURE <name> 或 PROCEDURE <object>.<event>
    pattern = re.compile(rb'(?i)PROCEDURE\s+([\w.]+)')

    for match in pattern.finditer(raw):
        proc_start = match.start()
        proc_name = match.group(1).decode('ascii', errors='replace')

        # 找到對應的 ENDPROC
        endproc_pos = raw.find(b'ENDPROC', proc_start + len(match.group(0)))
        if endproc_pos < 0 or endproc_pos - proc_start > 50000:
            continue  # 跳過找不到 ENDPROC 或過大的區塊

        block_bytes = raw[proc_start:endproc_pos + 7]  # include "ENDPROC"

        # 用 cp950 解碼
        source = block_bytes.decode('cp950', errors='replace')

        # 清理：移除不可見字元但保留換行
        clean_lines = []
        for line in source.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
            # 過濾掉含有大量亂碼的行（二進位殘留）
            printable_ratio = sum(1 for c in line if c.isprintable() or c in '\t ') / max(len(line), 1)
            if printable_ratio > 0.7 or len(line.strip()) == 0:
                clean_lines.append(line)

        clean_source = '\n'.join(clean_lines)

        # 分類
        category = classify_procedure(proc_name, clean_source)

        procedures.append(ProcedureBlock(
            name=proc_name,
            offset=proc_start,
            size=len(block_bytes),
            source=clean_source,
            category=category,
        ))

    return procedures


def classify_procedure(name: str, source: str) -> str:
    """分類 PROCEDURE"""
    name_lower = name.lower()

    # 按鈕事件
    if any(btn in name_lower for btn in ['cmdsave', 'cmdadd', 'cmdmod', 'cmddel', 'cmdcan',
                                          'cmdprint', 'cmdquery', 'cmdok', 'cmdclose']):
        return 'button_event'

    # 事件方法
    if '.' in name:
        event = name.split('.')[-1].lower()
        if event in ('click', 'init', 'destroy', 'load', 'unload', 'activate',
                      'deactivate', 'interactivechange', 'programmaticchange'):
            return 'form_event'
        if event in ('valid', 'when', 'gotfocus', 'lostfocus'):
            return 'validation'

    # 名稱判斷
    if name_lower in ('valid',):
        return 'validation'
    if any(kw in name_lower for kw in ['check', 'chk', 'verify', 'validate']):
        return 'validation'
    if any(kw in name_lower for kw in ['p_save', 'p_add', 'p_del', 'p_upd', 'p_mod',
                                        'save_data', 'add_data', 'del_data']):
        return 'business_logic'
    if any(kw in name_lower for kw in ['p_gen', 'p_load', 'p_read', 'p_get', 'display',
                                        'refresh', 'requery']):
        return 'data_access'
    if any(kw in name_lower for kw in ['sql_error', 'f_msg', 'check_right', 'onoffbtn']):
        return 'utility'

    # 內容判斷
    source_upper = source.upper()
    if 'MESSAGEBOX' in source_upper and ('EMPTY' in source_upper or 'OPMODE' in source_upper):
        return 'business_logic'

    return 'other'


def read_prg_file(file_path: str) -> List[ProcedureBlock]:
    """讀取 PRG 純文字檔案"""
    path = Path(file_path)
    encodings = ['cp950', 'big5', 'utf-8', 'latin-1']

    content = None
    for encoding in encodings:
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        raise ValueError(f"無法解碼檔案: {file_path}")

    # PRG 整體視為一個程序，但也提取內部 PROCEDURE
    procedures = []

    # 提取 PROCEDURE..ENDPROC 區塊
    proc_pattern = re.compile(r'(?im)^PROCEDURE\s+([\w.]+).*?^ENDPROC', re.DOTALL | re.MULTILINE)
    for match in proc_pattern.finditer(content):
        name = match.group(1)
        source = match.group(0)
        category = classify_procedure(name, source)
        procedures.append(ProcedureBlock(
            name=name, offset=match.start(), size=len(source),
            source=source, category=category,
        ))

    # 如果沒有找到 PROCEDURE，把整個檔案當一個區塊
    if not procedures:
        procedures.append(ProcedureBlock(
            name=path.stem, offset=0, size=len(content),
            source=content, category='main',
        ))

    return procedures


# ============================================================
# Phase 2: 語意分析（僅在業務邏輯區塊內）
# ============================================================

def extract_messagebox_messages(source: str) -> List[str]:
    """提取 MESSAGEBOX 中的訊息文字"""
    messages = []
    # 模式: =MESSAGEBOX('...') 或 MESSAGEBOX("...")
    pattern = re.compile(r"""MESSAGEBOX\s*\(\s*['"]([^'"]+)['"]""", re.IGNORECASE)
    for match in pattern.finditer(source):
        msg = match.group(1).strip()
        if msg and len(msg) > 1 and not msg.startswith('SELECT') and not msg.startswith('INSERT'):
            messages.append(msg)

    # 模式: MESSAGEBOX(變數+字串拼接)
    concat_pattern = re.compile(
        r"""MESSAGEBOX\s*\(\s*['"]([^'"]*)['"]\s*\+""", re.IGNORECASE)
    for match in concat_pattern.finditer(source):
        msg = match.group(1).strip()
        if msg and len(msg) > 1:
            messages.append(msg + "...")

    return messages


def extract_empty_validations(source: str, proc_name: str) -> List[ValidationRule]:
    """從驗證/儲存程序中提取 EMPTY 必填驗證"""
    rules = []
    # 只匹配 IF 條件內的 EMPTY（排除 !EMPTY 用於資料查詢的場景）
    # 模式: IF EMPTY(THISFORM.xxx.VALUE) 後接 MESSAGEBOX
    lines = source.split('\n')

    for i, line in enumerate(lines):
        line_upper = line.upper().strip()

        # 檢查 EMPTY 在 IF 條件中
        empty_match = re.search(
            r'(?i)IF\s+EMPTY\s*\(\s*(?:THISFORM\.)?(\w+(?:\.\w+)*)',
            line)
        if not empty_match:
            continue

        field_path = empty_match.group(1).upper()
        # 提取最後的欄位名（移除 .VALUE 等）
        field_name = field_path.replace('.VALUE', '').split('.')[-1]

        # 排除 UI 屬性和控制欄位
        skip_fields = {'TOOLTIPTEXT', 'STATUSBARTEXT', 'CAPTION', 'NAME',
                       'CONTROLSOURCE', 'ROWSOURCE', 'FORMAT', 'INPUTMASK',
                       'TAG', 'COMMENT', 'BASECLASS', 'CLASS', 'CLASSLIBRARY'}
        if field_name in skip_fields:
            continue

        # 向後搜尋 MESSAGEBOX 提取錯誤訊息
        message = f'請輸入{field_name}'
        for j in range(i + 1, min(i + 8, len(lines))):
            msg_match = re.search(r"""MESSAGEBOX\s*\(\s*['"]([^'"]+)['"]""",
                                  lines[j], re.IGNORECASE)
            if msg_match:
                message = msg_match.group(1)
                break
            if re.match(r'(?i)\s*ENDIF', lines[j]):
                break

        rules.append(ValidationRule(
            rule_id='', field=field_name, rule_type='required',
            description=f'{field_name} 不可為空',
            message=message, procedure=proc_name,
        ))

    return rules


def extract_unique_validations(source: str, proc_name: str) -> List[ValidationRule]:
    """提取唯一性驗證（SEEK 或 SQL 查詢+RECCOUNT 檢查）"""
    rules = []

    # 模式: SEEK(值, 別名)
    seek_pattern = re.compile(r"SEEK\s*\([^,]+,\s*['\"]?(\w+)['\"]?\s*\)", re.IGNORECASE)
    for match in seek_pattern.finditer(source):
        table = match.group(1).upper()
        rules.append(ValidationRule(
            rule_id='', field='', rule_type='unique',
            description=f'在 {table} 中檢查唯一性',
            message='資料已存在', procedure=proc_name,
        ))

    # 模式: SQLEXEC + RECCOUNT > 0 + MESSAGEBOX（常見的 SQL 唯一性檢查）
    sql_unique = re.compile(
        r'(?i)SQLEXEC\s*\([^,]+,\s*["\']([^"\']*SELECT[^"\']*WHERE[^"\']*)["\']',
        re.DOTALL)
    for match in sql_unique.finditer(source):
        sql = match.group(1)
        # 後續有 RECCOUNT > 0 檢查表示唯一性
        pos = match.end()
        context = source[pos:pos + 300]
        if re.search(r'RECCOUNT.*>.*0', context, re.IGNORECASE):
            tables = re.findall(r'FROM\s+(\w+)', sql, re.IGNORECASE)
            for t in tables:
                rules.append(ValidationRule(
                    rule_id='', field='', rule_type='unique',
                    description=f'在 {t.upper()} 中檢查重複',
                    message='資料已存在', procedure=proc_name,
                ))

    return rules


def extract_delete_restrictions(source: str, proc_name: str) -> List[ValidationRule]:
    """提取刪除限制"""
    rules = []

    # 搜尋中文刪除限制訊息
    patterns = [
        r"""MESSAGEBOX\s*\(\s*['"]([^'"]*不[能可]刪除[^'"]*)['"]""",
        r"""MESSAGEBOX\s*\(\s*['"]([^'"]*已存在[^'"]*刪除[^'"]*)['"]""",
        r"""MESSAGEBOX\s*\(\s*['"]([^'"]*cannot\s+delete[^'"]*)['"]""",
    ]

    for pat in patterns:
        for match in re.finditer(pat, source, re.IGNORECASE):
            msg = match.group(1)
            # 嘗試從上下文找到相關表名
            start = max(0, match.start() - 500)
            context = source[start:match.start()]
            tables = re.findall(r'FROM\s+(\w+)', context, re.IGNORECASE)
            table = tables[-1].upper() if tables else '未知'

            rules.append(ValidationRule(
                rule_id='', field='', rule_type='delete_restriction',
                description=f'{table} 有關聯資料時不可刪除',
                message=msg, procedure=proc_name,
                timing='delete',
            ))

    return rules


def extract_sql_operations(source: str, proc_name: str) -> List[SqlOperation]:
    """提取 SQL 操作"""
    operations = []
    seen = set()

    # SELECT
    for match in re.finditer(r'(?i)\bSELECT\b.*?\bFROM\s+(\w+)', source):
        table = match.group(1).upper()
        key = ('SELECT', table)
        if key not in seen and table not in ('CS_XXX', 'CS_CHECK', 'CS_LIST1', 'TMP'):
            seen.add(key)
            operations.append(SqlOperation('SELECT', table, proc_name))

    # INSERT INTO
    for match in re.finditer(r'(?i)\bINSERT\s+INTO\s+(\w+)', source):
        table = match.group(1).upper()
        key = ('INSERT', table)
        if key not in seen:
            seen.add(key)
            operations.append(SqlOperation('INSERT', table, proc_name))

    # UPDATE
    for match in re.finditer(r'(?i)\bUPDATE\s+(\w+)\s+SET\b', source):
        table = match.group(1).upper()
        key = ('UPDATE', table)
        if key not in seen:
            seen.add(key)
            operations.append(SqlOperation('UPDATE', table, proc_name))

    # DELETE FROM
    for match in re.finditer(r'(?i)\bDELETE\s+FROM\s+(\w+)', source):
        table = match.group(1).upper()
        key = ('DELETE', table)
        if key not in seen:
            seen.add(key)
            operations.append(SqlOperation('DELETE', table, proc_name))

    return operations


def extract_form_field_assignments(source: str) -> List[Dict[str, str]]:
    """提取表單欄位賦值（THISFORM.xxx.VALUE = yyy）"""
    fields = []
    seen = set()
    pattern = re.compile(r'(?i)THISFORM\.(\w+)\.VALUE\s*=')
    for match in pattern.finditer(source):
        field = match.group(1).upper()
        if field not in seen:
            seen.add(field)
            fields.append({'field': field})
    return fields


# ============================================================
# Phase 3: 整合分析
# ============================================================

def analyze_foxpro_file(file_path: str) -> Dict[str, Any]:
    """完整分析 FoxPro 檔案"""
    path = Path(file_path)
    raw = read_binary_file(file_path)

    # Phase 1: 提取結構
    if path.suffix.lower() in ('.app', '.scx', '.sct', '.vcx', '.vct'):
        procedures = extract_procedures(raw)
    else:
        procedures = read_prg_file(file_path)

    # Phase 2: 僅對業務相關區塊做語意分析
    business_categories = {'button_event', 'validation', 'business_logic', 'form_event'}
    all_validations: List[ValidationRule] = []
    all_sql_ops: List[SqlOperation] = []
    all_messages: List[MessageBoxEntry] = []
    all_form_fields: List[Dict[str, str]] = []

    rule_counter = 1

    for proc in procedures:
        if proc.category in business_categories or proc.category == 'utility':
            # 提取 MESSAGEBOX 訊息
            for msg in extract_messagebox_messages(proc.source):
                all_messages.append(MessageBoxEntry(
                    message=msg, procedure=proc.name,
                    msg_type='error' if any(kw in msg for kw in ['失敗', '錯誤', '不']) else 'info',
                ))

        if proc.category in business_categories:
            # 提取驗證規則
            for rule in extract_empty_validations(proc.source, proc.name):
                rule.rule_id = f'VR-{rule_counter:03d}'
                all_validations.append(rule)
                rule_counter += 1

            for rule in extract_unique_validations(proc.source, proc.name):
                rule.rule_id = f'VR-{rule_counter:03d}'
                all_validations.append(rule)
                rule_counter += 1

            for rule in extract_delete_restrictions(proc.source, proc.name):
                rule.rule_id = f'VR-{rule_counter:03d}'
                all_validations.append(rule)
                rule_counter += 1

            # 提取 SQL 操作
            all_sql_ops.extend(extract_sql_operations(proc.source, proc.name))

            # 提取表單欄位
            all_form_fields.extend(extract_form_field_assignments(proc.source))

    # 去重表單欄位
    seen_fields = set()
    unique_fields = []
    for f in all_form_fields:
        if f['field'] not in seen_fields:
            seen_fields.add(f['field'])
            unique_fields.append(f)

    # 統整 SQL 表名
    table_summary: Dict[str, Dict[str, int]] = {}
    for op in all_sql_ops:
        if op.table not in table_summary:
            table_summary[op.table] = {}
        table_summary[op.table][op.operation] = table_summary[op.table].get(op.operation, 0) + 1

    # 分類統計
    category_counts = {}
    for proc in procedures:
        cat = proc.category
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        'file': file_path,
        'file_size': len(raw),
        'total_procedures': len(procedures),
        'category_counts': category_counts,
        'procedures': procedures,
        'validations': all_validations,
        'sql_operations': all_sql_ops,
        'table_summary': table_summary,
        'messages': all_messages,
        'form_fields': unique_fields,
    }


# ============================================================
# 輸出格式化
# ============================================================

def format_as_markdown(results: Dict[str, Any]) -> str:
    """格式化為 Markdown 報告"""
    out = []
    file_name = Path(results['file']).stem
    out.append(f"# {file_name} FoxPro 分析報告\n")

    # 1. 基本資訊
    out.append("## 1. 基本資訊\n")
    out.append("| 項目 | 內容 |")
    out.append("|------|------|")
    out.append(f"| 檔案 | `{results['file']}` |")
    out.append(f"| 大小 | {results['file_size']:,} bytes |")
    out.append(f"| 程序數 | {results['total_procedures']} |")

    cats = results['category_counts']
    for cat, count in sorted(cats.items()):
        out.append(f"| {cat} | {count} |")

    # 2. 涉及資料表
    if results['table_summary']:
        out.append("\n## 2. 涉及資料表\n")
        out.append("| 資料表 | 操作類型 |")
        out.append("|--------|----------|")
        for table, ops in sorted(results['table_summary'].items()):
            ops_str = ', '.join(f"{op}({cnt})" for op, cnt in sorted(ops.items()))
            out.append(f"| {table} | {ops_str} |")

    # 3. 驗證規則
    if results['validations']:
        out.append("\n## 3. 驗證規則\n")
        out.append("| 規則編號 | 欄位 | 驗證類型 | 規則描述 | 錯誤訊息 | 所屬程序 |")
        out.append("|----------|------|----------|----------|----------|----------|")
        for v in results['validations']:
            out.append(f"| {v.rule_id} | {v.field} | {v.rule_type} | {v.description} | {v.message} | {v.procedure} |")

    # 4. 錯誤訊息清單
    if results['messages']:
        out.append("\n## 4. 錯誤訊息清單\n")
        out.append("| 訊息 | 類型 | 所屬程序 |")
        out.append("|------|------|----------|")
        seen = set()
        for m in results['messages']:
            if m.message not in seen:
                seen.add(m.message)
                out.append(f"| {m.message} | {m.msg_type} | {m.procedure} |")

    # 5. 表單欄位
    if results['form_fields']:
        out.append("\n## 5. 表單欄位\n")
        out.append("| 欄位名稱 |")
        out.append("|----------|")
        for f in results['form_fields']:
            out.append(f"| {f['field']} |")

    # 6. 主要事件邏輯摘要
    out.append("\n## 6. 主要事件邏輯\n")
    key_procs = [p for p in results['procedures']
                 if p.category in ('button_event', 'business_logic')]
    key_procs.sort(key=lambda p: -p.size)

    for proc in key_procs[:10]:
        out.append(f"### {proc.name} ({proc.size} bytes)\n")
        out.append(f"**分類**: {proc.category}\n")
        # 摘要：前 30 行有意義的程式碼
        lines = [l.strip() for l in proc.source.split('\n')
                 if l.strip() and not l.strip().startswith('*')]
        summary = '\n'.join(lines[:30])
        out.append(f"```foxpro\n{summary}\n```\n")

    return '\n'.join(out)


def format_procedure_list(results: Dict[str, Any]) -> str:
    """列出所有 PROCEDURE"""
    out = []
    out.append(f"# {Path(results['file']).stem} - PROCEDURE 列表\n")
    out.append(f"總計: {results['total_procedures']} 個程序\n")

    # 按分類分組
    by_category: Dict[str, List[ProcedureBlock]] = {}
    for proc in results['procedures']:
        cat = proc.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(proc)

    for cat in sorted(by_category.keys()):
        procs = by_category[cat]
        out.append(f"\n## {cat} ({len(procs)})\n")
        out.append("| 名稱 | 大小 | 偏移量 |")
        out.append("|------|------|--------|")
        for p in sorted(procs, key=lambda x: -x.size):
            out.append(f"| {p.name} | {p.size} | {p.offset} |")

    return '\n'.join(out)


def format_as_json(results: Dict[str, Any]) -> str:
    """格式化為 JSON"""
    serializable = {
        'file': results['file'],
        'file_size': results['file_size'],
        'total_procedures': results['total_procedures'],
        'category_counts': results['category_counts'],
        'procedures': [
            {'name': p.name, 'offset': p.offset, 'size': p.size,
             'category': p.category, 'source': p.source}
            for p in results['procedures']
        ],
        'validations': [asdict(v) for v in results['validations']],
        'table_summary': results['table_summary'],
        'messages': [asdict(m) for m in results['messages']],
        'form_fields': results['form_fields'],
    }
    return json.dumps(serializable, ensure_ascii=False, indent=2)


def show_procedure(results: Dict[str, Any], proc_name: str) -> str:
    """顯示指定 PROCEDURE 的完整內容"""
    for proc in results['procedures']:
        if proc.name.lower() == proc_name.lower():
            return f"# PROCEDURE {proc.name}\n\n**分類**: {proc.category}\n**大小**: {proc.size} bytes\n\n```foxpro\n{proc.source}\n```"

    # 模糊匹配
    matches = [p for p in results['procedures'] if proc_name.lower() in p.name.lower()]
    if matches:
        out = [f"找不到精確匹配 '{proc_name}'，以下為模糊匹配結果：\n"]
        for proc in matches:
            out.append(f"## PROCEDURE {proc.name}\n\n**分類**: {proc.category}\n**大小**: {proc.size} bytes\n\n```foxpro\n{proc.source}\n```\n")
        return '\n'.join(out)

    return f"找不到 PROCEDURE: {proc_name}"


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='FoxPro APP/PRG 檔案解析工具 v2')
    parser.add_argument('file_path', help='FoxPro 檔案路徑')
    parser.add_argument('--output', '-o', choices=['json', 'markdown', 'procedures'],
                        default='markdown', help='輸出格式 (預設: markdown)')
    parser.add_argument('--list', action='store_true', help='列出所有 PROCEDURE')
    parser.add_argument('--proc', type=str, help='顯示指定 PROCEDURE 內容')

    args = parser.parse_args()

    # 強制 stdout 為 utf-8
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    try:
        results = analyze_foxpro_file(args.file_path)

        if args.proc:
            print(show_procedure(results, args.proc))
        elif args.list:
            print(format_procedure_list(results))
        elif args.output == 'json':
            print(format_as_json(results))
        elif args.output == 'procedures':
            print(format_procedure_list(results))
        else:
            print(format_as_markdown(results))

    except FileNotFoundError as e:
        print(f"錯誤: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"分析失敗: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
