"""Prompt editing and contextual completion for the AnY terminal."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, cast

from rich.cells import cell_len
from rich.text import Text
from textual import on
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import OptionList, Static, TextArea
from textual.widgets.option_list import Option


def plain(value):
    return "".join(c for c in str(value) if c in "\n\t" or (ord(c) >= 32 and not 127 <= ord(c) <= 159))


@dataclass(frozen=True)
class Command:
    description: str
    arguments: str = ""
    optional: bool = False


COMMANDS = {
    "new": Command("新建会话"),
    "resume": Command("搜索并切换会话"),
    "model": Command("选择成员的模型和思考强度", "[成员 [模型 [强度]]]", optional=True),
    "debate": Command("开启论道，设置议题和参辩成员", "[议题]", optional=True),
    "debate-continue": Command("补充意见，继续上一场论道", "[补充意见]", optional=True),
    "debate-finish": Command("结束轮流发言并请主持人总结"),
    "mode": Command("切换讨论或干活模式", "discuss|work"),
    "status": Command("查看目录、成员和执行状态"),
    "stop": Command("停止当前回复", "[成员]", optional=True),
    "compact": Command("压缩成员上下文", "[成员]", optional=True),
    "agents": Command("查看已配置的联系人"),
    "scan": Command("查找本机 CLI / ACP Harness"),
    "connect": Command("接入并检查本机 Harness", "成员 cli|acp"),
    "invite": Command("将联系人加入当前会话", "成员"),
    "handoff": Command("交给 Harness 的原生终端", "成员"),
    "return": Command("从原生终端收回会话", "成员"),
    "project": Command("新建项目"),
    "announce": Command("更新或清空会议目标", "[目标]", optional=True),
    "todo": Command("添加看板待办", "内容"),
    "done": Command("完成看板待办", "编号"),
    "help": Command("查看键盘操作和命令"),
    "quit": Command("退出终端客户端"),
}


@dataclass(frozen=True)
class Completion:
    label: str
    hint: str
    value: str
    execute: bool = False
    cursor: int | None = None


class Prompt(TextArea):
    BINDINGS = [
        Binding("enter", "send", show=False, priority=True),
        Binding("shift+enter,alt+enter,ctrl+j", "newline", show=False, priority=True),
        Binding("tab", "complete", show=False, priority=True),
        Binding("escape", "dismiss_completion", show=False, priority=True),
    ]

    @property
    def composer(self) -> Composer:
        return cast(Composer, self.parent)

    def check_action(self, action, parameters):
        if action in ("complete", "dismiss_completion"):
            # A hidden menu gives Tab back to Textual's ordinary focus navigation.
            return self.composer.menu.display
        return super().check_action(action, parameters)

    def action_send(self):
        self.composer.accept_or_send()

    def action_newline(self):
        start, end = self.selection
        self.replace("\n", start, end)

    def action_complete(self):
        self.composer.accept_completion(execute=False)

    def action_dismiss_completion(self):
        self.composer.hide_completion()

    def action_cursor_up(self, select=False):
        if not select and self.composer.navigate(-1):
            return
        super().action_cursor_up(select)

    def action_cursor_down(self, select=False):
        if not select and self.composer.navigate(1):
            return
        super().action_cursor_down(select)

    def action_cursor_left(self, select=False):
        if not select and not self.text and not self.composer.menu.display:
            app = cast(Any, self.app)
            if hasattr(app, "action_switch_to_rooms"):
                app.action_switch_to_rooms()
                return
        super().action_cursor_left(select)


class Composer(Vertical):
    class Submitted(Message):
        def __init__(self, text):
            super().__init__()
            self.text = text

    def __init__(self, complete_argument):
        super().__init__(id="composer")
        self.complete_argument = complete_argument
        self.suggestions: list[Completion] = []
        self.menu_state = None
        self.dismissed = None
        self.history: list[str] = []
        self.history_index = None
        self.before_recall = ""
        self.recalled = None

    @property
    def prompt(self):
        return self.query_one(Prompt)

    @property
    def menu(self):
        return self.query_one(OptionList)

    def compose(self):
        yield OptionList(id="completion", compact=True)
        yield Prompt(id="message", placeholder="输入消息 · / 命令 · @ 成员", highlight_cursor_line=False)
        yield Static("Enter 发送  ·  Shift+Enter 换行  ·  / 命令  ·  @ 成员  ·  F3 看板", id="prompt-hint", markup=False)

    def on_mount(self):
        self.menu.display = False
        self.menu.can_focus = False

    def set_text(self, value, cursor=None):
        self.prompt.load_text(value)
        self.move_cursor(value, cursor)

    def move_cursor(self, value, cursor=None):
        lines = value[:cursor].split("\n")
        self.prompt.move_cursor((len(lines) - 1, len(lines[-1])))
        self.refresh_completion()

    def set_history(self, prompts):
        self.history = prompts
        self.history_index = None
        self.recalled = None

    def hide_completion(self):
        self.dismissed = (self.prompt.text, self.prompt.cursor_location)
        self.refresh_completion()

    @on(TextArea.Changed)
    def prompt_changed(self):
        self.prompt.styles.height = min(8, self.prompt.document.line_count + 2)
        if self.prompt.text != self.recalled:
            self.history_index = None
        self.refresh_completion()

    @on(TextArea.SelectionChanged)
    def refresh_completion(self):
        prompt = self.prompt
        row, column = prompt.cursor_location
        position = sum(len(line) + 1 for line in prompt.text.split("\n")[:row]) + column
        key = (prompt.text, prompt.cursor_location)
        if key != self.dismissed:
            self.dismissed = None
        suggestions = self.matches(prompt.text, position) if key != self.dismissed and not prompt.selected_text else []
        if self.menu_state == (key, suggestions):
            return
        self.menu_state = (key, suggestions)
        self.suggestions = suggestions
        width = min(24, max((cell_len(item.label) for item in suggestions), default=0))
        options = []
        for item in suggestions:
            label = plain(item.label)
            gap = " " * (max(0, width - cell_len(label)) + 2)
            options.append(Option(Text.assemble((label, "bold"), (gap + plain(item.hint), "dim"))))
        self.menu.set_options(options)
        self.menu.highlighted = 0 if suggestions else None
        self.size_completion_menu()
        self.menu.display = bool(suggestions)
        self.query_one("#prompt-hint", Static).update(
            "↑↓ 选择  ·  Tab 补全  ·  Enter 确认  ·  Esc 收起" if suggestions
            else "Enter 发送  ·  Shift+Enter 换行  ·  / 命令  ·  @ 成员  ·  F3 看板"
        )

    def size_completion_menu(self):
        self.menu.styles.height = min(7, max(2, self.app.size.height // 4), len(self.suggestions)) + 2

    def matches(self, value, position):
        if value.startswith("/") and not value.startswith("//"):
            if "\n" in value or position != len(value):
                return []
            name, space, argument = value[1:].partition(" ")
            if not space:
                name = name.lower()
                matched = sorted((key for key in COMMANDS if key.startswith(name)), key=lambda key: key != name)
                return [Completion(f"/{key}", COMMANDS[key].description,
                                   f"/{key}" + (" " if COMMANDS[key].arguments else ""),
                                   not COMMANDS[key].arguments or (key == name and COMMANDS[key].optional))
                        for key in matched]
            if name.lower() in COMMANDS:
                return self.complete_argument(name.lower(), argument)
            return []
        mention = re.search(r"(?<![\w@])@([\w-]*)$", value[:position])
        if mention:
            suffix = re.match(r"[\w-]+", value[position:])
            end = position + (len(suffix[0]) if suffix else 0)
            candidates = []
            for member, label in self.complete_argument("@", mention[1]):
                prefix = value[:mention.start()] + "@" + member
                if not value[end:end + 1].isspace():
                    prefix += " "
                candidates.append(Completion("@" + member, label, prefix + value[end:], cursor=len(prefix)))
            return candidates
        return []

    def navigate(self, direction):
        if self.menu.display:
            if direction < 0:
                self.menu.action_cursor_up()
            else:
                self.menu.action_cursor_down()
            return True
        cursor = self.prompt.cursor_location
        navigator = self.prompt.navigator
        at_boundary = navigator.is_first_wrapped_line(cursor) if direction < 0 else navigator.is_last_wrapped_line(cursor)
        if not at_boundary:
            return False
        if not self.history or (self.history_index is None and direction > 0):
            return False
        if self.history_index is None:
            self.before_recall = self.prompt.text
            self.history_index = len(self.history)
        target = min(len(self.history), max(0, self.history_index + direction))
        self.history_index = target
        self.recalled = self.before_recall if target == len(self.history) else self.history[target]
        self.set_text(self.recalled)
        return True

    def accept_or_send(self):
        if self.menu.display:
            self.accept_completion(execute=True)
        elif self.prompt.text.strip():
            self.post_message(self.Submitted(self.prompt.text))

    def accept_completion(self, *, execute):
        index = self.menu.highlighted
        if index is None or index >= len(self.suggestions):
            return
        selected = self.suggestions[index]
        self.prompt.replace(selected.value, (0, 0), self.prompt.document.end)
        self.move_cursor(selected.value, selected.cursor)
        if execute and selected.execute:
            self.post_message(self.Submitted(selected.value))

    @on(OptionList.OptionSelected, "#completion")
    def select_completion(self):
        self.accept_completion(execute=True)
        self.prompt.focus()
