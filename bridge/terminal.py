"""Interactive terminal interface for the shared AnY backend."""
import asyncio
import os
import re
import secrets
from contextlib import suppress
from typing import Any

from rich.cells import cell_len, get_character_cell_size
from rich.console import Group, Measurement
from rich.markdown import Markdown
from rich.padding import Padding
from rich.rule import Rule
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, HorizontalScroll, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, RichLog, Select, SelectionList, Static
from textual.widgets.option_list import Option

from . import cli_updater
from .cli import CliError, room_path
from .terminal_brand import (
    AGENT_FALLBACKS, CORAL, GOLD, INK, MINT, MUTED_TEXT,
    PAPER, RAISED, RED, SILVER, TERMINAL_THEME, Splash, WelcomeMark, splash_enabled,
)
from .terminal_input import COMMANDS, Completion, Composer, composer_mention, plain
from .version import CLI_VERSION


CLI_VIAS = ("cli", "codex", "claude")


def motion_enabled(app):
    return not app.no_color and app.animation_level != "none"


def readable_agent_color(raw_color, index=0):
    if re.fullmatch(r"#[0-9a-fA-F]{6}", raw_color or ""):
        r, g, b = int(raw_color[1:3], 16), int(raw_color[3:5], 16), int(raw_color[5:7], 16)
        # Keep colors with sufficient contrast on #0b0e13; brighten overly dark presets (e.g. #111827).
        if (0.299 * r + 0.587 * g + 0.114 * b) >= 85:
            return raw_color
    return AGENT_FALLBACKS[index % len(AGENT_FALLBACKS)]


def agent_colors(state):
    return {
        agent["id"]: readable_agent_color(agent.get("color"), idx)
        for idx, agent in enumerate(state.get("agents", []))
    }


def _message_body_items(message, *, markdown=False):
    items: list[Any] = []
    if reply := message.get("reply_to"):
        items.append(Text(f"↳ {plain(reply.get('speaker', ''))}：{plain(reply.get('text', ''))}", style=f"dim {MUTED_TEXT}"))
    if message.get("recalled"):
        items.append(Text("消息已撤回", style=f"dim {MUTED_TEXT}"))
    elif text := message.get("text"):
        items.append(Markdown(plain(text), hyperlinks=False, code_theme="github-dark") if markdown else Text(plain(text), style=PAPER))
    for attachment in message.get("attachments", []):
        items.append(Text("📎 " + plain(attachment.get("name", "文件")), style=f"bold {SILVER}"))
    return items


class Barred:
    """Render a child with a vertical bar prefix on every line, optionally over a background."""

    def __init__(self, renderable, prefix="▌ ", style=SILVER, *, bg=None):
        self.renderable = renderable
        self.prefix = prefix
        self.style = style
        self.bg = bg

    def __rich_console__(self, console, options):
        width = max(4, options.max_width - cell_len(self.prefix))
        lines = console.render_lines(self.renderable, options.update(width=width), pad=False)
        bar = Segment(self.prefix, Style.parse(self.style))
        bg = Style(bgcolor=self.bg) if self.bg else None
        newline = Segment.line()
        for line in lines:
            yield bar
            used = 0
            for seg in line:
                used += cell_len(seg.text)
                if bg is not None:
                    yield Segment(seg.text, (seg.style or Style()) + bg)
                else:
                    yield seg
            if bg is not None and used < width:
                yield Segment(" " * (width - used), bg)
            yield newline

    def __rich_measure__(self, console, options):
        measurement = Measurement.get(console, options, self.renderable)
        extra = cell_len(self.prefix)
        return Measurement(measurement.minimum + extra, measurement.maximum + extra)


def transcript_entry(message, agents, colors, members):
    speaker = message["speaker"]
    agent = agents.get(speaker, {})
    name = plain(agent.get("label") or speaker)
    time_str = plain(message.get("time") or "")
    if speaker == "系统":
        text = plain(message.get("text") or "系统通知")
        if "\n" not in text and len(text) <= 44 and not message.get("attachments") and not message.get("reply_to"):
            return Padding(Rule(f" ─ 系统 · {text} ", style=f"dim {MUTED_TEXT}", characters="─"), (0, 2, 1, 2))
        body_items = _message_body_items(message, markdown=False)
        header = Text.assemble(("─ 系统", f"bold {MUTED_TEXT}"), (f"  {time_str}" if time_str else "", f"dim {MUTED_TEXT}"))
        return Padding(Group(header, *(Padding(item, (0, 0, 0, 2)) for item in body_items)), (0, 2, 1, 2))

    is_human = agent.get("kind") == "user" or members.get(speaker, {}).get("transport") == "human"
    body_items = _message_body_items(message, markdown=(speaker != "你" and not is_human))
    content = Group(*body_items) if body_items else Text("")

    if speaker == "你" or is_human:
        marker = "◆ 你" if speaker == "你" else f"○ {name} · 成员"
        header = Text(marker, style=f"bold {SILVER}")
        if time_str:
            header.append(f"  {time_str}", style=f"dim {MUTED_TEXT}")
        bar_style = SILVER if speaker == "你" else MUTED_TEXT
        block = Barred(Group(header, content), prefix="▌ ", style=bar_style, bg=RAISED)
        return Padding(block, (0, 0, 1, 0))

    color = colors.get(speaker) or GOLD
    header = Text.assemble((f"● {name}", f"bold {color}"), (" · AI", f"dim {GOLD}"))
    if name.casefold() != speaker.casefold():
        header.append(f"  @{plain(speaker)}", style=f"dim {MUTED_TEXT}")
    if message.get("origin") == "debate-summary":
        header.append("  论道总结", style=f"bold {GOLD}")
    elif message.get("to_user"):
        header.append("  → 用户", style=f"bold {SILVER}")
    if time_str:
        header.append(f"  {time_str}", style=f"dim {MUTED_TEXT}")
    return Padding(Group(header, Padding(content, (0, 0, 0, 2))), (0, 0, 1, 0))


def append_details_header(details, title, bg_color, count=None, right_note="", *, first=False):
    if not first:
        details.append("\n\n")
    details.append(title, style=f"bold {bg_color}")
    if count is not None:
        details.append(f"  {count}", style=f"dim {bg_color}")
    elif right_note:
        details.append(f"  {right_note}", style=f"dim {bg_color}")
    details.append("\n")


def _wrap_cells(text, first_width, rest_width):
    lines = []
    for raw_line in plain(text).splitlines() or [""]:
        limit = max(8, first_width)
        buf: list[str] = []
        width = 0
        for ch in raw_line:
            cw = max(0, get_character_cell_size(ch))
            if buf and width + cw > limit:
                lines.append("".join(buf).rstrip())
                buf = [] if ch == " " else [ch]
                width = 0 if ch == " " else cw
                limit = max(8, rest_width)
            else:
                buf.append(ch)
                width += cw
        lines.append("".join(buf).rstrip())
    return lines


def _append_wrapped_row(details, prefix, prefix_style, body, body_style, *,
                        id_prefix="", id_style="", cont_indent="  ", total_width=35):
    first_w = total_width - cell_len(prefix) - cell_len(id_prefix)
    rest_w = total_width - cell_len(cont_indent)
    wrapped = _wrap_cells(body, first_w, rest_w)
    details.append(prefix, style=prefix_style)
    if id_prefix:
        details.append(id_prefix, style=id_style)
    details.append(wrapped[0], style=body_style)
    for cont in wrapped[1:]:
        details.append("\n" + cont_indent, style=prefix_style)
        details.append(cont, style=body_style)


