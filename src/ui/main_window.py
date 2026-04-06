"""
main_window.py: Main application window for Macktechs DriveKit
"""

import logging
import threading
import wx

from ..core import installer_manager, disk_manager, profile_manager, tools_manager, deploy_profile
from ..models.profile import DriveProfile
from ..utils.constants import APP_NAME, APP_VERSION, OS_NAMES

logger = logging.getLogger("drivekit.ui")

EVT_UPDATE_ID = wx.NewId()
EVT_COMPLETE_ID = wx.NewId()


class UpdateEvent(wx.PyEvent):
    def __init__(self, data=None):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_UPDATE_ID)
        self.data = data


class CompleteEvent(wx.PyEvent):
    def __init__(self, data=None):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_COMPLETE_ID)
        self.data = data


class MainWindow(wx.Frame):
    def __init__(self):
        super().__init__(
            None, title=f"{APP_NAME} v{APP_VERSION}",
            size=(960, 800),
            style=wx.DEFAULT_FRAME_STYLE
        )

        self.available_installers = []
        self.downloaded_installers = []
        self.external_drives = []
        self.profiles = []
        self.selected_profile = None
        self.tool_catalog = tools_manager.get_tool_catalog()
        self.deploy_profiles = deploy_profile.get_builtin_profiles()
        self.is_single_mode = False

        self._build_ui()
        self.Centre()

        self.Connect(-1, -1, EVT_UPDATE_ID, self._on_thread_update)
        self.Connect(-1, -1, EVT_COMPLETE_ID, self._on_thread_complete)

        wx.CallAfter(self._refresh_all)

    def _build_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # ── Header ──
        header_panel = wx.Panel(self)
        header_panel.SetBackgroundColour(wx.Colour(45, 45, 48))
        hsizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(header_panel, label=f"  {APP_NAME}")
        title.SetForegroundColour(wx.WHITE)
        font = title.GetFont()
        font.SetPointSize(20)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(font)
        hsizer.Add(title, 0, wx.TOP | wx.LEFT, 12)

        subtitle = wx.StaticText(header_panel,
            label="  Build multi-boot installer drives, single USB installers, and service tools")
        subtitle.SetForegroundColour(wx.Colour(180, 180, 180))
        hsizer.Add(subtitle, 0, wx.LEFT | wx.BOTTOM, 12)

        header_panel.SetSizer(hsizer)
        sizer.Add(header_panel, 0, wx.EXPAND)

        # ── Mode buttons ──
        mode_panel = wx.Panel(self)
        mode_sizer = wx.BoxSizer(wx.HORIZONTAL)
        mode_sizer.AddSpacer(12)

        self.multi_btn = wx.ToggleButton(mode_panel, label="  Multi-Boot Drive  ", size=(-1, 36))
        self.multi_btn.SetValue(True)
        self.multi_btn.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._set_mode(False))
        mode_sizer.Add(self.multi_btn, 0, wx.ALL, 6)

        self.single_btn = wx.ToggleButton(mode_panel, label="  Single Installer  ", size=(-1, 36))
        self.single_btn.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self._set_mode(True))
        mode_sizer.Add(self.single_btn, 0, wx.ALL, 6)

        mode_panel.SetSizer(mode_sizer)
        sizer.Add(mode_panel, 0, wx.EXPAND)

        # ── Notebook ──
        self.notebook = wx.Notebook(self)

        self._build_step1_drive()
        self._build_step2_installers()
        self._build_step3_layout()
        self._build_step4_tools()
        self._build_step5_deploy()
        self._build_step6_build()

        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 6)

        self.CreateStatusBar()
        self.SetStatusText("Ready")
        self.SetSizer(sizer)
        self.Layout()

    # ═══════════════════════════════════════════
    # Step 1: Select Drive
    # ═══════════════════════════════════════════

    def _build_step1_drive(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Step description
        desc = wx.StaticText(panel,
            label="Step 1: Select the external drive to use.\n"
                  "All data on this drive will be erased during the build process.")
        desc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(desc, 0, wx.ALL, 14)

        # Drive selector
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(panel, label="Drive:"), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.drive_choice = wx.Choice(panel, size=(500, -1))
        self.drive_choice.Bind(wx.EVT_CHOICE, self._on_drive_selected)
        row.Add(self.drive_choice, 1, wx.EXPAND | wx.RIGHT, 8)
        refresh_btn = wx.Button(panel, label="Refresh")
        refresh_btn.Bind(wx.EVT_BUTTON, lambda e: self._refresh_drives())
        row.Add(refresh_btn, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)

        # Drive details
        self.drive_info = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 200)
        )
        self.drive_info.SetFont(wx.Font(12, wx.FONTFAMILY_TELETYPE,
                                         wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.drive_info, 1, wx.EXPAND | wx.ALL, 14)

        # Recommendation
        self.rec_label = wx.StaticText(panel, label="")
        self.rec_label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(self.rec_label, 0, wx.LEFT | wx.BOTTOM, 14)

        # Next button
        next_btn = wx.Button(panel, label="Next: Choose Installers  >>", size=(250, 36))
        next_btn.Bind(wx.EVT_BUTTON, lambda e: self.notebook.SetSelection(1))
        sizer.Add(next_btn, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 14)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  1. Drive  ")

    # ═══════════════════════════════════════════
    # Step 2: Installers
    # ═══════════════════════════════════════════

    def _build_step2_installers(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Description (changes with mode)
        self.inst_desc = wx.StaticText(panel, label=(
            "Step 2: Download the macOS installers you want on your service drive.\n"
            "Click 'Fetch Latest from Apple' to see all available versions from Apple's servers.\n"
            "Check the versions you need and click 'Download Selected'. Already downloaded\n"
            "installers are marked — you only need to download what's missing."
        ))
        self.inst_desc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.inst_desc, 0, wx.ALL, 14)

        # Buttons
        row = wx.BoxSizer(wx.HORIZONTAL)
        fetch_btn = wx.Button(panel, label="Fetch Latest from Apple")
        fetch_btn.Bind(wx.EVT_BUTTON, self._on_fetch_installers)
        row.Add(fetch_btn, 0, wx.RIGHT, 8)
        self.dl_btn = wx.Button(panel, label="Download Selected")
        self.dl_btn.Bind(wx.EVT_BUTTON, self._on_download_selected)
        self.dl_btn.Disable()
        row.Add(self.dl_btn, 0)
        sizer.Add(row, 0, wx.LEFT | wx.RIGHT, 14)

        sizer.AddSpacer(8)

        # Installer list
        self.inst_list = wx.CheckListBox(panel, size=(-1, 250))
        sizer.Add(self.inst_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)

        # Already downloaded section
        self.downloaded_label = wx.StaticText(panel, label="")
        self.downloaded_label.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                               wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.downloaded_label, 0, wx.ALL, 14)

        # Progress
        self.dl_gauge = wx.Gauge(panel, range=100, size=(-1, 18))
        sizer.Add(self.dl_gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)
        self.dl_status = wx.StaticText(panel, label="")
        sizer.Add(self.dl_status, 0, wx.LEFT | wx.TOP, 14)

        # Nav
        nav = wx.BoxSizer(wx.HORIZONTAL)
        back = wx.Button(panel, label="<<  Back")
        back.Bind(wx.EVT_BUTTON, lambda e: self.notebook.SetSelection(0))
        nav.Add(back, 0, wx.RIGHT, 8)
        nav.AddStretchSpacer()
        # Next label changes with mode
        self.inst_next_btn = wx.Button(panel, label="Next  >>", size=(250, 36))
        self.inst_next_btn.Bind(wx.EVT_BUTTON, self._on_inst_next)
        nav.Add(self.inst_next_btn, 0)
        sizer.Add(nav, 0, wx.EXPAND | wx.ALL, 14)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  2. Installers  ")

    # ═══════════════════════════════════════════
    # Step 3: Layout (Multi-Boot only)
    # ═══════════════════════════════════════════

    def _build_step3_layout(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        desc = wx.StaticText(panel,
            label="Step 3: Choose a partition layout for your drive.\n"
                  "Profiles pre-configure partition sizes based on your drive capacity.")
        desc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(desc, 0, wx.ALL, 14)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(panel, label="Profile:"), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.profile_choice = wx.Choice(panel, size=(400, -1))
        self.profile_choice.Bind(wx.EVT_CHOICE, self._on_profile_selected)
        row.Add(self.profile_choice, 1, wx.EXPAND)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)

        self.profile_desc = wx.StaticText(panel, label="")
        self.profile_desc.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                           wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.profile_desc, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 14)

        self.layout_list = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(-1, 250)
        )
        self.layout_list.InsertColumn(0, "Partition Name", width=220)
        self.layout_list.InsertColumn(1, "Format", width=80)
        self.layout_list.InsertColumn(2, "Size", width=90)
        self.layout_list.InsertColumn(3, "Purpose", width=110)
        self.layout_list.InsertColumn(4, "macOS", width=100)
        sizer.Add(self.layout_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)

        self.total_label = wx.StaticText(panel, label="")
        sizer.Add(self.total_label, 0, wx.LEFT | wx.TOP, 14)

        nav = wx.BoxSizer(wx.HORIZONTAL)
        back = wx.Button(panel, label="<<  Back")
        back.Bind(wx.EVT_BUTTON, lambda e: self.notebook.SetSelection(1))
        nav.Add(back, 0)
        nav.AddStretchSpacer()
        nxt = wx.Button(panel, label="Next: Select Tools  >>", size=(250, 36))
        nxt.Bind(wx.EVT_BUTTON, lambda e: self.notebook.SetSelection(3))
        nav.Add(nxt, 0)
        sizer.Add(nav, 0, wx.EXPAND | wx.ALL, 14)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  3. Layout  ")

    # ═══════════════════════════════════════════
    # Step 4: Tools
    # ═══════════════════════════════════════════

    def _build_step4_tools(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        desc = wx.StaticText(panel,
            label="Step 4: Choose free tools and scripts to include on the Tools partition.\n"
                  "These will be copied to the drive so they're available when booting client Macs.")
        desc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(desc, 0, wx.ALL, 14)

        # Scrollable tool list
        self.tools_checkboxes = []
        categories = {}
        for tool in self.tool_catalog:
            categories.setdefault(tool.category, []).append(tool)

        scroll = wx.ScrolledWindow(panel)
        scroll.SetScrollRate(0, 10)
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)

        for cat_name, tools in categories.items():
            box = wx.StaticBoxSizer(wx.VERTICAL, scroll, cat_name)
            for tool in tools:
                cb = wx.CheckBox(scroll, label=tool.display)
                cb.tool_ref = tool
                if tool.install_method == "app_copy":
                    from pathlib import Path
                    if Path(tool.source).exists():
                        cb.SetValue(True)
                        tool.selected = True
                    else:
                        cb.SetLabel(f"{tool.display}  [not installed locally]")
                        cb.Disable()
                cb.Bind(wx.EVT_CHECKBOX, lambda e: setattr(e.GetEventObject().tool_ref, 'selected', e.IsChecked()))
                box.Add(cb, 0, wx.ALL, 4)
                self.tools_checkboxes.append(cb)
            scroll_sizer.Add(box, 0, wx.EXPAND | wx.ALL, 4)

        scroll.SetSizer(scroll_sizer)
        sizer.Add(scroll, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)

        # Quick buttons + scripts
        row = wx.BoxSizer(wx.HORIZONTAL)
        sel_all = wx.Button(panel, label="Select All")
        sel_all.Bind(wx.EVT_BUTTON, lambda e: self._toggle_all_tools(True))
        row.Add(sel_all, 0, wx.RIGHT, 8)
        sel_none = wx.Button(panel, label="Select None")
        sel_none.Bind(wx.EVT_BUTTON, lambda e: self._toggle_all_tools(False))
        row.Add(sel_none, 0, wx.RIGHT, 20)

        self.include_scripts = wx.CheckBox(panel,
            label="Include repair scripts (system report, cache flush, malware check)")
        self.include_scripts.SetValue(True)
        row.Add(self.include_scripts, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(row, 0, wx.ALL, 14)

        # Nav
        nav = wx.BoxSizer(wx.HORIZONTAL)
        back = wx.Button(panel, label="<<  Back")
        back.Bind(wx.EVT_BUTTON, lambda e: self.notebook.SetSelection(2 if not self.is_single_mode else 1))
        nav.Add(back, 0)
        nav.AddStretchSpacer()
        nxt = wx.Button(panel, label="Next: Deploy Settings  >>", size=(250, 36))
        nxt.Bind(wx.EVT_BUTTON, lambda e: self.notebook.SetSelection(4))
        nav.Add(nxt, 0)
        sizer.Add(nav, 0, wx.EXPAND | wx.ALL, 14)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  4. Tools  ")

    # ═══════════════════════════════════════════
    # Step 5: Deploy Profile
    # ═══════════════════════════════════════════

    def _build_step5_deploy(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        desc = wx.StaticText(panel,
            label="Step 5: Pre-configure a user account for macOS installs.\n"
                  "A first-boot package will be created that sets up this account automatically.\n"
                  "Leave blank to skip — the Mac will go through normal Setup Assistant.")
        desc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(desc, 0, wx.ALL, 14)

        # Preset
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(panel, label="Preset:"), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.deploy_choice = wx.Choice(panel, size=(300, -1))
        for dp in self.deploy_profiles:
            self.deploy_choice.Append(dp.name)
        self.deploy_choice.SetSelection(0)
        self.deploy_choice.Bind(wx.EVT_CHOICE, self._on_deploy_preset)
        row.Add(self.deploy_choice, 0)
        sizer.Add(row, 0, wx.LEFT | wx.BOTTOM, 14)

        # Fields
        grid = wx.FlexGridSizer(cols=2, vgap=10, hgap=12)
        grid.AddGrowableCol(1, 1)

        fields = [
            ("Full Name:", "deploy_fullname"),
            ("Username:", "deploy_username"),
            ("Password:", "deploy_password"),
            ("Computer Name:", "deploy_compname"),
            ("Timezone:", "deploy_tz"),
        ]
        for label, attr in fields:
            grid.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = wx.TextCtrl(panel, size=(350, -1))
            setattr(self, attr, ctrl)
            grid.Add(ctrl, 1, wx.EXPAND)

        sizer.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)

        self.deploy_autologin = wx.CheckBox(panel, label="Enable auto-login")
        sizer.Add(self.deploy_autologin, 0, wx.LEFT | wx.TOP, 14)

        self.deploy_skipsetup = wx.CheckBox(panel, label="Skip Setup Assistant")
        self.deploy_skipsetup.SetValue(True)
        sizer.Add(self.deploy_skipsetup, 0, wx.LEFT | wx.TOP, 14)

        # Save
        save_btn = wx.Button(panel, label="Save as Custom Preset")
        save_btn.Bind(wx.EVT_BUTTON, self._on_save_deploy_profile)
        sizer.Add(save_btn, 0, wx.LEFT | wx.TOP, 14)

        sizer.AddStretchSpacer()

        # Nav
        nav = wx.BoxSizer(wx.HORIZONTAL)
        back = wx.Button(panel, label="<<  Back")
        back.Bind(wx.EVT_BUTTON, lambda e: self.notebook.SetSelection(3))
        nav.Add(back, 0)
        nav.AddStretchSpacer()
        nxt = wx.Button(panel, label="Next: Review & Build  >>", size=(250, 36))
        nxt.Bind(wx.EVT_BUTTON, lambda e: (self._update_summary(), self.notebook.SetSelection(5)))
        nav.Add(nxt, 0)
        sizer.Add(nav, 0, wx.EXPAND | wx.ALL, 14)

        # Load first preset
        self._load_deploy_fields(self.deploy_profiles[0])

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  5. Deploy  ")

    # ═══════════════════════════════════════════
    # Step 6: Build
    # ═══════════════════════════════════════════

    def _build_step6_build(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        desc = wx.StaticText(panel,
            label="Step 6: Review your settings and build the drive.\n"
                  "This will erase the selected drive and set everything up.")
        desc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(desc, 0, wx.ALL, 14)

        self.summary_text = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 150)
        )
        self.summary_text.SetFont(wx.Font(11, wx.FONTFAMILY_TELETYPE,
                                           wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.summary_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 14)

        self.build_gauge = wx.Gauge(panel, range=100, size=(-1, 22))
        sizer.Add(self.build_gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)
        self.build_status = wx.StaticText(panel, label="Ready to build")
        sizer.Add(self.build_status, 0, wx.LEFT | wx.TOP, 14)

        self.build_log = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 180)
        )
        self.build_log.SetFont(wx.Font(11, wx.FONTFAMILY_TELETYPE,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.build_log, 1, wx.EXPAND | wx.ALL, 14)

        # Nav + Build
        nav = wx.BoxSizer(wx.HORIZONTAL)
        back = wx.Button(panel, label="<<  Back")
        back.Bind(wx.EVT_BUTTON, lambda e: self.notebook.SetSelection(4))
        nav.Add(back, 0)
        nav.AddStretchSpacer()
        self.build_btn = wx.Button(panel, label="Build Drive", size=(220, 44))
        self.build_btn.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.build_btn.Bind(wx.EVT_BUTTON, self._on_build)
        nav.Add(self.build_btn, 0)
        sizer.Add(nav, 0, wx.EXPAND | wx.ALL, 14)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  6. Build  ")

    # ═══════════════════════════════════════════
    # Mode Switching
    # ═══════════════════════════════════════════

    def _set_mode(self, single: bool):
        self.is_single_mode = single
        self.multi_btn.SetValue(not single)
        self.single_btn.SetValue(single)
        self._update_installer_desc()

        if single:
            self.notebook.SetPageText(0, "  1. Drive  ")
            self.notebook.SetPageText(1, "  2. Installer  ")
            self.notebook.SetPageText(2, "  3. (skip)  ")
            self.notebook.SetPageText(5, "  4. Build  ")
            self.SetStatusText("Single Installer: select a drive, pick one macOS version, and build.")
        else:
            self.notebook.SetPageText(0, "  1. Drive  ")
            self.notebook.SetPageText(1, "  2. Installers  ")
            self.notebook.SetPageText(2, "  3. Layout  ")
            self.notebook.SetPageText(5, "  6. Build  ")
            self.SetStatusText("Multi-Boot: build a full service drive with multiple macOS versions.")

    def _update_installer_desc(self):
        if self.is_single_mode:
            self.inst_desc.SetLabel(
                "Step 2: Pick the macOS version for this USB installer.\n"
                "Click 'Fetch Latest from Apple' to see available versions, then download the one you need.\n"
                "Select one installer to flash to the drive."
            )
            self.inst_next_btn.SetLabel("Next: Review & Build  >>")
        else:
            self.inst_desc.SetLabel(
                "Step 2: Download the macOS installers you want on your service drive.\n"
                "Click 'Fetch Latest from Apple' to see all available versions from Apple's servers.\n"
                "Check the versions you need and click 'Download Selected'. Already downloaded\n"
                "installers are marked — you only need to download what's missing."
            )
            self.inst_next_btn.SetLabel("Next: Partition Layout  >>")

    def _on_inst_next(self, event):
        if self.is_single_mode:
            self._update_summary()
            self.notebook.SetSelection(5)  # Skip to build
        else:
            self.notebook.SetSelection(2)  # Go to layout

    # ═══════════════════════════════════════════
    # Data Loading
    # ═══════════════════════════════════════════

    def _refresh_all(self):
        self._load_profiles()
        self._load_downloaded_installers()
        self._refresh_drives()

    def _refresh_drives(self):
        self.SetStatusText("Scanning for external drives...")
        self.external_drives = disk_manager.list_external_drives()
        self.drive_choice.Clear()
        for d in self.external_drives:
            self.drive_choice.Append(d.display_name)
        if self.external_drives:
            self.drive_choice.SetSelection(0)
            self._show_drive_info(0)
        self.SetStatusText(f"Found {len(self.external_drives)} external drive(s)")

    def _load_profiles(self):
        self.profiles = profile_manager.get_builtin_profiles()
        self.profile_choice.Clear()
        for p in self.profiles:
            self.profile_choice.Append(p.name)

    def _load_downloaded_installers(self):
        self.downloaded_installers = installer_manager.list_downloaded_installers()
        if self.downloaded_installers:
            names = [f"{d.display_name} ({d.build})" for d in self.downloaded_installers]
            self.downloaded_label.SetLabel(
                f"Already downloaded: {', '.join(names)}"
            )
        else:
            self.downloaded_label.SetLabel(
                "No installers downloaded yet. Click 'Fetch Latest from Apple' above."
            )

    # ═══════════════════════════════════════════
    # Drive Tab
    # ═══════════════════════════════════════════

    def _on_drive_selected(self, event):
        idx = self.drive_choice.GetSelection()
        if idx >= 0:
            self._show_drive_info(idx)

    def _show_drive_info(self, idx):
        drive = self.external_drives[idx]
        lines = [
            f"Drive:      {drive.name}",
            f"Identifier: {drive.identifier}",
            f"Size:       {drive.display_size}",
            "",
            "Current Partitions:",
            "-" * 50,
        ]
        for p in drive.partitions:
            lines.append(f"  {p.name:<30} {p.display_size:>8}")
        self.drive_info.SetValue("\n".join(lines))

        suggested = profile_manager.suggest_profile(drive.size_gb)
        self.rec_label.SetLabel(
            f"Recommended profile: {suggested.name}  |  "
            f"Uses {suggested.total_size_gb():.0f} GB of {drive.display_size}"
        )
        for i, p in enumerate(self.profiles):
            if p.name == suggested.name:
                self.profile_choice.SetSelection(i)
                self._show_layout(p)
                break

    # ═══════════════════════════════════════════
    # Installers Tab
    # ═══════════════════════════════════════════

    def _on_fetch_installers(self, event):
        self.SetStatusText("Fetching available installers from Apple...")
        self.inst_list.Clear()

        def fetch():
            all_inst = installer_manager.list_available_installers()
            latest = installer_manager.get_latest_per_major(all_inst)
            wx.PostEvent(self, CompleteEvent({"type": "fetch", "data": latest}))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_download_selected(self, event):
        checked = self.inst_list.GetCheckedItems()
        if not checked:
            wx.MessageBox("Select at least one installer to download.",
                          "Nothing Selected", wx.OK | wx.ICON_INFORMATION)
            return

        idx = checked[0]
        inst = self.available_installers[idx]
        if inst.downloaded:
            wx.MessageBox(f"{inst.display_name} is already downloaded.",
                          "Already Downloaded", wx.OK | wx.ICON_INFORMATION)
            return

        self.dl_status.SetLabel(f"Downloading {inst.display_name}... this may take a while.")
        self.dl_gauge.Pulse()

        def download():
            proc = installer_manager.download_installer(inst.version)
            proc.wait()
            wx.PostEvent(self, CompleteEvent({
                "type": "download", "version": inst.version,
                "ok": proc.returncode == 0,
            }))

        threading.Thread(target=download, daemon=True).start()

    # ═══════════════════════════════════════════
    # Layout Tab
    # ═══════════════════════════════════════════

    def _on_profile_selected(self, event):
        idx = self.profile_choice.GetSelection()
        if idx >= 0:
            self._show_layout(self.profiles[idx])

    def _show_layout(self, profile: DriveProfile):
        self.selected_profile = profile
        self.profile_desc.SetLabel(profile.description)
        self.layout_list.DeleteAllItems()
        for i, spec in enumerate(profile.partitions):
            row = self.layout_list.InsertItem(i, spec.name)
            self.layout_list.SetItem(row, 1, spec.format)
            self.layout_list.SetItem(row, 2,
                                      f"{spec.size_gb:.0f} GB" if spec.size_gb > 0 else "Remainder")
            self.layout_list.SetItem(row, 3, spec.purpose)
            self.layout_list.SetItem(row, 4, spec.installer_version or "")
        self.total_label.SetLabel(
            f"Total allocated: {profile.total_size_gb():.0f} GB  +  remainder as free space"
        )

    # ═══════════════════════════════════════════
    # Tools Tab
    # ═══════════════════════════════════════════

    def _toggle_all_tools(self, state):
        for cb in self.tools_checkboxes:
            if cb.IsEnabled():
                cb.SetValue(state)
                cb.tool_ref.selected = state

    # ═══════════════════════════════════════════
    # Deploy Tab
    # ═══════════════════════════════════════════

    def _on_deploy_preset(self, event):
        idx = self.deploy_choice.GetSelection()
        if idx >= 0 and idx < len(self.deploy_profiles):
            self._load_deploy_fields(self.deploy_profiles[idx])

    def _load_deploy_fields(self, dp):
        self.deploy_fullname.SetValue(dp.full_name)
        self.deploy_username.SetValue(dp.username)
        self.deploy_password.SetValue(dp.password)
        self.deploy_compname.SetValue(dp.computer_name)
        self.deploy_tz.SetValue(dp.timezone)
        self.deploy_autologin.SetValue(dp.auto_login)
        self.deploy_skipsetup.SetValue(dp.skip_setup_assistant)

    def _get_deploy_from_fields(self):
        return deploy_profile.DeployProfile(
            name=self.deploy_choice.GetStringSelection() or "Custom",
            full_name=self.deploy_fullname.GetValue(),
            username=self.deploy_username.GetValue(),
            password=self.deploy_password.GetValue(),
            computer_name=self.deploy_compname.GetValue(),
            auto_login=self.deploy_autologin.GetValue(),
            skip_setup_assistant=self.deploy_skipsetup.GetValue(),
            timezone=self.deploy_tz.GetValue(),
        )

    def _on_save_deploy_profile(self, event):
        dp = self._get_deploy_from_fields()
        dlg = wx.TextEntryDialog(self, "Profile name:", "Save Deploy Profile", dp.name)
        if dlg.ShowModal() == wx.ID_OK:
            dp.name = dlg.GetValue()
            deploy_profile.save_custom_profile(dp)
            names = [p.name for p in self.deploy_profiles]
            if dp.name not in names:
                self.deploy_profiles.append(dp)
                self.deploy_choice.Append(dp.name)
            wx.MessageBox(f"Saved profile '{dp.name}'.", "Saved", wx.OK | wx.ICON_INFORMATION)

    # ═══════════════════════════════════════════
    # Build Tab
    # ═══════════════════════════════════════════

    def _update_summary(self):
        drive_idx = self.drive_choice.GetSelection()
        drive_str = (self.external_drives[drive_idx].display_name
                     if drive_idx >= 0 else "No drive selected")
        mode = "Single Installer" if self.is_single_mode else "Multi-Boot Service Drive"

        lines = [f"Mode:    {mode}", f"Target:  {drive_str}", ""]

        if self.is_single_mode:
            checked = self.inst_list.GetCheckedItems()
            if checked and self.available_installers:
                inst = self.available_installers[checked[0]]
                lines.append(f"Installer: {inst.display_name}")
                lines.append(f"Status:    {'Ready' if inst.downloaded else 'NEEDS DOWNLOAD'}")
            elif self.downloaded_installers:
                lines.append("Select an installer from the Installers tab")
            else:
                lines.append("No installers available — fetch and download one first")
        else:
            if self.selected_profile:
                lines.append(f"Profile: {self.selected_profile.name}")
                lines.append("")
                inst_specs = [s for s in self.selected_profile.partitions if s.purpose == "installer"]
                missing = 0
                for s in inst_specs:
                    app = self._find_installer_app(s.installer_version)
                    tag = "Ready" if app else "NOT DOWNLOADED"
                    if not app:
                        missing += 1
                    lines.append(f"  {s.name:<35} [{tag}]")
                if missing:
                    lines.append(f"\n  {missing} installer(s) need downloading first")

        # Tools
        selected_tools = [t for t in self.tool_catalog if t.selected]
        if selected_tools:
            lines.append(f"\nTools: {len(selected_tools)} selected")

        # Deploy
        dp = self._get_deploy_from_fields()
        if dp.username:
            lines.append(f"Deploy: user '{dp.username}' on '{dp.computer_name or 'auto'}'")

        self.summary_text.SetValue("\n".join(lines))

    def _on_build(self, event):
        drive_idx = self.drive_choice.GetSelection()
        if drive_idx < 0:
            wx.MessageBox("Go back to Step 1 and select a drive.",
                          "No Drive", wx.OK | wx.ICON_WARNING)
            return

        drive = self.external_drives[drive_idx]

        if self.is_single_mode:
            self._do_single_build(drive)
        else:
            self._do_multi_build(drive)

    def _do_single_build(self, drive):
        # Figure out which installer
        checked = self.inst_list.GetCheckedItems()
        installer = None

        if checked and self.available_installers:
            installer = self.available_installers[checked[0]]
            if not installer.downloaded:
                # Try to find it in downloaded list
                for d in self.downloaded_installers:
                    if installer.version.startswith(d.version):
                        installer = d
                        break
                else:
                    wx.MessageBox("Download this installer first.",
                                  "Not Downloaded", wx.OK | wx.ICON_WARNING)
                    return
        elif self.downloaded_installers:
            # Let them pick from downloaded
            choices = [f"{d.display_name} ({d.build})" for d in self.downloaded_installers]
            dlg = wx.SingleChoiceDialog(self, "Select installer:", "Pick Installer", choices)
            if dlg.ShowModal() != wx.ID_OK:
                return
            installer = self.downloaded_installers[dlg.GetSelection()]
        else:
            wx.MessageBox("No installers available. Download one first.",
                          "Error", wx.OK | wx.ICON_WARNING)
            return

        dlg = wx.MessageDialog(
            self,
            f"ERASE ALL DATA on:\n\n"
            f"    {drive.name}  ({drive.display_size})\n"
            f"    {drive.identifier}\n\n"
            f"Flash: {installer.display_name}\n\nContinue?",
            "Confirm", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_EXCLAMATION,
        )
        if dlg.ShowModal() != wx.ID_YES:
            return

        if not disk_manager.verify_external(drive.identifier):
            wx.MessageBox("Safety check failed.", "Error", wx.OK | wx.ICON_ERROR)
            return

        self.build_btn.Disable()
        self.build_log.Clear()
        self._log(f"Single installer: {installer.display_name}")
        self._log(f"Target: {drive.display_name}\n")
        self.build_gauge.SetValue(10)

        def do_single():
            import time
            from ..core.privilege import run_privileged

            self._post_update("status", "Erasing drive...")
            self._post_update("log", "Erasing drive...")
            erase_cmd = f'diskutil eraseDisk JHFS+ "Install {installer.os_name}" GPT {drive.identifier}'
            p = run_privileged(erase_cmd)
            p.communicate()
            if p.returncode != 0:
                wx.PostEvent(self, CompleteEvent({"type": "build_error", "error": "Erase failed"}))
                return

            time.sleep(2)
            self._post_update("progress", 20)
            self._post_update("status", f"Flashing {installer.os_name}...")
            self._post_update("log", f"Flashing {installer.display_name}...")

            vol = f'/Volumes/Install {installer.os_name}'
            cmd = (
                f'"{installer.app_path}/Contents/Resources/createinstallmedia" '
                f'--volume "{vol}" --nointeraction'
            )
            p = run_privileged(cmd)
            p.communicate()

            if p.returncode != 0:
                wx.PostEvent(self, CompleteEvent({"type": "build_error", "error": "Flash failed"}))
            else:
                wx.PostEvent(self, CompleteEvent({"type": "build_done"}))

        threading.Thread(target=do_single, daemon=True).start()

    def _do_multi_build(self, drive):
        if not self.selected_profile:
            wx.MessageBox("Go to Step 3 and select a layout profile.",
                          "No Profile", wx.OK | wx.ICON_WARNING)
            return

        dlg = wx.MessageDialog(
            self,
            f"ERASE ALL DATA on:\n\n"
            f"    {drive.name}  ({drive.display_size})\n"
            f"    {drive.identifier}\n\n"
            f"Profile: {self.selected_profile.name}\n\nContinue?",
            "Confirm", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_EXCLAMATION,
        )
        if dlg.ShowModal() != wx.ID_YES:
            return

        if not disk_manager.verify_external(drive.identifier):
            wx.MessageBox("Safety check failed.", "Error", wx.OK | wx.ICON_ERROR)
            return

        self.build_btn.Disable()
        self.build_log.Clear()
        self._log(f"Multi-Boot build: {self.selected_profile.name}")
        self._log(f"Target: {drive.display_name}\n")
        self.build_gauge.SetValue(5)

        def do_multi():
            import time, os
            from ..core.privilege import run_privileged

            # Partition
            self._post_update("log", "Step 1: Partitioning drive...")
            self._post_update("status", "Partitioning...")
            proc = disk_manager.partition_drive(drive.identifier, self.selected_profile.partitions)
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                wx.PostEvent(self, CompleteEvent({"type": "build_error", "error": f"Partition failed:\n{stderr}"}))
                return

            self._post_update("log", "Done.\n")
            time.sleep(3)

            # Flash
            inst_specs = [s for s in self.selected_profile.partitions if s.purpose == "installer"]
            self._post_update("log", f"Step 2: Flashing {len(inst_specs)} installers...")
            for i, spec in enumerate(inst_specs):
                app_path = self._find_installer_app(spec.installer_version)
                if not app_path:
                    self._post_update("log", f"  Skip {spec.name}: not downloaded")
                    continue
                vol = f"/Volumes/{spec.name}"
                if not os.path.exists(vol):
                    self._post_update("log", f"  Skip {spec.name}: volume not found")
                    continue

                pct = 10 + int((i / max(len(inst_specs), 1)) * 70)
                self._post_update("progress", pct)
                self._post_update("status", f"Flashing {spec.name} ({i+1}/{len(inst_specs)})...")
                self._post_update("log", f"  Flashing {spec.name}...")

                cmd = (f'"{app_path}/Contents/Resources/createinstallmedia" '
                       f'--volume "{vol}" --nointeraction')
                p = run_privileged(cmd)
                p.communicate()

                if p.returncode != 0:
                    self._post_update("log", f"  ERROR: {spec.name}")
                else:
                    self._post_update("log", f"  Done: {spec.name}")

            # Tools
            selected_tools = [t for t in self.tool_catalog if t.selected]
            if selected_tools:
                self._post_update("log", f"\nStep 3: Setting up tools...")
                self._post_update("progress", 85)
                tools_specs = [s for s in self.selected_profile.partitions if s.purpose == "tools"]
                if tools_specs:
                    tools_vol = f"/Volumes/{tools_specs[0].name}"
                    if os.path.exists(tools_vol):
                        for tool in selected_tools:
                            if tool.install_method == "app_copy":
                                tools_manager.copy_app_to_volume(tool.source, tools_vol)
                                self._post_update("log", f"  Copied {tool.name}")
                            elif tool.install_method == "brew":
                                tools_manager.download_brew_to_volume(tool.source, tools_vol)
                                self._post_update("log", f"  Staged {tool.name}")
                        if self.include_scripts.GetValue():
                            tools_manager.copy_scripts_to_volume(tools_vol)
                            self._post_update("log", "  Added repair scripts")

            # Deploy
            dp = self._get_deploy_from_fields()
            if dp.username:
                self._post_update("log", f"\nStep 4: Creating deploy package...")
                self._post_update("progress", 92)
                if tools_specs:
                    tools_vol = f"/Volumes/{tools_specs[0].name}"
                    if os.path.exists(tools_vol):
                        pkg_dir = os.path.join(tools_vol, "DriveKit", "packages")
                        os.makedirs(pkg_dir, exist_ok=True)
                        pkg = deploy_profile.generate_firstboot_pkg(dp, pkg_dir)
                        if pkg:
                            self._post_update("log", f"  Created {os.path.basename(pkg)}")
                        deploy_profile.save_profiles_to_volume([dp], tools_vol)

            wx.PostEvent(self, CompleteEvent({"type": "build_done"}))

        threading.Thread(target=do_multi, daemon=True).start()

    # ═══════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════

    def _post_update(self, kind, value):
        wx.PostEvent(self, UpdateEvent({"kind": kind, "value": value}))

    def _find_installer_app(self, major_version: str) -> str:
        os_name = OS_NAMES.get(major_version, "")
        if not os_name:
            return ""
        from pathlib import Path
        for app in Path("/Applications").glob("Install macOS*.app"):
            if os_name.lower() in app.name.lower():
                if (app / "Contents" / "Resources" / "createinstallmedia").exists():
                    return str(app)
        return ""

    def _log(self, msg):
        self.build_log.AppendText(msg + "\n")

    def _on_thread_update(self, event):
        d = event.data
        kind = d.get("kind", "")
        val = d.get("value", "")
        if kind == "log":
            self._log(val)
        elif kind == "progress":
            self.build_gauge.SetValue(val)
        elif kind == "status":
            self.build_status.SetLabel(val)

    def _on_thread_complete(self, event):
        d = event.data
        t = d.get("type", "")

        if t == "fetch":
            self.available_installers = d["data"]
            self.inst_list.Clear()
            for inst in self.available_installers:
                self.inst_list.Append(str(inst))
            self.dl_btn.Enable()
            self.SetStatusText(f"Found {len(self.available_installers)} latest installers")

        elif t == "download":
            self.dl_gauge.SetValue(100 if d["ok"] else 0)
            self.dl_status.SetLabel(
                f"Download complete: macOS {d['version']}" if d["ok"]
                else f"Download failed: macOS {d['version']}"
            )
            self._load_downloaded_installers()

        elif t == "build_done":
            self.build_gauge.SetValue(100)
            self.build_status.SetLabel("Build complete!")
            self._log("\n" + "=" * 40)
            self._log("BUILD COMPLETE!")
            self._log("=" * 40)
            self.build_btn.Enable()
            wx.MessageBox("Drive build complete!\nYour service drive is ready.",
                          "Done", wx.OK | wx.ICON_INFORMATION)

        elif t == "build_error":
            self.build_gauge.SetValue(0)
            self.build_status.SetLabel("Build failed")
            self._log(f"\nERROR: {d['error']}")
            self.build_btn.Enable()
            wx.MessageBox(f"Build failed:\n{d['error']}", "Error", wx.OK | wx.ICON_ERROR)
