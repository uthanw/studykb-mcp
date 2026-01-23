"""Pytest fixtures for tests."""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from studykb_mcp.models.progress import ProgressEntry, ProgressFile


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def sample_kb(temp_dir):
    """Create a sample knowledge base structure."""
    kb_path = temp_dir / "kb"
    kb_path.mkdir()

    # Create category: 数据结构
    ds_path = kb_path / "数据结构"
    ds_path.mkdir()

    # Create material file
    material_content = """# 数据结构教材

## 第1章 绪论

数据结构是计算机科学的基础课程。

### 1.1 基本概念

数据结构（Data Structure）是指相互之间存在一种或多种特定关系的数据元素的集合。

### 1.2 算法

算法是解决问题的一系列步骤。

## 第2章 线性表

线性表是最基本的数据结构之一。

### 2.1 顺序表

顺序表使用连续内存存储元素。

### 2.2 链表

链表使用指针链接元素。

## 第3章 树

树是一种层次结构。

### 3.1 二叉树

二叉树每个节点最多有两个子节点。

### 3.2 二叉搜索树

二叉搜索树支持高效的查找操作。

Kruskal算法是最小生成树算法之一。

Prim算法也是最小生成树算法。
"""
    (ds_path / "数据结构教材.md").write_text(material_content, encoding="utf-8")

    # Create index file
    index_content = """# 数据结构教材索引

## 章节结构

| 章节 | 行号范围 |
|------|---------|
| 第1章 绪论 | 3-14 |
| 第2章 线性表 | 16-26 |
| 第3章 树 | 28-38 |

## 知识点索引

| 知识点 | 行号 |
|-------|------|
| Kruskal算法 | 36 |
| Prim算法 | 38 |
"""
    (ds_path / "数据结构教材_index.md").write_text(index_content, encoding="utf-8")

    # Create another material without index
    (ds_path / "算法笔记.md").write_text("# 算法笔记\n\n一些算法笔记内容。\n" * 10, encoding="utf-8")

    # Create another category: 计算机组成原理
    co_path = kb_path / "计算机组成原理"
    co_path.mkdir()
    (co_path / "计组教材.md").write_text("# 计算机组成原理\n\n内容...\n" * 5, encoding="utf-8")

    return kb_path


@pytest.fixture
def sample_progress(temp_dir):
    """Create a sample progress directory."""
    progress_path = temp_dir / "progress"
    progress_path.mkdir()

    # Create progress file for 数据结构
    now = datetime.now()
    progress = ProgressFile(
        category="数据结构",
        last_updated=now,
        entries={
            "ds.linear.array": ProgressEntry(
                name="顺序表",
                status="done",
                comment="基础内容，已掌握",
                updated_at=now - timedelta(days=10),
                mastered_at=now - timedelta(days=10),
                review_count=1,
                next_review_at=now - timedelta(days=3),  # Overdue for review
            ),
            "ds.linear.linked_list": ProgressEntry(
                name="链表",
                status="active",
                comment="正在学习单链表",
                updated_at=now - timedelta(hours=2),
            ),
            "ds.tree.binary": ProgressEntry(
                name="二叉树",
                status="done",
                comment="遍历方法都会了",
                updated_at=now - timedelta(days=5),
                mastered_at=now - timedelta(days=5),
                review_count=0,
                next_review_at=now + timedelta(days=2),  # Not yet due
            ),
            "ds.graph.mst.kruskal": ProgressEntry(
                name="Kruskal算法",
                status="pending",
                comment="待学习",
                updated_at=now - timedelta(days=1),
            ),
        },
    )

    import json

    (progress_path / "数据结构.json").write_text(
        progress.model_dump_json(indent=2), encoding="utf-8"
    )

    return progress_path


@pytest.fixture
def empty_kb(temp_dir):
    """Create an empty knowledge base."""
    kb_path = temp_dir / "kb"
    kb_path.mkdir()
    return kb_path


@pytest.fixture
def empty_progress(temp_dir):
    """Create an empty progress directory."""
    progress_path = temp_dir / "progress"
    progress_path.mkdir()
    return progress_path