class ReplyActivity(Static):
    BEATS = ("·", "✦", "●", "✦")

    def on_mount(self):
        self.lines = []
        self.color = None
        self.leading = False
        self.beat = 0
        self.timer = self.set_interval(0.35, self.advance, pause=True)

    def show(self, lines, *, color=None, leading=False):
        self.lines = lines
        self.color = color
        self.leading = leading
        if color and motion_enabled(self.app):
            self.timer.resume()
        else:
            self.timer.pause()
            self.beat = 0
        self.draw_activity()

    def advance(self):
        self.beat = (self.beat + 1) % len(self.BEATS)
        self.draw_activity()

    def draw_activity(self):
        status = Text()
        if self.lines and self.leading:
            beat = self.BEATS[self.beat] if self.color and motion_enabled(self.app) else "●"
            status.append(beat + " ", style=self.color or GOLD)
        status.append(plain("\n".join(self.lines)))
        self.update(status)


def room_status(room):
    if room.get("archived"):
        return "已归档", "dim"
    if room.get("running"):
        return "回复中", f"bold {GOLD}"
    if room.get("queued"):
        return "排队中", f"bold {SILVER}"
    return "空闲", MUTED_TEXT


class SessionSearch(Input):
    BINDINGS = [("up", "previous_room"), ("down", "next_room")]

    def action_previous_room(self):
        self.screen.query_one(OptionList).action_cursor_up()

    def action_next_room(self):
        self.screen.query_one(OptionList).action_cursor_down()


class SessionPicker(ModalScreen):
    BINDINGS = [("escape", "cancel")]

    def __init__(self, rooms, projects, current):
        super().__init__()
        self.rooms = rooms
        self.projects = {p["id"]: p["name"] for p in projects}
        self.current = current

    def compose(self):
        with Vertical(id="session-picker"):
            yield Label("切换会话", classes="heading")
            yield SessionSearch(placeholder="搜索会话、项目或目录", id="session-search")
            yield OptionList(compact=True, id="session-results")

    def on_mount(self):
        self.filter_rooms("")
        self.query_one(SessionSearch).focus()

    @on(Input.Changed, "#session-search")
    def update_search(self, event):
        self.filter_rooms(event.value)

    def filter_rooms(self, value):
        words = value.casefold().split()
        results = []
        for item in self.rooms:
            project = self.projects.get(item.get("project"), "独立会话")
            searchable = " ".join((item["title"], project, item.get("workdir", ""), item["id"])).casefold()
            if not all(word in searchable for word in words):
                continue
            status, color = room_status(item)
            marker = "› " if item["id"] == self.current else "  "
            results.append(Option(Text.assemble(marker + plain(item["title"]), ("  " + plain(project), "dim"),
                                                ("  " + status, color)), id=item["id"]))
        options = self.query_one(OptionList)
        options.set_options(results or [Option("没有匹配的会话", disabled=True)])
        options.highlighted = 0 if results else None

    @on(Input.Submitted, "#session-search")
    def submit_search(self):
        option = self.query_one(OptionList).highlighted_option
        if option is not None:
            self.dismiss(option.id)

    @on(OptionList.OptionSelected, "#session-results")
    def choose(self, event):
        self.dismiss(event.option_id)

    def action_cancel(self):
        self.dismiss()


class CreateForm(ModalScreen):
    BINDINGS = [("escape", "cancel", "取消")]

    def __init__(self, projects, current_project, *, create_project=False):
        super().__init__()
        self.projects = projects
        self.current_project = current_project
        self.create_project = create_project

    def compose(self) -> ComposeResult:
        with Vertical(id="new-form"):
            yield Label("新建项目" if self.create_project else "新建会话")
            yield Input(placeholder="项目名称" if self.create_project else "会话标题", id="new-title")
            if not self.create_project:
                choices = [("独立会话（不绑定项目）", "")] + [(plain(p["name"]), p["id"]) for p in self.projects]
                yield Select(choices, value=self.current_project, allow_blank=False, id="new-project")
            yield Input(os.getcwd(), placeholder="工作目录", id="new-directory")
            with Horizontal(id="new-actions"):
                yield Button("创建", id="create", variant="primary")
                yield Button("取消", id="cancel")

    def on_mount(self):
        self.query_one("#new-title", Input).focus()

    @on(Select.Changed, "#new-project")
    def show_directory(self, event):
        self.query_one("#new-directory", Input).disabled = bool(event.value)

    @on(Input.Submitted, "#new-title")
    @on(Button.Pressed, "#create")
    def submit(self):
        title = self.query_one("#new-title", Input).value.strip()
        if not title:
            self.notify("请填写项目名称。" if self.create_project else "请填写会话标题。", severity="warning")
            return
        folder = self.query_one("#new-directory", Input).value.strip().strip('"')
        if folder:
            folder = os.path.abspath(os.path.expandvars(os.path.expanduser(folder)))
        if self.create_project:
            if not folder:
                self.notify("请填写工作目录。", severity="warning")
                return
            self.dismiss({"name": title, "workdir": folder})
            return
        project = self.query_one("#new-project", Select).value
        body = {"title": title, "project": project}
        if not project and folder:
            body["workdir"] = folder
        self.dismiss(body)

    @on(Button.Pressed, "#cancel")
    def cancel(self):
        self.action_cancel()

    def action_cancel(self):
        self.dismiss()


class DebateForm(ModalScreen):
    BINDINGS = [("escape", "cancel")]

    def __init__(self, members, topic, previous=None):
        super().__init__()
        self.members = members
        self.topic = topic
        self.previous = previous

    def compose(self):
        with VerticalScroll(id="debate-form"):
            resume = self.previous is not None
            yield Label("继续论道" if resume else "开始论道", classes="heading")
            if resume:
                yield Label("原议题  " + plain(self.previous["topic"]), markup=False)
            yield Input(self.topic, placeholder="补充意见" if resume else "议题", id="debate-topic")
            with Horizontal(id="debate-rounds"):
                with Vertical():
                    yield Label("最少轮数")
                    yield Input("1" if resume else "0", type="integer", id="debate-min")
                with Vertical():
                    yield Label("最多轮数 · 留空不限")
                    yield Input("3", type="integer", id="debate-max")
            yield Label("参辩成员 · 空格切换")
            included = set(self.previous["participants"] if resume else self.members)
            moderator = (self.previous or {}).get("moderator")
            selected = [pid for pid in self.members if pid in included]
            yield SelectionList(*((plain(label), pid, pid in included) for pid, label in self.members.items()), id="debate-members")
            yield Label("负责总结")
            yield Select([(plain(self.members[pid]), pid) for pid in selected],
                         value=moderator if moderator in selected else next(iter(selected), Select.BLANK),
                         id="debate-moderator")
            with Horizontal(id="debate-actions"):
                yield Button("继续论道" if resume else "开始论道", id="debate-start", variant="primary")
                yield Button("取消", id="debate-cancel")

    @on(SelectionList.SelectedChanged)
    def participants_changed(self, event):
        moderator = self.query_one("#debate-moderator", Select)
        selected = event.selection_list.selected
        previous = moderator.value
        moderator.set_options([(plain(self.members[pid]), pid) for pid in selected])
        if selected:
            moderator.value = previous if previous in selected else selected[0]

    @on(Button.Pressed, "#debate-start")
    def submit_debate(self):
        topic = self.query_one("#debate-topic", Input).value.strip()
        ceiling = self.query_one("#debate-max", Input).value.strip()
        selected = self.query_one("#debate-members", SelectionList).selected
        moderator = self.query_one("#debate-moderator", Select).value
        try:
            minimum = int(self.query_one("#debate-min", Input).value.strip())
            maximum = int(ceiling) if ceiling else None
            if minimum < 0 or (maximum is not None and maximum < minimum):
                raise ValueError
        except ValueError:
            self.notify("轮数须为非负整数，上限须大于等于下限或留空。", severity="warning")
            return
        if not topic or len(selected) < (1 if maximum == 0 else 2) or moderator not in selected:
            self.notify("请填写议题，选择参辩成员和总结人。论道至少需要两位，直接总结时需要一位。", severity="warning")
            return
        self.dismiss({"feedback" if self.previous is not None else "topic": topic,
                      "min_rounds": minimum, "max_rounds": maximum,
                      "moderator": moderator, "participants": selected})

    @on(Button.Pressed, "#debate-cancel")
    def cancel(self):
        self.action_cancel()

    def action_cancel(self):
        self.dismiss()


