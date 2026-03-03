"""Tests for git_safety module - uses mock subprocess, no real git repo needed."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from vibewriting.agents.git_safety import (
    MANAGED_PATHS,
    create_snapshot_commit,
    get_managed_paths,
    has_uncommitted_changes,
    rollback_to_snapshot,
)

REPO_ROOT = Path("/fake/repo")


class TestGetManagedPaths:
    def test_get_managed_paths(self) -> None:
        """验证返回 ["paper/", "output/"]"""
        result = get_managed_paths()
        assert result == ["paper/", "output/"]

    def test_get_managed_paths_returns_copy(self) -> None:
        """验证返回的是副本，不是原始列表引用"""
        result = get_managed_paths()
        result.append("extra/")
        assert get_managed_paths() == ["paper/", "output/"]


class TestHasUncommittedChanges:
    def test_has_uncommitted_changes_true(self) -> None:
        """mock subprocess 返回非空 stdout - 有变更"""
        mock_result = MagicMock()
        mock_result.stdout = " M paper/main.tex\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = has_uncommitted_changes(REPO_ROOT)

        assert result is True

    def test_has_uncommitted_changes_false(self) -> None:
        """mock subprocess 返回空 stdout - 无变更"""
        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = has_uncommitted_changes(REPO_ROOT)

        assert result is False

    def test_has_uncommitted_changes_whitespace_only(self) -> None:
        """mock subprocess 返回仅空白字符 - 视为无变更"""
        mock_result = MagicMock()
        mock_result.stdout = "   \n  "

        with patch("subprocess.run", return_value=mock_result):
            result = has_uncommitted_changes(REPO_ROOT)

        assert result is False

    def test_has_uncommitted_changes_command_args(self) -> None:
        """验证传递的 git 命令参数正确"""
        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            has_uncommitted_changes(REPO_ROOT)

        expected_cmd = [
            "git", "-C", str(REPO_ROOT),
            "status", "--porcelain", "--",
            "paper/", "output/"
        ]
        mock_run.assert_called_once_with(
            expected_cmd,
            capture_output=True,
            text=True,
            check=False,
        )


class TestCreateSnapshotCommit:
    def _make_run_side_effects(
        self,
        diff_returncode: int = 1,
        commit_hash: str = "abc1234567890def",
    ):
        """构造 subprocess.run 的 side_effect 列表。

        调用顺序: add -> diff -> commit -> rev-parse
        diff_returncode=0 表示无变更，=1 表示有变更。
        """
        add_result = MagicMock(returncode=0, stdout="", stderr="")
        diff_result = MagicMock(returncode=diff_returncode, stdout="", stderr="")
        commit_result = MagicMock(returncode=0, stdout="", stderr="")
        hash_result = MagicMock(returncode=0, stdout=commit_hash + "\n", stderr="")
        return [add_result, diff_result, commit_result, hash_result]

    def test_create_snapshot_commit_success(self) -> None:
        """验证 add -> diff -> commit -> rev-parse 调用顺序"""
        side_effects = self._make_run_side_effects(diff_returncode=1)

        with patch("subprocess.run", side_effect=side_effects) as mock_run:
            create_snapshot_commit(REPO_ROOT, "phase5")

        calls = mock_run.call_args_list
        # 第一个调用：git add
        assert "add" in calls[0][0][0]
        # 第二个调用：git diff --cached --quiet
        assert "diff" in calls[1][0][0]
        assert "--cached" in calls[1][0][0]
        # 第三个调用：git commit
        assert "commit" in calls[2][0][0]
        # 第四个调用：git rev-parse
        assert "rev-parse" in calls[3][0][0]

    def test_create_snapshot_commit_nothing_to_commit(self) -> None:
        """mock diff 返回 0（无变更），验证返回空字符串，不调用 commit"""
        side_effects = self._make_run_side_effects(diff_returncode=0)

        with patch("subprocess.run", side_effect=side_effects) as mock_run:
            result = create_snapshot_commit(REPO_ROOT, "phase5")

        assert result == ""
        # 只调用了 add 和 diff，没有 commit 和 rev-parse
        assert mock_run.call_count == 2

    def test_create_snapshot_commit_returns_hash(self) -> None:
        """mock rev-parse 返回 hash，验证函数返回该 hash"""
        expected_hash = "deadbeef1234567890abcdef"
        side_effects = self._make_run_side_effects(
            diff_returncode=1,
            commit_hash=expected_hash,
        )

        with patch("subprocess.run", side_effect=side_effects):
            result = create_snapshot_commit(REPO_ROOT, "phase5")

        assert result == expected_hash

    def test_create_snapshot_commit_message_format(self) -> None:
        """验证 commit 消息格式为 'auto: snapshot before {message}'"""
        side_effects = self._make_run_side_effects(diff_returncode=1)

        with patch("subprocess.run", side_effect=side_effects) as mock_run:
            create_snapshot_commit(REPO_ROOT, "phase5-writing")

        # commit 调用是第三个（index 2）
        commit_call = mock_run.call_args_list[2]
        commit_cmd = commit_call[0][0]
        assert "auto: snapshot before phase5-writing" in commit_cmd

    def test_create_snapshot_commit_add_managed_paths(self) -> None:
        """验证 git add 包含正确的 managed paths"""
        side_effects = self._make_run_side_effects(diff_returncode=1)

        with patch("subprocess.run", side_effect=side_effects) as mock_run:
            create_snapshot_commit(REPO_ROOT, "test")

        add_call = mock_run.call_args_list[0]
        add_cmd = add_call[0][0]
        assert "paper/" in add_cmd
        assert "output/" in add_cmd


class TestRollbackToSnapshot:
    def test_rollback_to_snapshot_calls_subprocess(self) -> None:
        """验证调用了 subprocess.run"""
        mock_result = MagicMock(returncode=0)

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            rollback_to_snapshot(REPO_ROOT, "abc12345")

        assert mock_run.called

    def test_rollback_to_snapshot_command_args(self) -> None:
        """验证 checkout 命令参数正确"""
        commit_hash = "abc1234567890def"
        mock_result = MagicMock(returncode=0)

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            rollback_to_snapshot(REPO_ROOT, commit_hash)

        expected_cmd = [
            "git", "-C", str(REPO_ROOT),
            "checkout", commit_hash, "--",
            "paper/", "output/"
        ]
        mock_run.assert_called_once_with(
            expected_cmd,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_rollback_to_snapshot_uses_check_true(self) -> None:
        """验证使用 check=True，失败时会抛出异常"""
        mock_result = MagicMock(returncode=0)

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            rollback_to_snapshot(REPO_ROOT, "abc12345")

        _, kwargs = mock_run.call_args
        assert kwargs.get("check") is True
