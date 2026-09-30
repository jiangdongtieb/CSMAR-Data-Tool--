# CSMAR 数据接入工具

国泰安（CSMAR）数据库 Python API 数据下载工具，支持列出已购数据库、数据表、字段，以及按条件查询并导出 CSV/Excel。

## 文件说明

| 文件 | 说明 |
|------|------|
| `CSMAR数据下载工具.py` | 主程序，命令行工具 |
| `CSMAR账号密码.txt` | 凭据模板，**使用前请替换为你自己的账号密码**（第1行账号，第2行密码） |

## 环境要求

- Windows 系统（CSMAR 官方 Python 库仅支持 Windows）
- Python 3.6+
- 依赖库：`csmarapi`（官方库）、`pandas`、`urllib3`、`websocket-client`、`prettytable`

## 使用方法

1. 编辑 `CSMAR账号密码.txt`，填入你的 CSMAR 账号和密码
2. 命令行运行：

```bash
# 列出所有已购数据库
python CSMAR数据下载工具.py --dbs

# 列出某数据库下的数据表
python CSMAR数据下载工具.py --tables "财务报表"

# 列出某数据表的字段
python CSMAR数据下载工具.py --fields "FS_Combas"

# 按脚本内 QUERY_CONFIG 配置执行查询并导出
python CSMAR数据下载工具.py --query

# 查询结果导出为 Excel
python CSMAR数据下载工具.py --query --fmt excel
```

## 自定义查询

编辑 `CSMAR数据下载工具.py` 中的 `QUERY_CONFIG`：

```python
QUERY_CONFIG = {
    "table": "TRD_Dalyr",              # 数据表名
    "columns": ["Stkcd", "Trddt", "Dretwd"],  # 需要的字段
    "condition": "Stkcd like '6%' limit 0, 5000",  # 查询条件
    "start": "2023-01-01",             # 开始日期
    "end": "2023-12-31",               # 结束日期
    "output_name": "CSMAR_query_result",  # 输出文件名
}
```

## 注意事项

- 单次查询最多返回 200,000 条记录，超过时脚本会提示分页
- 同一查询条件 30 分钟内只能执行一次，命中冷却会自动提示
- 查询结果默认保存到脚本同目录的 `output` 文件夹