class AnYTerminal(App):
    TITLE = "AnY"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("f2", "show_projects", "项目与会话"), ("f3", "toggle_details", "会话详情"),
        ("ctrl+r", "resume", "切换会话"), ("ctrl+q", "quit", "退出"),
        Binding("left", "switch_to_rooms", show=False),
        Binding("right", "switch_to_chat", show=False),
        Binding("ctrl+n", "new_room", show=False), Binding("ctrl+l", "compose_message", show=False),
        Binding("escape", "interrupt", show=False), Binding("f1", "help", show=False),
    ]
    CSS = """
    #layout { height: 1fr; }
    #navigation { display: none; width: 100%; max-width: 104; padding: 0 1; }
    #layout.home { align-horizontal: center; }
    #layout.home #navigation { display: block; }
    #layout.home #chat, #layout.home #details-pane { display: none; }
    #masthead { height: auto; margin-bottom: 1; border: round #89651e; padding: 0 1; }
    #masthead-body { height: auto; }
    #welcome { width: auto; height: auto; padding: 0 2 0 1; }
    #masthead-info { width: 1fr; height: auto; padding: 0 1; }
    #masthead-tips { width: auto; height: auto; padding: 0 1 0 2; border-left: solid #2c3644; display: none; }
    #layout.wide #masthead-tips { display: block; }
    #masthead-tagline { display: none; width: auto; height: 1; padding: 0 1; color: $text-muted; }
    #layout.compact #masthead { border: none; padding: 0; }
    #layout.compact #masthead-info, #layout.compact #masthead-tips { display: none; }
    #layout.compact #masthead-tagline { display: block; }
    #projects-heading { height: 1; width: 1fr; }
    #project-actions { height: 1; margin: 0 0 1 1; }
    #rooms { height: 1fr; border: none; padding: 0 1; background: $background; background-tint: transparent; }
    #rooms:focus { border: none; background: $background; background-tint: transparent; }
    #rooms > .option-list--option-highlighted { background: $surface; color: $text; text-style: bold; }
    #home-help { height: 1; padding: 0 1; color: $text-muted; text-overflow: ellipsis; }
    #chat { width: 1fr; min-width: 10; }
    #transcript { height: 1fr; min-height: 2; padding: 1 1 0 1; background: $background; overflow-x: hidden; scrollbar-size-vertical: 1; }
    #details-pane { display: none; width: 42; max-width: 44%; background: $surface; border-left: solid $panel; }
    #layout.expanded #details-pane { display: block; }
    #layout.expanded.narrow #chat { display: none; }
    #layout.expanded.narrow #details-pane { width: 1fr; max-width: 100%; border: none; }
    #details { padding: 1 1 1 2; }
    .heading { color: $text; padding: 0 1; height: 1; text-style: bold; }
    #chat-heading, #details-heading, #roster-bar { height: 1; }
    #chat-heading, #details-heading { margin: 0; padding: 0 1; background: $background; }
    #details-heading { background: $surface; }
    #title, #details-label { width: 1fr; height: 1; text-overflow: ellipsis; }
    #meeting-mode { width: auto; height: 1; padding: 0; background: $background; }
    #roster-bar { height: 1; padding: 0 1; background: $background; }
    #roster-scroll { width: 1fr; height: 1; overflow-x: auto; scrollbar-size-horizontal: 0; }
    #roster { width: auto; height: 1; }
    .link-button { width: auto; min-width: 0; height: 1; padding: 0 1; }
    #status, #activity { padding: 0 2; height: auto; color: $text-muted; }
    #status { max-height: 1; text-overflow: ellipsis; background: $background; color: $text-muted; }
    #activity { max-height: 4; }
    #composer { height: auto; padding: 0 1; }
    #message { height: 3; border: round #46576b; background: $background; }
    #message:focus { border: round #9f7523; }
    #completion { display: none; width: 100%; padding: 0; background: $surface; border: round $panel; }
    #completion > .option-list--option-highlighted { background: $primary 30%; color: $text; }
    #prompt-hint { padding: 0 1; height: 1; color: $text-muted; text-overflow: ellipsis; }
    CreateForm, SessionPicker, DebateForm { align: center middle; }
    #session-picker { width: 72; max-width: 95%; height: 18; max-height: 90%; border: round #9f7523; background: $surface; }
    #session-results { height: 1fr; border: none; }
    #new-form { width: 62; max-width: 95%; height: auto; border: round #9f7523; background: $surface; padding: 1 2; }
    #new-actions { height: auto; }
    #debate-form { width: 64; max-width: 95%; height: auto; max-height: 96%; border: round #9f7523; background: $surface; padding: 1; }
    #debate-rounds { height: 4; }
    #debate-members { height: auto; max-height: 9; }
    #debate-actions { height: 3; }
    Splash { background: #0b0e13; }
    #splash-center { width: 100%; height: 100%; align: center middle; }
    #splash-box { width: auto; height: auto; }
    #splash-art { width: auto; height: auto; }
    #splash-word { width: 34; height: 1; margin-top: 1; text-align: center; }
    #splash-tag { width: 34; height: 1; text-align: center; }
    """

    def __init__(self, client, room=None):
        super().__init__()
        self.register_theme(TERMINAL_THEME)
        self.theme = TERMINAL_THEME.name
        self.client = client
        self.room = room
        self.cursor = 0
        self.rooms = []
        self.projects = []
        self.state = {}
        self.tab = secrets.token_urlsafe(18)
        self.sending = False
        self.connected = False
        self.lease_request: asyncio.Task | None = None
        self.show_details = False
        self.last_room = None
        self.pending_open = None
        self.drafts: dict[str | None, str] = {}
        self.discovered: dict[str, str] = {}
        self._transcript_items: list[Any] = []
        self._transcript_width: int | None = None
        self.splash_active = False
        self.updating_cli = False

    @property
    def composer(self):
        return self.query_one(Composer)

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout", classes="home" if self.room is None else ""):
            with Vertical(id="navigation"):
                with Vertical(id="masthead"):
                    with Horizontal(id="masthead-body"):
                        yield WelcomeMark(id="welcome")
                        yield Static(id="masthead-info", markup=False)
                        yield Static(
                            Text.assemble(("上手提示", f"bold {GOLD}"),
                                          ("\nEnter 打开会话 · Ctrl+N 新建", f"dim {MUTED_TEXT}"),
                                          ("\n/ 命令 · @ 点名成员", f"dim {MUTED_TEXT}"),
                                          ("\nF3 看板与成员 · F1 帮助", f"dim {MUTED_TEXT}")),
                            id="masthead-tips", markup=False)
                        yield Static(f"  v{CLI_VERSION} · Agents and You", id="masthead-tagline", markup=False)
                with Horizontal(id="project-actions"):
                    yield Label("项目与会话", id="projects-heading", classes="heading")
                    yield Button("新建会话", id="home-new", compact=True, classes="link-button")
                    yield Button("新建项目", id="home-project", compact=True, classes="link-button")
                yield OptionList(id="rooms", compact=True)
                yield Static("↑↓ 选择  ·  Enter / → 打开  ·  Ctrl+R 搜索", id="home-help")
            with Vertical(id="chat"):
                with Horizontal(id="chat-heading"):
                    yield Button("‹ 项目", id="back-projects", compact=True, classes="link-button")
                    yield Static("AnY", id="title", classes="heading", markup=False)
                    yield Static(id="meeting-mode", markup=False)
                with Horizontal(id="roster-bar"):
                    with HorizontalScroll(id="roster-scroll"):
                        yield Static("你", id="roster", markup=False)
                    yield Button("看板 F3", id="show-members", compact=True, classes="link-button")
                yield RichLog(id="transcript", wrap=True, auto_scroll=False, max_lines=4000, min_width=10)
                yield ReplyActivity(id="activity", markup=False)
                yield Composer(self.complete_argument)
            with Vertical(id="details-pane"):
                with Horizontal(id="details-heading"):
                    yield Label("看板与成员", id="details-label", classes="heading")
                    yield Button("‹ 聊天", id="hide-members", compact=True, classes="link-button")
                with VerticalScroll():
                    yield Static(id="details", markup=False)
        yield Static("正在连接本机后台…", id="status", markup=False)

    def on_mount(self):
        self.splash_active = False
        self._sync_compact()
        self.update_masthead()
        self.focus_main()
        self.refresh_backend()
        if self.room is None and motion_enabled(self) and splash_enabled(self):
            self.splash_active = True

            def splash_done(_result=None):
                self.splash_active = False

            self.push_screen(Splash(), splash_done)

    def _sync_compact(self):
        layout = self.query_one("#layout")
        compact = self.size.width < 72 or self.size.height < 26
        layout.set_class(compact, "compact")
        layout.set_class(self.size.width >= 100, "wide")
        mark = self.query_one("#welcome", WelcomeMark)
        if mark.compact != compact:
            mark.compact = compact
            mark.redraw()
        with suppress(Exception):
            self.query_one("#masthead").border_title = f" AnY v{CLI_VERSION} "

    def update_masthead(self):
        try:
            info = self.query_one("#masthead-info", Static)
        except Exception:
            return
        cwd = os.getcwd()
        width = max(20, self.size.width - 60)
        if cell_len(cwd) > width:
            while cwd and cell_len("…" + cwd) > width:
                cwd = cwd[1:]
            cwd = "…" + cwd
        connection = ("已连接", MINT) if self.connected else ("连接中…", MUTED_TEXT)
        lines = Text()
        lines.append("欢迎回来\n", style=f"bold {PAPER}")
        lines.append("Agents and You\n\n", style=MUTED_TEXT)
        lines.append(cwd + "\n", style=f"dim {MUTED_TEXT}")
        lines.append(f"本机后台 127.0.0.1:{self.client.port}  ", style=f"dim {MUTED_TEXT}")
        lines.append(connection[0], style=connection[1])
        info.update(lines)

    async def on_unmount(self):
        self.workers.cancel_group(self, "refresh")
        if self.lease_request is not None:
            with suppress(CliError):
                await self.lease_request
                self.connected = True
        if self.connected:
            with suppress(CliError):
                await self.request("/api/ui/session", {"tab": self.tab, "action": "close"})

    def on_resize(self, event):
        self.query_one("#layout").set_class(event.size.width < 100, "narrow")
        self._sync_compact()
        self.update_masthead()
        self.composer.size_completion_menu()
        self.call_after_refresh(self._sync_transcript_width)

    @on(Button.Pressed, "#back-projects")
    def action_show_projects(self):
        previous = self.room
        self.select_room(None)
        rooms = self.query_one("#rooms", OptionList)
        if previous and any(row["id"] == previous for row in self.rooms):
            with suppress(Exception):
                rooms.highlighted = rooms.get_option_index(previous)
        self.focus_main()

    def action_switch_to_rooms(self):
        if self.room is None:
            return
        prompt = self.composer.prompt
        if self.focused is prompt and (bool(getattr(prompt, "text", "")) or self.composer.menu.display):
            return
        self.action_show_projects()

    def action_switch_to_chat(self):
        if self.room is not None:
            return
        widget = self.query_one("#rooms", OptionList)
        option = widget.highlighted_option
        target = option.id if option and option.id else None
        if not target:
            active_ids = [row["id"] for row in self.rooms if not row.get("archived")]
            if self.last_room in active_ids:
                target = self.last_room
            elif active_ids:
                target = active_ids[0]
        if target:
            self.open_room(target)
            self.action_compose_message()

    @on(Button.Pressed, "#show-members, #hide-members")
    def action_toggle_details(self):
        if self.room is not None:
            self.set_details(not self.show_details)

    def set_details(self, visible):
        self.show_details = visible
        self.query_one("#layout").set_class(visible, "expanded")
        self.focus_main()
        self.call_after_refresh(self._sync_transcript_width)

    def focus_main(self):
        if self.room is None:
            self.query_one("#rooms").focus()
        elif self.show_details and self.size.width < 100:
            self.query_one("#hide-members").focus()
        else:
            self.query_one("#message").focus()

    def action_compose_message(self):
        if self.room is not None and self.show_details and self.size.width < 100:
            self.set_details(False)
        else:
            self.focus_main()

    def action_help(self):
        if self.room is None:
            self.notify("↑↓ 选择会话，Enter / → 打开；Ctrl+R 搜索，Ctrl+N 新建。", timeout=6)
            return
        self.write("输入 / 查看命令，输入 @ 选择成员。Tab 补全，↑↓ 浏览候选或历史，Ctrl+R 搜索会话。\n"
                   "空输入框按 ← 返回会话列表（会话列表按 → 进入会话）。Enter 发送，Shift+Enter 或 Alt+Enter 换行。生成中按 Esc 停止。", "cyan")
        self.write("\n".join(f"/{name} {spec.arguments}  {spec.description}" for name, spec in COMMANDS.items()))

    def action_resume(self):
        self.push_screen(SessionPicker(self.rooms, self.projects, self.room), self.resume_room)

    def resume_room(self, room):
        if room is not None:
            self.open_room(room)
        self.action_compose_message()

    def check_action(self, action, parameters):
        if action in ("show_projects", "toggle_details", "resume", "new_room", "interrupt",
                      "switch_to_rooms", "switch_to_chat") and self.screen is not self.default_screen:
            return False
        if action == "switch_to_rooms":
            return self.room is not None
        if action == "switch_to_chat":
            return self.room is None
        if action == "interrupt":
            return bool(self.room and not self.sending and not self.composer.menu.display
                        and (self.state.get("running") or self.state.get("queued")))
        return super().check_action(action, parameters)

    def action_interrupt(self):
        self.submit(room_path(self.room, "stop"), {})

    @on(Button.Pressed, "#home-new")
    def action_new_room(self):
        if self.sending:
            return
        option = self.query_one("#rooms", OptionList).highlighted_option
        current = self.room if self.room is not None else option.id if option else None
        project = next((r["project"] for r in self.rooms if r["id"] == current), "")
        self.open_room_form(project)

    @on(Button.Pressed, "#home-project")
    def action_new_project(self):
        if not self.sending:
            self.push_screen(CreateForm([], "", create_project=True), self.create_project)

    def open_room_form(self, project):
        self.push_screen(CreateForm(self.projects, project), self.create_room)

    def create_room(self, data):
        if data is not None:
            self.submit("/api/rooms/new", data, created=True)

    def create_project(self, data):
        if data is not None:
            self.submit("/api/projects/new", data, project_created=True)

    async def request(self, path, data=None):
        return await asyncio.to_thread(self.client.call, path, data)

    async def connect_harness(self, data):
        discovery = await self.request("/api/discovery")
        pid = data["id"].lower()
        candidate: dict[str, Any] = next((row for row in discovery["detected"] if row["id"] == pid), {})
        wanted = CLI_VIAS if data["via"] == "cli" else ("acp",)
        via = next((mode for mode in candidate.get("options", []) if mode in wanted), None)
        if via is None:
            raise CliError("未找到对应的本机程序或接入方式，请用 /scan 查看可用接入。")
        return await self.request("/api/discovery/connect", {"id": pid, "via": via})

    def _append_transcript(self, item, *, scroll_end=None):
        self._transcript_items.append(item)
        if len(self._transcript_items) > 1000:
            del self._transcript_items[:-1000]
        log = self.query_one("#transcript", RichLog)
        width = log.scrollable_content_region.width
        if width > 0:
            self._transcript_width = width
        log.write(item, expand=True, scroll_end=scroll_end)

    def _sync_transcript_width(self):
        if self.room is None or (self.show_details and self.size.width < 100) or not self._transcript_items:
            return
        log = self.query_one("#transcript", RichLog)
        width = log.scrollable_content_region.width
        if width <= 0 or width == self._transcript_width:
            return
        follow = log.is_vertical_scroll_end
        self._transcript_width = width
        log.clear()
        for item in self._transcript_items:
            log.write(item, expand=True, scroll_end=False)
        if follow:
            log.scroll_end(animate=False)

    def write(self, value, style=None):
        log = self.query_one("#transcript", RichLog)
        self._append_transcript(Text(plain(value), style=style), scroll_end=log.is_vertical_scroll_end)

    def status(self, message):
        widget = self.query_one("#status", Static)
        widget.update(plain(message))
        widget.display = bool(message)

    def select_room(self, room):
        if room == self.room:
            return
        self.drafts[self.room] = self.composer.prompt.text
        self.room = room
        self.query_one("#layout").set_class(room is None, "home")
        self.set_details(False)
        self.cursor = 0
        self.state = {}
        self._transcript_items.clear()
        self._transcript_width = None
        self.query_one("#transcript", RichLog).clear()
        title = next((item["title"] for item in self.rooms if item["id"] == room), room)
        self.query_one("#title", Static).update(plain(title or "AnY"))
        self.query_one(ReplyActivity).show([])
        self.query_one("#details", Static).update("")
        self.query_one("#roster", Static).update("你")
        self.composer.set_history([])
        self.composer.dismissed = None
        self.composer.set_text(self.drafts.get(room, ""))

    @on(OptionList.OptionSelected, "#rooms")
    def choose_room(self, event):
        self.open_room(event.option_id)
        self.action_compose_message()

    def open_room(self, room):
        self.select_room(room)
        self.pending_open = room
        self.render_rooms({"rooms": self.rooms, "projects": self.projects}, force=True)

    def render_rooms(self, payload, *, force=False):
        rooms = payload["rooms"]
        projects = payload["projects"]
        self.last_room = payload.get("last", self.last_room)
        if not force and rooms == self.rooms and projects == self.projects:
            widget = self.query_one("#rooms", OptionList)
            if not widget.option_count:
                widget.add_option(Option("暂无会话，可先新建项目或会话。", disabled=True))
            return
        self.rooms, self.projects = rooms, projects
        groups = {p["id"]: p["name"] for p in projects}
        archived_projects = {room.get("project", "") for room in rooms if room.get("archived")}
        buckets: dict[str, list[dict[str, Any]]] = {pid: [] for pid in groups}
        for room in rooms:
            if not room.get("archived"):
                buckets.setdefault(room.get("project", ""), []).append(room)
        options = []
        for project, rows in buckets.items():
            if not rows and project in archived_projects:
                continue
            name = groups.get(project, "独立会话")
            heading = name if rows else f"{name} · 暂无会话"
            options.append(Option(Text(plain(heading), style=f"bold {SILVER}"), disabled=True))
            for row in rows:
                state, color = room_status(row)
                options.append(Option(Text.assemble(("  ● " if row.get("running") else "  ○ ", color),
                                                    (plain(row["title"]), PAPER), ("  ·  " + state, color)), id=row["id"]))
        widget = self.query_one("#rooms", OptionList)
        previous = widget.highlighted_option
        selected = previous.id if not force and previous and previous.id else self.room or self.last_room
        widget.set_options(options or [Option("暂无会话，可先新建项目或会话。", disabled=True)])
        widget.highlighted = next((i for i, opt in enumerate(options) if opt.id and opt.id == selected),
                                  next((i for i, opt in enumerate(options) if opt.id), None))

    def render_state(self, state):
        self.state = state
        title = plain(state["title"])
        mode = " 干活 " if state.get("mode") == "work" else " 讨论 "
        mode_bg = GOLD if state.get("mode") == "work" else SILVER
        project_id = state.get("project") or next((r["project"] for r in self.rooms if r["id"] == self.room), "")
        project = next((p["name"] for p in self.projects if p["id"] == project_id), "")
        heading = Text.assemble((plain(project) + " / " if project else "", f"dim {MUTED_TEXT}"), (title, f"bold {PAPER}"))
        self.query_one("#title", Static).update(heading)
        self.query_one("#meeting-mode", Static).update(Text(mode, style=f"bold {INK} on {mode_bg}"))
        names = {a["id"]: a["label"] for a in state.get("agents", [])}
        colors = agent_colors(state)
        roster = Text("◆ 你", style=f"bold {SILVER}", no_wrap=True, overflow="ignore")
        running = state.get("running", [])
        member_rows = []
        for member in state.get("participants", []):
            info = state.get("ais", {}).get(member, {})
            connection = state.get("members", {}).get(member, {})
            transport = connection.get("transport")
            tag = {"local": "本机", "desktop": "桌面", "member": "远端", "human": "人类", "http": "HTTP"}.get(transport, "")
            member_color = SILVER if transport == "human" else colors.get(member, MINT)
            if info.get("handed_off"):
                status, status_color = "已交接", MUTED_TEXT
            elif info.get("approval"):
                status, status_color = "等你确认", CORAL
            elif member in running:
                status, status_color = "回复中", f"bold {GOLD}"
            elif info.get("busy"):
                status, status_color = "排队", SILVER
            elif info.get("failure") is not None:
                status, status_color = "执行失败", RED
            elif transport in ("desktop", "member") and not connection.get("automatic"):
                status, status_color = "未连接", "dim"
            elif transport == "human":
                status, status_color = "在线", SILVER
            else:
                status, status_color = "空闲", member_color
            name = names.get(member, member)
            roster.append("  ·  ", style="dim")
            roster.append(f"{'○' if transport == 'human' else '●'} {plain(name)}", style=member_color)
            if status not in ("空闲", "在线"):
                roster.append(" " + status, style=status_color)
            model = info.get("model", {}).get("label") if transport != "human" else ""
            member_rows.append((transport == "human", member, name, member_color, tag, status, status_color, model))
        self.query_one("#roster", Static).update(roster)

        board = state.get("board") or []
        notes = [i for i in board if i.get("kind") == "note"]
        todos = [i for i in board if i.get("kind") != "note"]
        pending_todos = [i for i in todos if not i.get("done")]
        done_todos = [i for i in todos if i.get("done")]
        self.query_one("#details-label", Label).update(
            f"看板({len(pending_todos)} 待办) · 成员" if pending_todos else "看板与成员"
        )

        details = Text()
        # 1. 会议目标
        append_details_header(details, "会议目标", SILVER, first=True)
        announcement = (state.get("announcement") or "").strip()
        if announcement:
            _append_wrapped_row(details, "  ▌ ", f"bold {SILVER}", announcement, f"bold {PAPER}", cont_indent="  ▌ ")
        else:
            details.append("  ▌ ", style=f"dim {SILVER}")
            details.append("用 /announce 设置会议目标", style=f"dim {MUTED_TEXT}")

        # 2. 待办
        append_details_header(details, "待办", SILVER, count=len(pending_todos))
        if pending_todos:
            for idx, item in enumerate(pending_todos):
                if idx:
                    details.append("\n")
                _append_wrapped_row(
                    details, "  [ ] ", f"bold {SILVER}", item["text"], PAPER,
                    id_prefix=f"#{item['id']} ", id_style=f"bold {SILVER}", cont_indent="      ",
                )
        else:
            details.append("  暂无", style=f"dim {MUTED_TEXT}")

        # 3. 公告
        append_details_header(details, "公告", SILVER, count=len(notes))
        if notes:
            for idx, item in enumerate(notes):
                if idx:
                    details.append("\n")
                _append_wrapped_row(
                    details, "  › ", f"bold {SILVER}", item["text"], PAPER,
                    id_prefix=f"#{item['id']} ", id_style=f"bold {SILVER}", cont_indent="    ",
                )
        else:
            details.append("  暂无", style=f"dim {MUTED_TEXT}")

        # 4. 已完成
        append_details_header(details, "已完成", MUTED_TEXT, count=len(done_todos))
        if done_todos:
            for idx, item in enumerate(done_todos):
                if idx:
                    details.append("\n")
                _append_wrapped_row(
                    details, "  [x] ", f"dim {SILVER}", f"#{item['id']} {item['text']}", f"dim strike {MUTED_TEXT}",
                    cont_indent="      ",
                )
        else:
            details.append("  暂无", style=f"dim {MUTED_TEXT}")

        # 5. 正在改的文件（仅在存在占锁时展示）
        claims = state.get("claims") or []
        if claims:
            append_details_header(details, "正在改的文件", MUTED_TEXT, count=len(claims))
            for idx, claim in enumerate(claims):
                if idx:
                    details.append("\n")
                _append_wrapped_row(
                    details, "  ▸ ", f"bold {MUTED_TEXT}", f"{claim['shown']} · {claim['who']}", PAPER,
                    cont_indent="    ",
                )

        # 6. 论道
        debate = state.get("debate") or {}
        debate_state = debate.get("status") or ""
        if debate.get("topic"):
            phase = {"running": "进行中", "summarizing": "总结中", "completed": "已完成", "interrupted": "已中断",
                     "cancelled": "已取消", "failed": "未完成"}.get(debate_state, "")
            append_details_header(details, "论道", GOLD, right_note=phase)
            _append_wrapped_row(details, "  ▌ ", f"bold {GOLD}", debate["topic"], f"bold {PAPER}", cont_indent="  ▌ ")
            details.append(f"\n  已完成 {debate.get('completed_rounds', 0)} 轮", style=GOLD)

        # 7. 成员
        append_details_header(details, "成员", MINT, count=1 + len(member_rows))
        details.append("  ◆ ", style=f"bold {SILVER}")
        details.append("你", style=f"bold {PAPER}")
        details.append(" · 主持人", style=f"dim {MUTED_TEXT}")
        if member_rows:
            for is_human, member, name, member_color, tag, status, status_color, model in member_rows:
                details.append("\n")
                details.append("  ○ " if is_human else "  ● ", style=f"bold {member_color}")
                details.append(plain(name), style=f"bold {PAPER}")
                details.append(f" @{plain(member)}", style=f"dim {MUTED_TEXT}")
                meta = " · ".join(filter(None, (tag, status)))
                if meta:
                    details.append(f"  {meta}", style=status_color)
                if model:
                    details.append(f"\n  {plain(model)}", style=f"dim {MUTED_TEXT}")
        else:
            details.append("\n  用 /agents 查看并邀请联系人", style=f"dim {MUTED_TEXT}")

        self.query_one("#details", Static).update(details)
        live = [f"{name} · {entry['text']}" for name, entry in state.get("live", {}).items() if entry.get("text")]
        if debate_state in ("running", "summarizing"):
            stage = "总结中" if debate_state == "summarizing" else f"第 {debate.get('completed_rounds', 0) + 1} 轮"
            speaker = debate.get("speaker") or ""
            finish = " · 已请求收尾" if debate.get("finish_requested") and debate_state == "running" else ""
            live.insert(0, f"论道 · {stage}" + (" · " + names.get(speaker, speaker) if speaker else "") + finish)
        if not live and state.get("running"):
            live.append("回复中 · " + "、".join(state["running"]))
        if state.get("queued"):
            live.append(f"排队 {state['queued']}")
        active = next((member for member in state.get("live", {})
                       if member in running and state["live"][member].get("text")),
                      running[0] if running else None)
        self.query_one(ReplyActivity).show(
            live, color=GOLD if active else None,
            leading=bool(running or state.get("queued")),
        )
        self.composer.refresh_completion()

    def render_messages(self, batch):
        log = self.query_one("#transcript", RichLog)
        if batch["next"] < self.cursor:
            self.cursor = 0
            self._transcript_items.clear()
            log.clear()
            self.composer.history.clear()
            return
        follow = log.is_vertical_scroll_end
        colors = agent_colors(self.state)
        agents = {agent["id"]: agent for agent in self.state.get("agents", [])}
        members = self.state.get("members") or {}
        for message in batch["messages"]:
            if message.get("quiet"):
                continue
            speaker = message["speaker"]
            text = message.get("text")
            if speaker == "你" and text and (not self.composer.history or self.composer.history[-1] != text):
                self.composer.history.append(text)
                if len(self.composer.history) > 50:
                    del self.composer.history[0]
            self._append_transcript(transcript_entry(message, agents, colors, members), scroll_end=False)
        if follow and batch["messages"]:
            log.scroll_end(animate=False)
        self.cursor = batch["next"]

    @work(exclusive=True, group="refresh")
    async def refresh_backend(self):
        clock = asyncio.get_running_loop().time
        lease_due = rooms_due = state_due = 0.0
        last_state_room = None
        while self.is_running:
            room = self.room
            try:
                now = clock()
                if now >= lease_due:
                    self.lease_request = asyncio.create_task(self.request("/api/ui/session", {"tab": self.tab, "action": "open"}))
                    await asyncio.shield(self.lease_request)
                    if not self.is_running:
                        break
                    self.connected = True
                    self.update_masthead()
                    lease_due = now + 30
                if now >= rooms_due:
                    rooms_payload = await self.request("/api/rooms")
                    if not self.is_running:
                        break
                    self.render_rooms(rooms_payload)
                    rooms_due = now + 5
                room = self.room
                pending, self.pending_open = self.pending_open, None
                if pending is not None and pending == room:
                    await self.request(room_path(pending, "open"), {})
                    if not self.is_running:
                        break
                if room is not None:
                    if room != last_state_room or now >= state_due:
                        state = await self.request(room_path(room, "state"))
                        if not self.is_running:
                            break
                        if self.room == room:
                            if state != self.state:
                                self.render_state(state)
                            last_state_room, state_due = room, now + 2
                    if self.room == room:
                        batch = await self.request(room_path(room, f"messages?since={self.cursor}"))
                        if not self.is_running:
                            break
                        if self.room == room:
                            self.render_messages(batch)
                if self.sending:
                    self.status("正在处理命令…")
                else:
                    self.status(self.state.get("workdir") or ("正在加载会话…" if room else ""))
            except CliError as error:
                if not self.is_running:
                    break
                self.status(str(error))
                lease_due = 0
                if error.status == 404 and room is not None and room == self.room:
                    self.notify(plain(error), severity="warning", markup=False)
                    self.select_room(None)
            await asyncio.sleep(0.6)

    def complete_argument(self, command, argument):
        labels = {row["id"]: row["label"] for row in self.state.get("agents", [])}
        participants = {pid: labels.get(pid, pid) for pid in self.state.get("participants", [])}
        if command == "@":
            prefix = argument.casefold()
            return [(pid, label) for pid, label in participants.items() if pid.casefold() != prefix
                    and (pid.casefold().startswith(prefix) or label.casefold().startswith(prefix))]
        args = argument.split()
        if not args or argument.endswith(" "):
            args.append("")
        index = len(args) - 1
        choices, suffix = self.argument_values(command, args, index, participants)
        prefix = args[-1].casefold()
        return [Completion(value, hint, " ".join(("/" + command, *args[:-1], value)) + suffix)
                for value, hint in choices.items() if value.casefold() != prefix and value.casefold().startswith(prefix)]

    def argument_values(self, command, args, index, participants):
        if command == "model":
            models = {pid: info.get("model", {}) for pid, info in self.state.get("ais", {}).items()}
            if index == 0:
                return {pid: label for pid, label in participants.items()
                        if any(models.get(pid, {}).get(key) for key in ("model_supported", "effort_supported"))}, " "
            model = models.get(args[0], {})
            if index == 1 and (model.get("model_supported") or model.get("effort_supported")):
                hints = model.get("model_labels", {})
                return {"default": "由 Agent 决定", **{name: hints.get(name, "模型") for name in model.get("models", [])}}, " "
            if index == 2 and model.get("effort_supported"):
                model_id = model.get("default_model") if args[1] == "default" else args[1]
                efforts = model.get("efforts_by_model", {}).get(model_id, [])
                return {"default": "会话默认思考强度", **{effort: "思考强度" for effort in efforts}}, ""
        if command == "connect" and index == 0:
            return self.discovered, " "
        if command == "connect" and index == 1:
            return {"cli": "原生命令行", "acp": "Agent Client Protocol"}, ""
        if index == 0:
            if command == "mode":
                return {"discuss": "讨论模式", "work": "干活模式"}, ""
            if command == "update":
                return {"check": "检查 CLI 新版本", "install": "下载并安装 CLI 新版本"}, ""
            if command == "invite":
                return {row["id"]: row["label"] for row in self.state.get("agents", [])
                        if row["enabled"] and row["id"] not in participants}, ""
            if command in ("handoff", "return", "stop", "compact"):
                return participants, ""
            if command == "done":
                return {str(row["id"]): row["text"] for row in self.state.get("board", [])
                        if row["kind"] == "todo" and not row["done"]}, ""
        return {}, ""

    @on(Composer.Submitted)
    def send_message(self, event):
        value = event.text.strip()
        if not value or self.sending:
            return
        command, argument = "", ""
        if value.startswith("//"):
            value = value[1:]
        elif value.startswith("/"):
            parts = value[1:].split(maxsplit=1)
            command = parts[0].lower() if parts else ""
            argument = parts[1] if len(parts) == 2 else ""
            if command not in COMMANDS:
                self.notify("没有这个命令。输入 / 查看候选，发送以 / 开头的文字时用 //。", severity="warning")
                return
        if not command:
            value = composer_mention(value, self.state.get("participants", [])).strip()
            if not value:
                return
        local = {"help": self.action_help, "new": self.action_new_room, "resume": self.action_resume,
                 "status": self.show_status, "quit": self.exit,
                 "project": self.action_new_project}
        if command in local:
            self.composer.set_text("")
            local[command]()
            return
        if command == "agents":
            self.submit("/api/agents", None, draft=event.text)
            return
        if command == "scan":
            self.submit("/api/discovery/scan", {}, draft=event.text)
            return
        if command == "connect":
            parts = argument.split()
            if len(parts) != 2 or parts[1] not in ("cli", "acp"):
                self.notify("用法 /connect ID cli 或 /connect ID acp。先用 /scan 查找程序。", severity="warning")
                return
            self.submit("/api/discovery/connect", {"id": parts[0], "via": parts[1]}, draft=event.text)
            return
        if command == "update":
            sub = argument.strip().lower()
            if sub not in ("", "check", "install"):
                self.notify("用法 /update、/update check 或 /update install", severity="warning")
                return
            if self.updating_cli:
                self.notify("正在检查或更新 CLI，请稍候…", severity="warning")
                return
            self.composer.set_text("")
            self.run_cli_update(install=(sub == "install"))
            return
        if not self.room:
            self.notify("请先选择或创建会话。", severity="warning")
            return
        if command in ("debate", "debate-continue"):
            self.open_debate(argument, resume=command == "debate-continue")
            return
        if command == "model" and len(argument.split()) < 2:
            self.composer.set_text("/model " + (argument + " " if argument else ""))
            if not self.composer.menu.display:
                self.notify("请选择可配置的成员，或输入 /model 成员 模型 [强度]。", severity="warning")
            return
        try:
            action, data = self.message_action(command, argument, value)
        except CliError as error:
            self.notify(str(error), severity="warning")
            return
        self.submit(room_path(self.room, action), data, draft=event.text,
                    handoff=argument if command == "handoff" else None)

    def show_status(self):
        if self.room:
            self.set_details(True)

    def open_debate(self, topic, *, resume=False):
        previous = self.state.get("debate") if resume else None
        if resume and (not previous or previous.get("status") in ("running", "summarizing")):
            self.notify("当前没有可继续的论道。", severity="warning")
            return
        permissions = self.state.get("permissions", {})
        participants = self.state.get("participants", [])
        agents = self.state.get("agents", [])
        members = {a["id"]: a["label"] for a in agents if a["id"] in participants and a.get("kind") != "user"
                   and permissions.get(a["id"], {}).get("read") and permissions.get(a["id"], {}).get("post")
                   and not self.state.get("ais", {}).get(a["id"], {}).get("handed_off")
                   and self.state.get("execution", {}).get(a["id"], {}).get("phase", "ready") == "ready"}
        if not members:
            self.notify("当前会话没有可参加论道的 Agent。", severity="warning")
            return
        room = self.room
        draft = self.composer.prompt.text
        action = "debate/continue" if resume else "debate/start"

        def start_debate(data):
            if data is not None:
                self.submit(room_path(room, action), data, draft=draft)

        self.push_screen(DebateForm(members, topic, previous), start_debate)

    def message_action(self, command, argument, value):
        if command == "debate-finish":
            return "debate/finish", {}
        if command in ("stop", "compact"):
            return command, {"ai": argument}
        if command in ("handoff", "return"):
            if not argument:
                raise CliError(f"用法 /{command} 成员ID")
            return "handoff", {"ai": argument, "on": command == "handoff"}
        if command == "model":
            parts = argument.split()
            if len(parts) not in (2, 3):
                raise CliError("用法 /model 成员 模型 [强度]，default 使用默认值。")
            member, model, effort = (parts + [""])[:3]
            return "models", {"ai": member, "model": "" if model == "default" else model,
                              "effort": "" if effort == "default" else effort}
        if command == "mode":
            if argument not in ("discuss", "work"):
                raise CliError("用法 /mode discuss 或 /mode work")
            return "mode", {"mode": argument}
        if command == "invite":
            contact = next((a for a in self.state.get("agents", []) if a["id"] == argument and a["enabled"]), None)
            if contact is None:
                raise CliError("请用 /agents 查看已启用的联系人 ID。")
            if argument in self.state.get("participants", []):
                raise CliError("此联系人已经加入会话。")
            permissions = {"read": True, "post": True, "trigger": True, **contact.get("default_permissions", {})}
            return "invite", {"contact": argument, "permissions": permissions}
        if command == "announce":
            return "announcement", {"text": argument}
        if command == "todo":
            if not argument:
                raise CliError("用法 /todo 待办内容")
            return "board", {"op": "add", "kind": "todo", "text": argument}
        if command == "done":
            if not argument.isascii() or not argument.isdecimal() or len(argument) > 15:
                raise CliError("用法 /done 待办编号")
            return "board", {"op": "done", "id": int(argument)}
        return "send", {"text": value}

    @work(group="send")
    async def submit(self, path, data, *, draft=None, created=False, project_created=False, handoff=None):
        if self.sending:
            return
        self.sending = True
        room = self.room
        try:
            if path == "/api/discovery/connect":
                result = await self.connect_harness(data)
            else:
                result = await self.request(path, data)
            if draft is not None:
                if room == self.room and self.composer.prompt.text == draft:
                    self.composer.set_text("")
                elif room != self.room and self.drafts.get(room) == draft:
                    self.drafts[room] = ""
            if project_created:
                project = result["project"]
                self.render_rooms(await self.request("/api/rooms"))
                self.open_room_form(project["id"])
            elif created:
                self.select_room(result["id"])
                self.render_rooms(await self.request("/api/rooms"))
                self.action_compose_message()
            elif path == "/api/agents":
                self.write("\n".join(f"{a['id']}  ·  {a['label']}  ·  {'启用' if a['enabled'] else '未启用'}"
                                     for a in result["agents"]) or "没有已配置的联系人。", "cyan")
            elif path == "/api/discovery/scan":
                lines = []
                self.discovered = {}
                for item in result.get("detected", []):
                    options = item.get("options", [])
                    modes = ["cli"] if any(mode in CLI_VIAS for mode in options) else []
                    if "acp" in options:
                        modes.append("acp")
                    if modes:
                        self.discovered[item["id"]] = item["label"]
                        lines.append(f"{item['id']}  ·  {item['label']}  ·  {' / '.join(modes)}")
                self.write("\n".join(lines) or "没有发现可直连的本机 CLI 或 ACP 程序。", "cyan")
            elif path == "/api/discovery/connect":
                self.write(f"{result['id']}  ·  {result.get('msg') or '接入成功'}\n用 /invite {result['id']} 加入当前会话。", "cyan")
                if self.room:
                    selected = self.room
                    state = await self.request(room_path(selected, "state"))
                    if self.room == selected:
                        self.render_state(state)
            elif handoff:
                state = await self.request(room_path(room, "state"))
                if self.room == room:
                    command = state.get("ais", {}).get(handoff, {}).get("cmd")
                    if command:
                        self.write(f"在另一个终端运行\n{command}\n完成后在这里输入 /return {handoff}", "cyan")
        except CliError as error:
            self.notify(plain(error), severity="error", markup=False)
        finally:
            self.sending = False

    @work(group="cli-update")
    async def run_cli_update(self, *, install: bool):
        if self.updating_cli:
            return
        self.updating_cli = True
        self.write("正在检查 AnY CLI 更新（与桌面端更新独立）…", "dim")
        try:
            result = await asyncio.to_thread(cli_updater.check)
            state = result.get("state")
            if state == "error":
                msg = f"检查 AnY CLI 更新失败：{result.get('error') or '请检查网络后重试'}"
                self.write(msg, RED)
                self.notify(plain(msg), severity="error", markup=False)
                return
            if state != "available":
                msg = f"AnY CLI 当前已是最新版本（v{result.get('current')}，独立于桌面端更新）。"
                self.write(msg, "cyan")
                return

            notes = f"\n{result['notes']}" if result.get("notes") else ""
            if not install:
                hint = (
                    "\n输入 /update install 即可下载并安装新版 CLI（不影响桌面端）。"
                    if result.get("can_install")
                    else "\n当前为源码运行模式，请在源码目录执行 git pull 更新。"
                )
                self.write(
                    f"发现 AnY CLI 新版本 v{result['latest']}（当前 v{result['current']}）{notes}{hint}",
                    GOLD,
                )
                return

            if not result.get("can_install") or not result.get("release"):
                msg = (
                    f"发现 AnY CLI 新版本 v{result['latest']}（当前 v{result['current']}）。\n"
                    "当前不是通过官方终端安装脚本部署的环境，请在源码目录执行 git pull 更新。"
                )
                self.write(msg, CORAL)
                return

            self.write(f"正在下载并安装 AnY CLI v{result['latest']}…", "cyan")
            installed = await asyncio.to_thread(cli_updater.install_update, result["release"])
            msg = (
                f"AnY CLI 已更新至 v{installed['installed']}（{installed['commit'][:7]}），桌面端未受影响。\n"
                "退出后重新运行 any 即可启用新版（可输入 /quit 退出）。"
            )
            self.write(msg, MINT)
            self.notify("AnY CLI 更新完成，重新运行 any 即可生效。", timeout=6)
        except Exception as error:
            msg = f"AnY CLI 更新失败：{error}"
            self.write(msg, RED)
            self.notify(plain(msg), severity="error", markup=False)
        finally:
            self.updating_cli = False
