"""
main_window.py: Main application window for Macktechs DriveKit
"""

import logging
import threading
import wx
import wx.lib.scrolledpanel as scrolled

from ..core import installer_manager, disk_manager, profile_manager
from ..core.flash_manager import FlashQueue
from ..models.drive import PartitionSpec
from ..models.profile import DriveProfile
from ..utils.constants import APP_NAME, APP_VERSION

logger = logging.getLogger("drivekit.ui")


# Custom events for thread-safe UI updates
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
            size=(900, 700),
            style=wx.DEFAULT_FRAME_STYLE
        )

        self.available_installers = []
        self.downloaded_installers = []
        self.external_drives = []
        self.selected_profile = None
        self.flash_queue = None

        self._build_ui()
        self._bind_events()
        self.Centre()

        # Initial data load
        wx.CallAfter(self._refresh_all)

    def _build_ui(self):
        self.panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Header
        header = wx.StaticText(self.panel, label=APP_NAME)
        header_font = header.GetFont()
        header_font.SetPointSize(20)
        header_font.SetWeight(wx.FONTWEIGHT_BOLD)
        header.SetFont(header_font)
        main_sizer.Add(header, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        # Notebook (tabs)
        self.notebook = wx.Notebook(self.panel)
        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)

        # Tab 1: Drive Selection
        self._build_drive_tab()

        # Tab 2: Installers
        self._build_installer_tab()

        # Tab 3: Profile / Layout
        self._build_profile_tab()

        # Tab 4: Build
        self._build_build_tab()

        # Status bar
        self.status_bar = self.CreateStatusBar()
        self.status_bar.SetStatusText("Ready")

        self.panel.SetSizer(main_sizer)

    def _build_drive_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Drive selector
        drive_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "External Drives")

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.drive_choice = wx.Choice(panel, size=(500, -1))
        row.Add(self.drive_choice, 1, wx.EXPAND | wx.RIGHT, 5)

        refresh_btn = wx.Button(panel, label="Refresh")
        refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh_drives)
        row.Add(refresh_btn, 0)

        drive_box.Add(row, 0, wx.EXPAND | wx.ALL, 10)

        # Drive info display
        self.drive_info_text = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 200)
        )
        self.drive_info_text.SetFont(wx.Font(12, wx.FONTFAMILY_TELETYPE,
                                              wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        drive_box.Add(self.drive_info_text, 1, wx.EXPAND | wx.ALL, 10)

        sizer.Add(drive_box, 1, wx.EXPAND | wx.ALL, 10)

        # Recommended profile
        rec_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Recommended Setup")
        self.recommendation_text = wx.StaticText(panel, label="Select a drive to see recommendations")
        rec_box.Add(self.recommendation_text, 0, wx.ALL, 10)
        sizer.Add(rec_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "Drive")

    def _build_installer_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Available installers
        inst_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "macOS Installers")

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        fetch_btn = wx.Button(panel, label="Fetch Available Versions")
        fetch_btn.Bind(wx.EVT_BUTTON, self._on_fetch_installers)
        btn_row.Add(fetch_btn, 0, wx.RIGHT, 5)

        self.download_btn = wx.Button(panel, label="Download Selected")
        self.download_btn.Bind(wx.EVT_BUTTON, self._on_download_selected)
        self.download_btn.Disable()
        btn_row.Add(self.download_btn, 0)

        inst_box.Add(btn_row, 0, wx.ALL, 10)

        # Installer list with checkboxes
        self.installer_list = wx.CheckListBox(panel, size=(-1, 350))
        inst_box.Add(self.installer_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        sizer.Add(inst_box, 1, wx.EXPAND | wx.ALL, 10)

        # Download progress
        self.download_gauge = wx.Gauge(panel, range=100, size=(-1, 20))
        sizer.Add(self.download_gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.download_status = wx.StaticText(panel, label="")
        sizer.Add(self.download_status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "Installers")

    def _build_profile_tab(self):
        panel = scrolled.ScrolledPanel(self.notebook)
        panel.SetupScrolling()
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Profile selector
        prof_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Drive Profile")

        row = wx.BoxSizer(wx.HORIZONTAL)
        wx.StaticText(panel, label="Profile:").SetMinSize((60, -1))
        row.Add(wx.StaticText(panel, label="Profile: "), 0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.profile_choice = wx.Choice(panel, size=(400, -1))
        self.profile_choice.Bind(wx.EVT_CHOICE, self._on_profile_selected)
        row.Add(self.profile_choice, 1, wx.EXPAND)
        prof_box.Add(row, 0, wx.EXPAND | wx.ALL, 10)

        self.profile_desc = wx.StaticText(panel, label="")
        prof_box.Add(self.profile_desc, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        sizer.Add(prof_box, 0, wx.EXPAND | wx.ALL, 10)

        # Partition layout display
        layout_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Partition Layout")
        self.layout_list = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(-1, 300)
        )
        self.layout_list.InsertColumn(0, "Name", width=250)
        self.layout_list.InsertColumn(1, "Format", width=80)
        self.layout_list.InsertColumn(2, "Size", width=80)
        self.layout_list.InsertColumn(3, "Purpose", width=120)
        self.layout_list.InsertColumn(4, "OS Version", width=100)
        layout_box.Add(self.layout_list, 1, wx.EXPAND | wx.ALL, 10)

        # Total size indicator
        self.total_size_label = wx.StaticText(panel, label="Total: 0 GB")
        layout_box.Add(self.total_size_label, 0, wx.LEFT | wx.BOTTOM, 10)

        sizer.Add(layout_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "Layout")

    def _build_build_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Summary
        summary_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Build Summary")
        self.summary_text = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 150)
        )
        self.summary_text.SetFont(wx.Font(12, wx.FONTFAMILY_TELETYPE,
                                           wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        summary_box.Add(self.summary_text, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(summary_box, 0, wx.EXPAND | wx.ALL, 10)

        # Progress
        progress_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Progress")
        self.build_gauge = wx.Gauge(panel, range=100, size=(-1, 25))
        progress_box.Add(self.build_gauge, 0, wx.EXPAND | wx.ALL, 10)
        self.build_status = wx.StaticText(panel, label="Ready to build")
        progress_box.Add(self.build_status, 0, wx.LEFT | wx.BOTTOM, 10)

        # Per-operation log
        self.build_log = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 200)
        )
        self.build_log.SetFont(wx.Font(11, wx.FONTFAMILY_TELETYPE,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        progress_box.Add(self.build_log, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        sizer.Add(progress_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Build button
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self.build_btn = wx.Button(panel, label="Build Drive", size=(200, 40))
        self.build_btn.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT,
                                        wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.build_btn.Bind(wx.EVT_BUTTON, self._on_build)
        btn_row.Add(self.build_btn, 0, wx.ALIGN_CENTER)
        sizer.Add(btn_row, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "Build")

    def _bind_events(self):
        self.drive_choice.Bind(wx.EVT_CHOICE, self._on_drive_selected)
        self.Connect(-1, -1, EVT_UPDATE_ID, self._on_thread_update)
        self.Connect(-1, -1, EVT_COMPLETE_ID, self._on_thread_complete)

    # --- Data Loading ---

    def _refresh_all(self):
        self._load_profiles()
        self._load_downloaded_installers()
        self._refresh_drives()

    def _refresh_drives(self):
        self.status_bar.SetStatusText("Scanning for external drives...")
        self.external_drives = disk_manager.list_external_drives()
        self.drive_choice.Clear()
        for drive in self.external_drives:
            self.drive_choice.Append(drive.display_name)
        if self.external_drives:
            self.drive_choice.SetSelection(0)
            self._update_drive_info(0)
        self.status_bar.SetStatusText(
            f"Found {len(self.external_drives)} external drive(s)"
        )

    def _load_profiles(self):
        profiles = profile_manager.get_builtin_profiles()
        self.profiles = profiles
        self.profile_choice.Clear()
        for p in profiles:
            self.profile_choice.Append(p.name)

    def _load_downloaded_installers(self):
        self.downloaded_installers = installer_manager.list_downloaded_installers()

    # --- Event Handlers ---

    def _on_refresh_drives(self, event):
        self._refresh_drives()

    def _on_drive_selected(self, event):
        idx = self.drive_choice.GetSelection()
        if idx >= 0:
            self._update_drive_info(idx)

    def _update_drive_info(self, idx):
        drive = self.external_drives[idx]

        # Show drive details
        lines = [
            f"Drive:      {drive.name}",
            f"Identifier: {drive.identifier}",
            f"Size:       {drive.display_size}",
            f"Protocol:   {drive.protocol}",
            f"",
            f"Current Partitions:",
            f"{'─' * 50}",
        ]
        for part in drive.partitions:
            lines.append(f"  {part.name:<30} {part.display_size:>8}  ({part.type})")

        self.drive_info_text.SetValue("\n".join(lines))

        # Recommend a profile
        suggested = profile_manager.suggest_profile(drive.size_gb)
        self.recommendation_text.SetLabel(
            f"Recommended: {suggested.name}\n{suggested.description}\n"
            f"Uses {suggested.total_size_gb():.0f} GB of {drive.display_size}"
        )

        # Auto-select the profile
        for i, p in enumerate(self.profiles):
            if p.name == suggested.name:
                self.profile_choice.SetSelection(i)
                self._update_layout(p)
                break

    def _on_profile_selected(self, event):
        idx = self.profile_choice.GetSelection()
        if idx >= 0:
            profile = self.profiles[idx]
            self._update_layout(profile)

    def _update_layout(self, profile: DriveProfile):
        self.selected_profile = profile
        self.profile_desc.SetLabel(profile.description)
        self.layout_list.DeleteAllItems()

        for i, spec in enumerate(profile.partitions):
            idx = self.layout_list.InsertItem(i, spec.name)
            self.layout_list.SetItem(idx, 1, spec.format)
            self.layout_list.SetItem(idx, 2,
                                      f"{spec.size_gb:.0f} GB" if spec.size_gb > 0 else "Remainder")
            self.layout_list.SetItem(idx, 3, spec.purpose)
            self.layout_list.SetItem(idx, 4, spec.installer_version or "")

        total = profile.total_size_gb()
        self.total_size_label.SetLabel(f"Total allocated: {total:.0f} GB (+ remainder as free space)")

        # Update build summary
        self._update_build_summary()

    def _on_fetch_installers(self, event):
        self.status_bar.SetStatusText("Fetching available installers from Apple...")
        self.installer_list.Clear()

        def fetch():
            installers = installer_manager.list_available_installers()
            # Get only latest per major version
            latest = installer_manager.get_latest_per_major(installers)
            wx.PostEvent(self, CompleteEvent({"type": "fetch_installers", "data": latest}))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_download_selected(self, event):
        checked = self.installer_list.GetCheckedItems()
        if not checked:
            wx.MessageBox("No installers selected", "Nothing to download",
                          wx.OK | wx.ICON_INFORMATION)
            return

        # Download first checked item (sequential for now)
        idx = checked[0]
        installer = self.available_installers[idx]
        if installer.downloaded:
            wx.MessageBox(f"{installer.display_name} is already downloaded",
                          "Already Downloaded", wx.OK | wx.ICON_INFORMATION)
            return

        self.download_status.SetLabel(f"Downloading {installer.display_name}...")
        self.download_gauge.Pulse()

        def download():
            proc = installer_manager.download_installer(installer.version)
            proc.wait()
            wx.PostEvent(self, CompleteEvent({
                "type": "download",
                "version": installer.version,
                "returncode": proc.returncode,
            }))

        threading.Thread(target=download, daemon=True).start()

    def _on_build(self, event):
        # Validate
        drive_idx = self.drive_choice.GetSelection()
        if drive_idx < 0:
            wx.MessageBox("Please select a drive", "No Drive Selected",
                          wx.OK | wx.ICON_WARNING)
            return

        if not self.selected_profile:
            wx.MessageBox("Please select a profile", "No Profile Selected",
                          wx.OK | wx.ICON_WARNING)
            return

        drive = self.external_drives[drive_idx]

        # Safety confirmation
        msg = (
            f"WARNING: This will ERASE ALL DATA on:\n\n"
            f"  {drive.name}\n"
            f"  {drive.display_size} — {drive.identifier}\n\n"
            f"Profile: {self.selected_profile.name}\n\n"
            f"This cannot be undone. Continue?"
        )
        dlg = wx.MessageDialog(self, msg, "Confirm Erase and Build",
                                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_EXCLAMATION)
        if dlg.ShowModal() != wx.ID_YES:
            return

        # Verify external
        if not disk_manager.verify_external(drive.identifier):
            wx.MessageBox("Safety check failed: drive may not be external",
                          "Safety Error", wx.OK | wx.ICON_ERROR)
            return

        self.build_btn.Disable()
        self.build_log.Clear()
        self._log_build("Starting build...")
        self._log_build(f"Drive: {drive.display_name}")
        self._log_build(f"Profile: {self.selected_profile.name}")
        self._log_build("")

        # Step 1: Partition the drive
        self._log_build("Step 1: Partitioning drive...")
        self.build_status.SetLabel("Partitioning drive...")
        self.build_gauge.SetValue(5)

        def do_build():
            import tempfile, os, time

            # Partition
            proc = disk_manager.partition_drive(
                drive.identifier, self.selected_profile.partitions
            )
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                wx.PostEvent(self, CompleteEvent({
                    "type": "build_error",
                    "error": f"Partitioning failed: {stderr}",
                }))
                return

            wx.PostEvent(self, UpdateEvent({"step": "partition_done"}))

            # Wait for volumes to mount
            time.sleep(3)

            # Step 2: Flash installers
            installer_specs = [
                s for s in self.selected_profile.partitions
                if s.purpose == "installer"
            ]

            for i, spec in enumerate(installer_specs):
                # Find the downloaded installer for this version
                app_path = self._find_installer_app(spec.installer_version)
                if not app_path:
                    wx.PostEvent(self, UpdateEvent({
                        "step": "skip_installer",
                        "name": spec.name,
                        "reason": "Installer not downloaded",
                    }))
                    continue

                # Find the volume mount point
                vol_path = f"/Volumes/{spec.name}"
                if not os.path.exists(vol_path):
                    wx.PostEvent(self, UpdateEvent({
                        "step": "skip_installer",
                        "name": spec.name,
                        "reason": f"Volume not found at {vol_path}",
                    }))
                    continue

                wx.PostEvent(self, UpdateEvent({
                    "step": "flash_start",
                    "name": spec.name,
                    "index": i,
                    "total": len(installer_specs),
                }))

                # Flash it
                from ..core.privilege import run_privileged
                cmd = (
                    f'"{app_path}/Contents/Resources/createinstallmedia" '
                    f'--volume "{vol_path}" --nointeraction'
                )
                flash_proc = run_privileged(cmd)
                flash_stdout, flash_stderr = flash_proc.communicate()

                if flash_proc.returncode != 0:
                    wx.PostEvent(self, UpdateEvent({
                        "step": "flash_error",
                        "name": spec.name,
                        "error": flash_stderr or "Unknown error",
                    }))
                else:
                    wx.PostEvent(self, UpdateEvent({
                        "step": "flash_done",
                        "name": spec.name,
                    }))

            wx.PostEvent(self, CompleteEvent({"type": "build_complete"}))

        threading.Thread(target=do_build, daemon=True).start()

    def _find_installer_app(self, major_version: str) -> str:
        """Find the installer .app path for a major version."""
        from ..utils.constants import OS_NAMES
        os_name = OS_NAMES.get(major_version, "")
        if not os_name:
            return ""

        from pathlib import Path
        for app in Path("/Applications").glob("Install macOS*.app"):
            if os_name.lower() in app.name.lower():
                create_media = app / "Contents" / "Resources" / "createinstallmedia"
                if create_media.exists():
                    return str(app)
        return ""

    # --- Thread-safe UI Updates ---

    def _on_thread_update(self, event):
        data = event.data
        step = data.get("step", "")

        if step == "partition_done":
            self._log_build("Partitioning complete!")
            self._log_build("")
            self._log_build("Step 2: Flashing installers...")
            self.build_gauge.SetValue(15)

        elif step == "flash_start":
            name = data["name"]
            idx = data["index"]
            total = data["total"]
            self._log_build(f"  Flashing {name} ({idx + 1}/{total})...")
            self.build_status.SetLabel(f"Flashing {name}...")
            progress = 15 + int((idx / total) * 80)
            self.build_gauge.SetValue(progress)

        elif step == "flash_done":
            self._log_build(f"  {data['name']}: Done!")

        elif step == "flash_error":
            self._log_build(f"  {data['name']}: ERROR - {data['error']}")

        elif step == "skip_installer":
            self._log_build(f"  Skipping {data['name']}: {data['reason']}")

    def _on_thread_complete(self, event):
        data = event.data
        event_type = data.get("type", "")

        if event_type == "fetch_installers":
            self.available_installers = data["data"]
            self.installer_list.Clear()
            for inst in self.available_installers:
                label = str(inst)
                self.installer_list.Append(label)
            # Check items that aren't downloaded
            for i, inst in enumerate(self.available_installers):
                if not inst.downloaded:
                    pass  # Leave unchecked
            self.download_btn.Enable()
            self.status_bar.SetStatusText(
                f"Found {len(self.available_installers)} latest installers"
            )

        elif event_type == "download":
            self.download_gauge.SetValue(100)
            if data["returncode"] == 0:
                self.download_status.SetLabel(
                    f"Download complete: macOS {data['version']}"
                )
                self._load_downloaded_installers()
            else:
                self.download_status.SetLabel(
                    f"Download failed for macOS {data['version']}"
                )

        elif event_type == "build_complete":
            self.build_gauge.SetValue(100)
            self.build_status.SetLabel("Build complete!")
            self._log_build("")
            self._log_build("=" * 40)
            self._log_build("BUILD COMPLETE!")
            self._log_build("=" * 40)
            self.build_btn.Enable()
            wx.MessageBox(
                "Drive build complete!\n\nYour service drive is ready to use.",
                "Build Complete", wx.OK | wx.ICON_INFORMATION
            )

        elif event_type == "build_error":
            self.build_gauge.SetValue(0)
            self.build_status.SetLabel("Build failed!")
            self._log_build(f"\nERROR: {data['error']}")
            self.build_btn.Enable()
            wx.MessageBox(
                f"Build failed:\n\n{data['error']}",
                "Build Error", wx.OK | wx.ICON_ERROR
            )

    def _log_build(self, message: str):
        self.build_log.AppendText(message + "\n")
        logger.info(message)

    def _update_build_summary(self):
        if not self.selected_profile:
            return

        drive_idx = self.drive_choice.GetSelection()
        drive_name = self.external_drives[drive_idx].display_name if drive_idx >= 0 else "No drive selected"

        lines = [
            f"Target Drive: {drive_name}",
            f"Profile: {self.selected_profile.name}",
            f"",
            f"Operations:",
            f"  1. Erase and partition drive ({len(self.selected_profile.partitions)} partitions)",
        ]

        installer_specs = [
            s for s in self.selected_profile.partitions if s.purpose == "installer"
        ]
        for i, spec in enumerate(installer_specs):
            app = self._find_installer_app(spec.installer_version)
            status = "Ready" if app else "NOT DOWNLOADED"
            lines.append(f"  {i + 2}. Flash {spec.name} [{status}]")

        missing = sum(
            1 for s in installer_specs if not self._find_installer_app(s.installer_version)
        )
        if missing:
            lines.append(f"\n  WARNING: {missing} installer(s) not downloaded!")
            lines.append(f"  Go to the Installers tab to download them first.")

        self.summary_text.SetValue("\n".join(lines))
