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

DEFAULT_ENC = sys.getdefaultencoding()  # Usually UTF-8

# Get the usual system location of Steam
DEFAULT_STEAM_DIR = op.expanduser({
    "Linux": "~/.steam/steam",
    "Windows": r"C:\Program Files (x86)\Steam",
    "Darwin": "~/Library/Application Support/Steam",
    }[platform.system()])

# Allow the user to override the Steam location
# This environment variable is the same one Protontricks uses
STEAM_DIR = os.environ.get("STEAM_DIR", DEFAULT_STEAM_DIR)

# The Steam user data folder
USERDATA_DIR = op.join(STEAM_DIR, "userdata")

# Padding for GUI widgets
PAD = 10

# If the Steam user data folder does not exist, we have the wrong Steam path
if not op.exists(USERDATA_DIR):
    # If the user did not set STEAM_DIR, suggest they do
    # Assumes that they did not explicitly set it to the default
    if STEAM_DIR == DEFAULT_STEAM_DIR:
        secondhalf = "Try setting the STEAM_DIR environment variable."
    # If the user set STEAM_DIR, it's pointing to the wrong place
    else:
        secondhalf = "STEAM_DIR environment variable is set to an invalid path."

    # Show the error, and exit with a failure status
    mb.showerror(
        "Invalid path",
        "Could not find the Steam/userdata folder. " +
        secondhalf,
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
        self.launch_options = tk.StringVar(self)
        self.launch_options.trace_add("write", lambda *args: self.__on_launch_ops_edit())

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

        # Read the user config file
        with open(self.get_config_file_path(loc_user_id), encoding=DEFAULT_ENC) as f:
            data = vdf.load(f)

        # We can find out the user's name from their friends list
        # For some reason, a user is always marked as a friend of themselves
        self.user_local_ids[data["UserLocalConfigStore"]["friends"][loc_user_id]["name"]] = loc_user_id

        # Save the user data to our application memory
        self.user_datas[loc_user_id] = data

    @property
    def cur_loc_id(self):
        """The currently selected user's local ID"""
        # The user chooser works with display names
        return self.user_local_ids[self.user_choice.get()]

    @property
    def cur_appconfs(self):
        """The app subdictionary of the currently selected user's config"""
        return self.user_datas[self.cur_loc_id]["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"]

    def build(self):
        """Construct the GUI"""
        # Main frame for theming
        self.frame = ttk.Frame(self)
        self.frame.grid(padx=PAD, pady=PAD, sticky=tk.NSEW)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # User selection
        ttk.Label(self.frame, text="User:", anchor=tk.E).grid(row=0, column=0, sticky=tk.NSEW)
        users = tuple(self.user_local_ids.keys())
        self.user_chooser = ttk.OptionMenu(self.frame, self.user_choice, users[0], *users, command=self.__on_user_select)
        self.user_chooser.grid(row=0, column=1, sticky=tk.NSEW)

        # Statistics display
        ttk.Label(self.frame, textvariable=self.statistics).grid(row=1, column=0, columnspan=2, pady=[PAD, 0], sticky=tk.NSEW)

        # Options entry
        ttk.Label(self.frame, text="Launch options:", anchor=tk.E).grid(row=2, column=0, pady=[PAD, 0], sticky=tk.NSEW)
        ttk.Entry(self.frame, textvariable=self.launch_options).grid(row=2, column=1, pady=[PAD, 0], sticky=tk.NSEW)

        # Overwrite
        self.overwrite_checkbttn = ttk.Checkbutton(self.frame, text="Overwrite", variable=self.overwrite)
        self.overwrite_checkbttn.grid(row=3, column=0, columnspan=2, pady=[PAD, 0], sticky=tk.NS + tk.W)
        self.overwrite_checkbttn.configure(state=tk.DISABLED)

        # Go!
        ttk.Button(self.frame, text="Set", command=self.set_launch_options).grid(row=4, column=0, pady=[PAD, 0], columnspan=2)

        # Allow for expansion
        for row in range(5):
            self.frame.rowconfigure(row, weight=1)
        self.frame.columnconfigure(1, weight=1)

        # Lock built size as minimum
        self.update()
        self.minsize(self.winfo_width(), self.winfo_height())

    def scan_for_users(self):
        """Find all user folders and the user name they represent"""

        # Clear existing application memory
        self.user_local_ids = {}
        self.user_datas = {}

        # Find all user config files by path, and load them
        for loc_user_id in glob.glob("*", root_dir=USERDATA_DIR):
            self.load_user_config(loc_user_id)

        # No users were found
        if not self.user_local_ids:
            mb.showerror(
                "No users found",
                "There were no user data directories at the Steam location. Is Steam logged out?"
                )
            # The app cannot continue if this happens
            # TODO: This guarantees that the method is only called at launch
            self.destroy()
            sys.exit(1)

    def __on_launch_ops_edit(self):
        """The launch options field has been edited"""
        # The overwrite checkbutton should be disabled if the option field is empty
        self.overwrite_checkbttn.configure(
            state=(tk.DISABLED, tk.NORMAL)[bool(self.launch_options.get())]
            )

    def __on_user_select(self, e):
        """A new user has been selected in the GUI"""

        print(f"User `{e}` selected.")

        # Make sure our data on the user is up to date
        self.load_user_config(self.cur_loc_id)

        self.refresh_statistics()

    def refresh_statistics(self):
        """Refresh the statistics display"""

        # Go through the apps, check if they have launch options,
        # and count the list of resulting app IDs
        have_ops = len([
            appid for appid, appconf in self.cur_appconfs.items()
            if appconf.get("LaunchOptions")
            ])

        # Update the GUI statistics string
        self.statistics.set(f"{len(self.cur_appconfs):,} games, {have_ops:,} of which have set launch options.")

    def set_launch_options(self):
        """Start off the actual setting process"""

        # Make sure our data on the user is up to date
        self.load_user_config(self.cur_loc_id)

        # Grab the new option from the GUI
        new_option = self.launch_options.get()
        altered = 0

        # Go through the launch options for every Steam app
        for appid, appconf in self.cur_appconfs.items():
            old_ops = appconf.get("LaunchOptions")
            # The config has existing options
            if old_ops:
                # This is not an erasing
                if new_option:
                    # The existing options are different than what we want to put
                    if old_ops != new_option:
                        print("Game with ID", appid, "already has launch options:")
                        print(f"\t`{old_ops}`")

                        # We are to overwrite
                        if self.overwrite.get():
                            appconf["LaunchOptions"] = new_option
                            altered += 1

                # This is an erasing and an options key exists, delete it
                elif old_ops is not None:
                    del appconf["LaunchOptions"]
                    altered += 1

                # The only remaining case is that this is an erasing
                # and there was no options key

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
sys.exit(0)
