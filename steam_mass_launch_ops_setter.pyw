#!/usr/bin/env python3
"""Steam Library mass launch options setter

Set the launch options for all your Steam apps to the same thing.

Copyright 2025 Wilbur Jaywright d.b.a. Marswide BGL.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

S.D.G."""

import glob
import os
from os import path as op
import platform
import sys
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as mb
import vdf

DEFAULT_ENC = "utf-8"

NEW_OPTION = "obs-gamecapture %command%"
OVERWRITE = False
STEAM_DIR_DEF = op.expanduser({
    "Linux": "~/.steam/steam",
    "Windows": r"C:\Program Files (x86)\Steam",
    "Darwin": "~/Library/Application Support/Steam",
    }[platform.system()])

STEAM_DIR = os.environ.get("STEAM_DIR", STEAM_DIR_DEF)
USERDATA_DIR = op.join(STEAM_DIR, "userdata")

if not op.exists(USERDATA_DIR):
    mb.showerror(
        "Invalid path",
        "Could not find the Steam/userdata folder. " +
        "Try setting the STEAM_DIR environment variable.",
        )
    sys.exit(1)


class MainWindow(tk.Tk):
    """The main GUI window"""

    def __init__(self):
        """The main GUI window"""
        super().__init__()

        self.title("Steam Launch Options Setter")

        # User local ids to loaded data pairs
        self.user_datas = {}

        # Username to local ID pairs
        self.user_local_ids = {}

        # Variables used by the widgets
        self.user_choice = tk.StringVar(self)
        self.statistics = tk.StringVar(self, "No user selected")
        self.overwrite = tk.BooleanVar(self)

        self.scan_for_users()

        self.build()
        self.refresh_statistics()
        self.mainloop()

    def get_config_file_path(self, loc_user_id: str) -> str:
        """Get the path to the config file for a given user

        Args:
            loc_user_id (str): The local user ID (folder name).

        Returns:
            path (str): The complete path to the file."""

        return op.join(
            USERDATA_DIR,
            loc_user_id,
            "config",
            "localconfig.vdf",
            )

    def load_user_config(self, loc_user_id: str) -> dict:
        """Read and parse the config file for a given user, and save it to
            memory

        Args:
            loc_user_id (str): The local user ID (folder name)."""

        with open(self.get_config_file_path(loc_user_id), encoding=DEFAULT_ENC) as f:
            data = vdf.load(f)
        self.user_local_ids[data["UserLocalConfigStore"]["friends"][loc_user_id]["name"]] = loc_user_id
        self.user_datas[loc_user_id] = data

    @property
    def cur_loc_id(self):
        """The currently selected user's local ID"""
        return self.user_local_ids[self.user_choice.get()]

    @property
    def cur_appconfs(self):
        """The app subdictionary of the currently selected user's config"""
        return self.user_datas[self.cur_loc_id]["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"]

    def build(self):
        """Construct the GUI"""
        # User selection
        ttk.Label(self, text="User:", anchor=tk.E).grid(row=0, column=0, sticky=tk.NSEW)
        users = tuple(self.user_local_ids.keys())
        self.user_chooser = ttk.OptionMenu(self, self.user_choice, users[0], *users, command=self.on_user_select)
        self.user_chooser.grid(row=0, column=1, sticky=tk.NSEW)

        # Statistics display
        ttk.Label(self, textvariable=self.statistics).grid(row=1, column=0, columnspan=2, sticky=tk.NSEW)

        # Options entry
        ttk.Label(self, text="Launch options:", anchor=tk.E).grid(row=2, column=0, sticky=tk.NSEW)
        self.ops_entry = tk.Entry(self)
        self.ops_entry.grid(row=2, column=1, sticky=tk.NSEW)

        # Overwrite
        ttk.Checkbutton(self, text="Overwrite", variable=self.overwrite).grid(row=3, column=0, columnspan=2, sticky=tk.NS + tk.W)

        # Go!
        ttk.Button(self, text="Set", command=self.set_launch_options).grid(row=4, column=0, columnspan=2)

        # Allow for expansion
        for row in range(5):
            self.rowconfigure(row, weight=1)
        self.columnconfigure(1, weight=1)

        # Lock built size as minimum
        self.update()
        self.minsize(self.winfo_width(), self.winfo_height())

    def scan_for_users(self):
        """Find all user folders and the user name they represent"""

        # Clear existing scan
        self.user_local_ids = {}
        self.user_datas = {}

        for loc_user_id in glob.glob("*", root_dir=USERDATA_DIR):
            self.load_user_config(loc_user_id)

        # No users were found
        if not self.user_local_ids:
            mb.showerror(
                "No users found",
                "There were no user data directories at the Steam location. Is Steam logged out?"
                )
            self.destroy()
            sys.exit(1)

    def on_user_select(self, e):
        """Refresh stuff based on a new user selection"""

        print(f"User `{e}` selected.")

        # Make sure our data on the user is up to date
        self.load_user_config(self.cur_loc_id)

        self.refresh_statistics()

    def refresh_statistics(self):
        """Refresh the statistics display"""

        have_ops = len([
            appconf for appid, appconf in self.cur_appconfs.items()
            if "LaunchOptions" in appconf
            ])

        self.statistics.set(f"{len(self.cur_appconfs):,} games, {have_ops:,} of which have set launch options.")

    def set_launch_options(self):
        """Start off the actual setting process"""

        # Make sure our data on the user is up to date
        self.load_user_config(self.cur_loc_id)

        new_option = self.ops_entry.get()
        altered = 0

        # Go through the launch options for every Steam app
        for appid, appconf in self.cur_appconfs.items():

            # There are existing options
            if "LaunchOptions" in appconf:
                ops = appconf["LaunchOptions"]

                # This is not an erasing
                if new_option:
                    # The existing options are different than what we want to put
                    if ops != new_option:
                        print("Game with ID", appid, "already has launch options:")
                        print(f"\t`{ops}`")

                        # We are to overwrite
                        if OVERWRITE:
                            appconf["LaunchOptions"] = new_option
                            altered += 1

                # This is an erasing, delete the options
                else:
                    del appconf["LaunchOptions"]
                    altered += 1

            # This is not an erasing and there are no previous options
            elif new_option:
                appconf["LaunchOptions"] = new_option
                altered += 1

        # No changes were made
        if not altered:
            mb.showerror("No changes made", "None of the launch options were altered.")

        # Some changes were made
        else:
            with open(self.get_config_file_path(self.cur_loc_id), "w", encoding=DEFAULT_ENC) as f:
                vdf.dump(self.user_datas[self.cur_loc_id], f, pretty=True)
            mb.showinfo("Changes made", f"Wrote changes for {altered:,} Steam apps.")

        self.refresh_statistics()


MainWindow()
