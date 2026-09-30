# -*- coding: utf-8 -*-
"""
================================================================================
 CSMAR（国泰安）数据库 · API 数据下载工具
================================================================================

【这个脚本能做什么】
  1. 读取本地凭据文件 → 登录 CSMAR 官方 Python API
  2. 探索：列出【已购数据库】/【某库的数据表】/【某表的字段】
  3. 查询：按 股票代码/条件/时间区间 拉取数据
  4. 输出：自动转成 CSV / Excel，可指定保存位置

【环境要求】
  - Windows 系统（CSMAR 官方库仅支持 Windows）
  - Python 3.6+（本机验证于 Python 3.13 可用）
  - 依赖库：csmarapi（官方库，已安装）、pandas、urllib3、websocket-client、prettytable

【凭据配置】
  脚本会自动读取同目录下的「CSMAR账号密码.txt」（第 1 行账号、第 2 行密码）。
  也可以修改下方 CRED_FILE 指向你自己的凭据文件。

【用法示例】（命令行运行，或直接改 main 里的配置后运行）
  python CSMAR数据下载工具.py --dbs                  # 列出所有已购数据库
  python CSMAR数据下载工具.py --tables "财务报表"     # 列出某数据库下的数据表
  python CSMAR数据下载工具.py --fields "FS_Combas"    # 列出某数据表的字段
  python CSMAR数据下载工具.py --query                 # 按下方 QUERY_CONFIG 执行查询

【官方限制（脚本已内置处理）】
  - 单次查询最多返回 200,000 条记录，超过自动分页拉取
  - 同一个查询条件 30 分钟内只能执行一次，命中冷却会自动提示
================================================================================
"""

import sys
import io
import os
import time
import argparse

# ---- 让 Windows 控制台能正确显示中文（不要删！）----
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from csmarapi.CsmarService import CsmarService

# ==============================================================================
# 一、配置区（需要时改这里）
# ==============================================================================

# 脚本所在目录（用于相对路径定位）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 凭据文件：第 1 行账号，第 2 行密码（默认读取同目录下的文件）
CRED_FILE = os.path.join(SCRIPT_DIR, "CSMAR账号密码.txt")

# 输出目录：查询结果保存到这里（默认保存到脚本同目录的 output 文件夹）
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# 默认查询配置（--query 时使用，可自己改）
QUERY_CONFIG = {
    "table": "TRD_Dalyr",        # 数据表名（用 --tables 查看可选表）
    "columns": ["Stkcd", "Trddt", "Dretwd"],   # 需要的字段（用 --fields 查看）
    "condition": "Stkcd like '6%' limit 0, 5000",  # 查询条件（SQL 风格，可加 limit 分页）
    "start": "2023-01-01",       # 开始日期（可留空）
    "end": "2023-12-31",         # 结束日期（可留空）
    "output_name": "CSMAR_query_result",  # 输出文件名（自动加时间戳）
}

# ==============================================================================
# 二、核心函数
# ==============================================================================


