"""
main_window.py: Main application window for Macktechs DriveKit
"""

import logging
import threading
import wx

from ..core import installer_manager, disk_manager, profile_manager, tools_manager, deploy_profile
from ..core.flash_manager import FlashQueue
from ..models.drive import PartitionSpec
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
            size=(960, 780),
            style=wx.DEFAULT_FRAME_STYLE
        )

        self.available_installers = []
        self.downloaded_installers = []
        self.external_drives = []
        self.profiles = []
        self.selected_profile = None
        self.tool_catalog = tools_manager.get_tool_catalog()
        self.deploy_profiles = deploy_profile.get_builtin_profiles()
        self.selected_deploy = self.deploy_profiles[0]

        self._build_ui()
        self.Centre()

        self.Connect(-1, -1, EVT_UPDATE_ID, self._on_thread_update)
        self.Connect(-1, -1, EVT_COMPLETE_ID, self._on_thread_complete)

        wx.CallAfter(self._refresh_all)

    def _build_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        header = wx.StaticText(self, label=f"  {APP_NAME}")
        font = header.GetFont()
        font.SetPointSize(18)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        header.SetFont(font)
        sizer.Add(header, 0, wx.TOP | wx.LEFT, 10)

        # Mode selector
        mode_row = wx.BoxSizer(wx.HORIZONTAL)
        mode_row.Add(wx.StaticText(self, label="  Mode: "), 0, wx.ALIGN_CENTER_VERTICAL)
        self.mode_choice = wx.Choice(self, choices=[
            "Multi-Boot Service Drive",
            "Single Installer USB",
        ])
        self.mode_choice.SetSelection(0)
        self.mode_choice.Bind(wx.EVT_CHOICE, self._on_mode_changed)
        mode_row.Add(self.mode_choice, 0, wx.LEFT, 4)
        sizer.Add(mode_row, 0, wx.LEFT | wx.BOTTOM, 8)

        # Notebook
        self.notebook = wx.Notebook(self)

        self._build_drive_tab()
        self._build_installer_tab()
        self._build_profile_tab()
        self._build_tools_tab()
        self._build_deploy_tab()
        self._build_build_tab()

        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 8)

        self.CreateStatusBar()
        self.SetStatusText("Ready")
        self.SetSizer(sizer)
        self.Layout()

    # ── Tab 1: Drive ──

    def _build_drive_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(panel, label="External Drive:"), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.drive_choice = wx.Choice(panel, size=(450, -1))
        self.drive_choice.Bind(wx.EVT_CHOICE, self._on_drive_selected)
        row.Add(self.drive_choice, 1, wx.EXPAND | wx.RIGHT, 8)
        refresh_btn = wx.Button(panel, label="Refresh")
        refresh_btn.Bind(wx.EVT_BUTTON, lambda e: self._refresh_drives())
        row.Add(refresh_btn, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 12)

        self.drive_info = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 220)
        )
        self.drive_info.SetFont(wx.Font(12, wx.FONTFAMILY_TELETYPE,
                                         wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.drive_info, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.rec_label = wx.StaticText(panel, label="Select a drive to see recommendations.")
        self.rec_label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT,
                                        wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.rec_label, 0, wx.ALL, 12)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  Drive  ")

    # ── Tab 2: Installers ──

    def _build_installer_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        row = wx.BoxSizer(wx.HORIZONTAL)
        fetch_btn = wx.Button(panel, label="Fetch Available Versions")
        fetch_btn.Bind(wx.EVT_BUTTON, self._on_fetch_installers)
        row.Add(fetch_btn, 0, wx.RIGHT, 8)
        self.dl_btn = wx.Button(panel, label="Download Selected")
        self.dl_btn.Bind(wx.EVT_BUTTON, self._on_download_selected)
        self.dl_btn.Disable()
        row.Add(self.dl_btn, 0)
        sizer.Add(row, 0, wx.ALL, 12)

        self.inst_list = wx.CheckListBox(panel, size=(-1, 300))
        sizer.Add(self.inst_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.dl_gauge = wx.Gauge(panel, range=100, size=(-1, 18))
        sizer.Add(self.dl_gauge, 0, wx.EXPAND | wx.ALL, 12)
        self.dl_status = wx.StaticText(panel, label="")
        sizer.Add(self.dl_status, 0, wx.LEFT | wx.BOTTOM, 12)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  Installers  ")

    # ── Tab 3: Layout ──

    def _build_profile_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(panel, label="Profile:"), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.profile_choice = wx.Choice(panel, size=(400, -1))
        self.profile_choice.Bind(wx.EVT_CHOICE, self._on_profile_selected)
        row.Add(self.profile_choice, 1, wx.EXPAND)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 12)

        self.profile_desc = wx.StaticText(panel, label="")
        sizer.Add(self.profile_desc, 0, wx.LEFT | wx.BOTTOM, 12)

        self.layout_list = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(-1, 280)
        )
        self.layout_list.InsertColumn(0, "Partition Name", width=220)
        self.layout_list.InsertColumn(1, "Format", width=80)
        self.layout_list.InsertColumn(2, "Size", width=90)
        self.layout_list.InsertColumn(3, "Purpose", width=110)
        self.layout_list.InsertColumn(4, "macOS", width=100)
        sizer.Add(self.layout_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.total_label = wx.StaticText(panel, label="")
        sizer.Add(self.total_label, 0, wx.ALL, 12)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  Layout  ")

    # ── Tab 4: Tools ──

    def _build_tools_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel, label="Select tools to include on the Tools partition:")
        lbl.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(lbl, 0, wx.ALL, 12)

        # Group tools by category
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

                # Auto-check apps that exist locally
                if tool.install_method == "app_copy":
                    from pathlib import Path
                    if Path(tool.source).exists():
                        cb.SetValue(True)
                        tool.selected = True
                    else:
                        cb.SetLabel(f"{tool.display}  [not installed]")
                        cb.Disable()

                cb.Bind(wx.EVT_CHECKBOX, self._on_tool_toggled)
                box.Add(cb, 0, wx.ALL, 4)
                self.tools_checkboxes.append(cb)

            scroll_sizer.Add(box, 0, wx.EXPAND | wx.ALL, 6)

        scroll.SetSizer(scroll_sizer)
        sizer.Add(scroll, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        # Select all / none
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        sel_all = wx.Button(panel, label="Select All")
        sel_all.Bind(wx.EVT_BUTTON, lambda e: self._toggle_all_tools(True))
        btn_row.Add(sel_all, 0, wx.RIGHT, 8)
        sel_none = wx.Button(panel, label="Select None")
        sel_none.Bind(wx.EVT_BUTTON, lambda e: self._toggle_all_tools(False))
        btn_row.Add(sel_none, 0)
        sizer.Add(btn_row, 0, wx.ALL, 12)

        # Include repair scripts checkbox
        self.include_scripts = wx.CheckBox(panel,
            label="Include repair scripts (system report, cache flush, malware check, etc.)")
        self.include_scripts.SetValue(True)
        sizer.Add(self.include_scripts, 0, wx.LEFT | wx.BOTTOM, 12)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  Tools  ")

    # ── Tab 5: Deploy Profile ──

    def _build_deploy_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel, label="Pre-configure macOS install (username, password, settings):")
        lbl.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(lbl, 0, wx.ALL, 12)

        # Profile preset selector
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(panel, label="Preset:"), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.deploy_choice = wx.Choice(panel, size=(300, -1))
        for dp in self.deploy_profiles:
            self.deploy_choice.Append(dp.name)
        self.deploy_choice.SetSelection(0)
        self.deploy_choice.Bind(wx.EVT_CHOICE, self._on_deploy_preset)
        row.Add(self.deploy_choice, 0)
        sizer.Add(row, 0, wx.LEFT | wx.BOTTOM, 12)

        # Fields
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(panel, label="Full Name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.deploy_fullname = wx.TextCtrl(panel, size=(300, -1))
        grid.Add(self.deploy_fullname, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Username:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.deploy_username = wx.TextCtrl(panel, size=(300, -1))
        grid.Add(self.deploy_username, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Password:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.deploy_password = wx.TextCtrl(panel, size=(300, -1))
        grid.Add(self.deploy_password, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Computer Name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.deploy_compname = wx.TextCtrl(panel, size=(300, -1))
        grid.Add(self.deploy_compname, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Timezone:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.deploy_tz = wx.TextCtrl(panel, size=(300, -1))
        grid.Add(self.deploy_tz, 1, wx.EXPAND)

        sizer.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        # Options
        self.deploy_autologin = wx.CheckBox(panel, label="Enable auto-login")
        sizer.Add(self.deploy_autologin, 0, wx.ALL, 12)

        self.deploy_skipsetup = wx.CheckBox(panel, label="Skip Setup Assistant")
        self.deploy_skipsetup.SetValue(True)
        sizer.Add(self.deploy_skipsetup, 0, wx.LEFT | wx.BOTTOM, 12)

        # Save button
        save_row = wx.BoxSizer(wx.HORIZONTAL)
        save_btn = wx.Button(panel, label="Save as Custom Preset")
        save_btn.Bind(wx.EVT_BUTTON, self._on_save_deploy_profile)
        save_row.Add(save_btn, 0)
        sizer.Add(save_row, 0, wx.LEFT | wx.BOTTOM, 12)

        # Info text
        info = wx.StaticText(panel,
            label="This generates a first-boot package (.pkg) that creates the user account\n"
                  "and applies settings when macOS is installed from this drive.\n"
                  "The package is placed on the Tools partition for use with MDS or manual install.")
        info.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        sizer.Add(info, 0, wx.ALL, 12)

        # Load first preset
        self._load_deploy_fields(self.deploy_profiles[0])

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  Deploy  ")

    # ── Tab 6: Build ──

    def _build_build_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(panel, label="Build Summary")
        lbl.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(lbl, 0, wx.ALL, 12)

        self.summary_text = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 140)
        )
        self.summary_text.SetFont(wx.Font(11, wx.FONTFAMILY_TELETYPE,
                                           wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.summary_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.build_gauge = wx.Gauge(panel, range=100, size=(-1, 22))
        sizer.Add(self.build_gauge, 0, wx.EXPAND | wx.ALL, 12)
        self.build_status = wx.StaticText(panel, label="Ready to build")
        sizer.Add(self.build_status, 0, wx.LEFT, 12)

        self.build_log = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 180)
        )
        self.build_log.SetFont(wx.Font(11, wx.FONTFAMILY_TELETYPE,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.build_log, 1, wx.EXPAND | wx.ALL, 12)

        self.build_btn = wx.Button(panel, label="Build Drive", size=(220, 44))
        self.build_btn.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.build_btn.Bind(wx.EVT_BUTTON, self._on_build)
        sizer.Add(self.build_btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 12)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "  Build  ")

    # ── Data Loading ──

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

    # ── Mode ──

    def _on_mode_changed(self, event):
        mode = self.mode_choice.GetSelection()
        if mode == 1:  # Single installer
            # Hide layout tab content, simplify
            self.SetStatusText("Single Installer mode: select one installer and a drive, then build.")
        else:
            self.SetStatusText("Multi-Boot mode: configure a full service drive.")

    # ── Drive Tab ──

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
            f"Recommended: {suggested.name}  --  "
            f"Uses {suggested.total_size_gb():.0f} GB of {drive.display_size}"
        )
        for i, p in enumerate(self.profiles):
            if p.name == suggested.name:
                self.profile_choice.SetSelection(i)
                self._show_layout(p)
                break

    # ── Installers Tab ──

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
            wx.MessageBox("No installers selected.", "Info", wx.OK | wx.ICON_INFORMATION)
            return

        idx = checked[0]
        inst = self.available_installers[idx]
        if inst.downloaded:
            wx.MessageBox(f"{inst.display_name} is already downloaded.", "Info",
                          wx.OK | wx.ICON_INFORMATION)
            return

        self.dl_status.SetLabel(f"Downloading {inst.display_name}...")
        self.dl_gauge.Pulse()

        def download():
            proc = installer_manager.download_installer(inst.version)
            proc.wait()
            wx.PostEvent(self, CompleteEvent({
                "type": "download", "version": inst.version,
                "ok": proc.returncode == 0,
            }))

        threading.Thread(target=download, daemon=True).start()

    # ── Layout Tab ──

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
            f"Total allocated: {profile.total_size_gb():.0f} GB  (+  remainder as free space)"
        )
        self._update_summary()

    # ── Tools Tab ──

    def _on_tool_toggled(self, event):
        cb = event.GetEventObject()
        cb.tool_ref.selected = cb.GetValue()

    def _toggle_all_tools(self, state):
        for cb in self.tools_checkboxes:
            if cb.IsEnabled():
                cb.SetValue(state)
                cb.tool_ref.selected = state

    # ── Deploy Tab ──

    def _on_deploy_preset(self, event):
        idx = self.deploy_choice.GetSelection()
        if idx >= 0:
            self._load_deploy_fields(self.deploy_profiles[idx])

    def _load_deploy_fields(self, dp):
        self.deploy_fullname.SetValue(dp.full_name)
        self.deploy_username.SetValue(dp.username)
        self.deploy_password.SetValue(dp.password)
        self.deploy_compname.SetValue(dp.computer_name)
        self.deploy_tz.SetValue(dp.timezone)
        self.deploy_autologin.SetValue(dp.auto_login)
        self.deploy_skipsetup.SetValue(dp.skip_setup_assistant)

    def _get_deploy_from_fields(self) -> deploy_profile.DeployProfile:
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
            # Add to list if new
            names = [p.name for p in self.deploy_profiles]
            if dp.name not in names:
                self.deploy_profiles.append(dp)
                self.deploy_choice.Append(dp.name)
            wx.MessageBox(f"Profile '{dp.name}' saved.", "Saved", wx.OK | wx.ICON_INFORMATION)

    # ── Build Tab ──

    def _update_summary(self):
        if not self.selected_profile:
            return
        drive_idx = self.drive_choice.GetSelection()
        drive_str = (self.external_drives[drive_idx].display_name
                     if drive_idx >= 0 else "No drive selected")
        mode = "Single Installer" if self.mode_choice.GetSelection() == 1 else "Multi-Boot"

        lines = [
            f"Mode:    {mode}",
            f"Target:  {drive_str}",
            f"Profile: {self.selected_profile.name}",
            "",
        ]

        inst_specs = [s for s in self.selected_profile.partitions if s.purpose == "installer"]
        missing = 0
        for s in inst_specs:
            app = self._find_installer_app(s.installer_version)
            tag = "Ready" if app else "NOT DOWNLOADED"
            if not app:
                missing += 1
            lines.append(f"  {s.name:<35} [{tag}]")

        # Tools summary
        selected_tools = [t for t in self.tool_catalog if t.selected]
        if selected_tools:
            lines.append(f"\n  Tools: {len(selected_tools)} selected")

        # Deploy summary
        dp = self._get_deploy_from_fields()
        if dp.username:
            lines.append(f"  Deploy: {dp.username}@{dp.computer_name or '(auto)'}")

        if missing:
            lines.append(f"\n  {missing} installer(s) not downloaded")

        self.summary_text.SetValue("\n".join(lines))

    def _on_build(self, event):
        drive_idx = self.drive_choice.GetSelection()
        if drive_idx < 0:
            wx.MessageBox("Select a drive first.", "Error", wx.OK | wx.ICON_WARNING)
            return

        drive = self.external_drives[drive_idx]
        mode = self.mode_choice.GetSelection()

        if mode == 1:
            # Single installer mode
            self._build_single_installer(drive)
            return

        if not self.selected_profile:
            wx.MessageBox("Select a profile first.", "Error", wx.OK | wx.ICON_WARNING)
            return

        dlg = wx.MessageDialog(
            self,
            f"This will ERASE ALL DATA on:\n\n"
            f"    {drive.name}\n"
            f"    {drive.display_size}  ({drive.identifier})\n\n"
            f"Profile: {self.selected_profile.name}\n\n"
            f"Continue?",
            "Confirm Erase and Build",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_EXCLAMATION,
        )
        if dlg.ShowModal() != wx.ID_YES:
            return

        if not disk_manager.verify_external(drive.identifier):
            wx.MessageBox("Safety check failed.", "Error", wx.OK | wx.ICON_ERROR)
            return

        self.build_btn.Disable()
        self.build_log.Clear()
        self._log("Starting multi-boot build...")
        self._log(f"Drive: {drive.display_name}")
        self._log(f"Profile: {self.selected_profile.name}")
        self._log("")

        self.build_status.SetLabel("Partitioning drive...")
        self.build_gauge.SetValue(5)

        def do_build():
            import time, os

            # Partition
            self._post_update("log", "Step 1: Partitioning drive...")
            proc = disk_manager.partition_drive(drive.identifier, self.selected_profile.partitions)
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                wx.PostEvent(self, CompleteEvent({
                    "type": "build_error", "error": f"Partitioning failed:\n{stderr}",
                }))
                return

            self._post_update("log", "Partitioning complete.\n")
            time.sleep(3)

            # Flash installers
            inst_specs = [s for s in self.selected_profile.partitions if s.purpose == "installer"]
            self._post_update("log", f"Step 2: Flashing {len(inst_specs)} installers...")

            for i, spec in enumerate(inst_specs):
                app_path = self._find_installer_app(spec.installer_version)
                if not app_path:
                    self._post_update("log", f"  Skipping {spec.name}: not downloaded")
                    continue

                vol = f"/Volumes/{spec.name}"
                if not os.path.exists(vol):
                    self._post_update("log", f"  Skipping {spec.name}: volume not mounted")
                    continue

                pct = 10 + int((i / max(len(inst_specs), 1)) * 70)
                self._post_update("progress", pct)
                self._post_update("status", f"Flashing {spec.name} ({i+1}/{len(inst_specs)})...")
                self._post_update("log", f"  Flashing {spec.name}...")

                from ..core.privilege import run_privileged
                cmd = (
                    f'"{app_path}/Contents/Resources/createinstallmedia" '
                    f'--volume "{vol}" --nointeraction'
                )
                p = run_privileged(cmd)
                p.communicate()

                if p.returncode != 0:
                    self._post_update("log", f"  ERROR flashing {spec.name}")
                else:
                    self._post_update("log", f"  {spec.name}: Done!")

            # Tools
            selected_tools = [t for t in self.tool_catalog if t.selected]
            if selected_tools:
                self._post_update("log", f"\nStep 3: Installing {len(selected_tools)} tools...")
                self._post_update("progress", 85)
                # Find tools partition
                tools_specs = [s for s in self.selected_profile.partitions
                              if s.purpose == "tools"]
                if tools_specs:
                    tools_vol = f"/Volumes/{tools_specs[0].name}"
                    if os.path.exists(tools_vol):
                        for tool in selected_tools:
                            if tool.install_method == "app_copy":
                                tools_manager.copy_app_to_volume(tool.source, tools_vol)
                                self._post_update("log", f"  Copied {tool.name}")
                            elif tool.install_method == "brew":
                                tools_manager.download_brew_to_volume(tool.source, tools_vol)
                                self._post_update("log", f"  Added {tool.name} to install script")

                        if self.include_scripts.GetValue():
                            tools_manager.copy_scripts_to_volume(tools_vol)
                            self._post_update("log", "  Copied repair scripts")

            # Deploy profile
            dp = self._get_deploy_from_fields()
            if dp.username:
                self._post_update("log", f"\nStep 4: Creating deploy package for '{dp.username}'...")
                self._post_update("progress", 92)
                if tools_specs:
                    tools_vol = f"/Volumes/{tools_specs[0].name}"
                    if os.path.exists(tools_vol):
                        pkg_dir = os.path.join(tools_vol, "DriveKit", "packages")
                        os.makedirs(pkg_dir, exist_ok=True)
                        pkg = deploy_profile.generate_firstboot_pkg(dp, pkg_dir)
                        if pkg:
                            self._post_update("log", f"  Created: {os.path.basename(pkg)}")
                        deploy_profile.save_profiles_to_volume([dp], tools_vol)
                        self._post_update("log", "  Saved deploy profile")

            wx.PostEvent(self, CompleteEvent({"type": "build_done"}))

        threading.Thread(target=do_build, daemon=True).start()

    def _build_single_installer(self, drive):
        """Build a single-installer USB drive."""
        # Pick which installer
        downloaded = installer_manager.list_downloaded_installers()
        if not downloaded:
            wx.MessageBox("No installers downloaded.\nGo to Installers tab first.",
                          "Error", wx.OK | wx.ICON_WARNING)
            return

        choices = [f"{d.display_name} ({d.build})" for d in downloaded]
        dlg = wx.SingleChoiceDialog(self, "Select macOS installer:", "Single Installer", choices)
        if dlg.ShowModal() != wx.ID_OK:
            return
        sel_idx = dlg.GetSelection()
        installer = downloaded[sel_idx]

        confirm = wx.MessageDialog(
            self,
            f"This will ERASE ALL DATA on:\n\n"
            f"    {drive.name}\n"
            f"    {drive.display_size}  ({drive.identifier})\n\n"
            f"Installer: {installer.display_name}\n\n"
            f"Continue?",
            "Confirm Erase and Flash",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_EXCLAMATION,
        )
        if confirm.ShowModal() != wx.ID_YES:
            return

        if not disk_manager.verify_external(drive.identifier):
            wx.MessageBox("Safety check failed.", "Error", wx.OK | wx.ICON_ERROR)
            return

        self.build_btn.Disable()
        self.build_log.Clear()
        self._log(f"Single installer: {installer.display_name}")
        self._log(f"Target: {drive.display_name}")
        self._log("")
        self.build_gauge.SetValue(10)
        self.build_status.SetLabel(f"Erasing and flashing {installer.os_name}...")

        def do_single():
            import time

            # Erase the drive with a single HFS+ partition
            from ..core.privilege import run_privileged
            erase_cmd = f'diskutil eraseDisk JHFS+ "Install {installer.os_name}" GPT {drive.identifier}'
            self._post_update("log", "Erasing drive...")
            p = run_privileged(erase_cmd)
            p.communicate()
            if p.returncode != 0:
                wx.PostEvent(self, CompleteEvent({
                    "type": "build_error", "error": "Failed to erase drive",
                }))
                return

            time.sleep(2)
            self._post_update("log", "Flashing installer...")
            self._post_update("progress", 20)

            vol = f'/Volumes/Install {installer.os_name}'
            cmd = (
                f'"{installer.app_path}/Contents/Resources/createinstallmedia" '
                f'--volume "{vol}" --nointeraction'
            )
            p = run_privileged(cmd)
            p.communicate()

            if p.returncode != 0:
                wx.PostEvent(self, CompleteEvent({
                    "type": "build_error", "error": "createinstallmedia failed",
                }))
            else:
                wx.PostEvent(self, CompleteEvent({"type": "build_done"}))

        threading.Thread(target=do_single, daemon=True).start()

    # ── Helpers ──

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

    # ── Thread Event Handlers ──

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
            self._update_summary()

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