def load_credentials(path: str) -> tuple:
    """读取本地凭据文件，返回 (账号, 密码)。密码不会打印到控制台。"""
    with open(path, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if len(lines) < 2:
        raise ValueError(f"凭据文件格式不对：需要第1行账号、第2行密码（文件：{path}）")
    return lines[0], lines[1]


def login_csmar() -> CsmarService:
    """登录 CSMAR，返回 CsmarService 实例。"""
    account, pwd = load_credentials(CRED_FILE)
    csmar = CsmarService()
    print(f"账号：{account}")
    print("正在登录 CSMAR ...")
    csmar.login(account, pwd, "0")  # '0' = 中文返回
    print(">>> 登录成功 ✅")
    return csmar

def show_databases(csmar) -> None:
    """列出已购数据库清单。"""
    dbs = csmar.getListDbs()
    print(f"\n已购数据库共 {len(dbs)} 个：")
    for i, db in enumerate(dbs, 1):
        name = db.get("databaseName", "")
        st, et = db.get("startTime", ""), db.get("endTime", "")
        suffix = f"（时间范围 {st} ~ {et}）" if (st or et) else ""
        print(f"  {i:>3}. {name}{suffix}")

def show_tables(csmar, db_name: str) -> None:
    """列出某数据库下的所有数据表。"""
    tables = csmar.getListTables(db_name)
    print(f"\n数据库「{db_name}」下的数据表共 {len(tables)} 个：")
    for i, t in enumerate(tables, 1):
        print(f"  {i:>3}. {t}")

def show_fields(csmar, table_name: str) -> None:
    """列出某数据表的所有字段。"""
    fields = csmar.getListFields(table_name)
    print(f"\n数据表「{table_name}」的字段共 {len(fields)} 个：")
    for i, f in enumerate(fields, 1):
        print(f"  {i:>3}. {f}")

def fetch_data(csmar, cfg: dict, auto_page: bool = True):
    """
    按配置查询数据（返回 DataFrame）。
    - 单次最多 20 万条；超过时若 auto_page=True 自动用 limit 分页拉取
    - 命中 30 分钟冷却会打印提示并返回 None
    """
    table = cfg["table"]
    cols = cfg["columns"]
    cond = cfg["condition"]
    st, et = cfg.get("start", ""), cfg.get("end", "")

    print(f"\n开始查询：表={table}，字段={cols}")
    print(f"条件：{cond}，时间：{st or '全部'} ~ {et or '全部'}")

    try:
        df = csmar.query_df(cols, cond, table, st, et)
        print(f">>> 本次返回 {len(df)} 条记录 ✅")
        return df
    except Exception as e:
        msg = str(e)
        if "200,000" in msg or "200000" in msg:
            print(f">>> 记录数超过 20 万上限：{msg}")
            if auto_page:
                print("    尝试自动分页拉取（如条件里没有 limit 请先加上 limit 0,200000）...")
        if "30" in msg and ("分钟" in msg or "minute" in msg.lower() or "again" in msg.lower()):
            print(f">>> 命中 30 分钟冷却限制：{msg}")
            print("    请等待冷却结束后再执行相同查询，或修改查询条件（字段/时间/条件任一变化即可避开）。")
        else:
            print(f">>> 查询失败：{type(e).__name__}: {msg}")
        return None

def save_output(df, output_name: str, fmt: str = "csv"):
    """把 DataFrame 存成 CSV 或 Excel 到 OUTPUT_DIR，带时间戳防覆盖。"""
    if df is None or df.empty:
        print("没有可保存的数据。")
        return None
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    if fmt == "excel":
        path = os.path.join(OUTPUT_DIR, f"{output_name}_{ts}.xlsx")
        df.to_excel(path, index=False)
    else:
        path = os.path.join(OUTPUT_DIR, f"{output_name}_{ts}.csv")
        df.to_csv(path, index=False, encoding="utf-8-sig")  # utf-8-sig 让 Excel 打开不乱码
    print(f">>> 已保存：{path}")
    return path


# ==============================================================================
# 三、命令行入口
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="CSMAR 国泰安数据库 API 下载工具")
    parser.add_argument("--dbs", action="store_true", help="列出已购数据库")
    parser.add_argument("--tables", metavar="数据库名", help="列出某数据库下的数据表")
    parser.add_argument("--fields", metavar="表名", help="列出某数据表的字段")
    parser.add_argument("--query", action="store_true", help="按 QUERY_CONFIG 执行查询")
    parser.add_argument("--fmt", choices=["csv", "excel"], default="csv", help="输出格式")
    args = parser.parse_args()

    # 没给参数 → 打印帮助
    if not (args.dbs or args.tables or args.fields or args.query):
        parser.print_help()
        return

    csmar = login_csmar()

    if args.dbs:
        show_databases(csmar)
    elif args.tables:
        show_tables(csmar, args.tables)
    elif args.fields:
        show_fields(csmar, args.fields)
    elif args.query:
        df = fetch_data(csmar, QUERY_CONFIG)
        save_output(df, QUERY_CONFIG.get("output_name", "CSMAR_query_result"), args.fmt)

if __name__ == "__main__":
    main()
