import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
from collections import defaultdict
import re
import json
import platform
import sys

def print_env_info():
    print("Python version:", sys.version)
    print("Platform:", platform.system())
    print("Platform version:", platform.version())
    print("Architecture:", platform.architecture())
    print("Tkinter version:", tk.TkVersion)
    
print_env_info()

SPELL_CLASSES = [
    "bard", "cleric", "druid", "paladin", "ranger",
    "sorcerer", "warlock", "wizard", "artificer"
]

STATS = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
CHECKS = {
    "Strength": ["Athletics"],
    "Dexterity": ["Acrobatics", "Sleight of Hand", "Stealth"],
    "Constitution": [],
    "Intelligence": ["Arcana", "History", "Investigation", "Nature", "Religion"],
    "Wisdom": ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
    "Charisma": ["Deception", "Intimidation", "Performance", "Persuasion"]
}

spell_point_costs = {
    "Cantrip": 0,
    "1st": 2,
    "2nd": 3,
    "3rd": 5,
    "4th": 6,
    "5th": 7,
    "6th": 9,
    "7th": 10,
    "8th": 11,
    "9th": 13,
}

ALL_METAMAGIC = {
    "Careful Spell": ["Protect allies from your area spells.",
                      "Protect chosen creatures from effects of your area spells, making them auto-succeed on saves and avoid half damage."],
    "Distant Spell": ["Double spell range or extend touch.",
                      "Spend 1 point to double range or cast touch spells from 30 feet."],
    "Empowered Spell": ["Reroll damage dice.",
                        "Spend 1 point to reroll a number of damage dice equal to your Charisma modifier."],
    "Extended Spell": ["Double duration.",
                       "Spend 1 point to double spell duration up to 24 hours."],
    "Heightened Spell": ["Disadvantage on save.",
                         "Spend 3 points to give a creature disadvantage on its first saving throw against your spell."],
    "Quickened Spell": ["Cast as bonus action.",
                        "Spend 2 points to change a spell's casting time from 1 action to 1 bonus action."],
    "Seeking Spell": ["Reroll missed spell attack.",
                      "Spend 2 points to reroll a missed spell attack roll."],
    "Subtle Spell": ["No components.",
                     "Spend 1 point to cast a spell without verbal or somatic components."],
    "Transmuted Spell": ["Change damage type.",
                         "Spend 1 point to change a spell's elemental damage type (acid, fire, etc.)."],
    "Twinned Spell": ["Target a second creature.",
                      "Spend Sorcery Points equal to the spell's level to target a second creature."]
}

class CharacterUI:
    def __init__(self, root):
        self.root = root
        self.csv_path = os.path.join(os.path.dirname(__file__), 'character_data.csv')
        root.title("D&D Character Spellbook & Sorcery Tracker")

        # Track resources
        self.stat_vars = {stat: tk.IntVar(value=10) for stat in STATS}
        self.exp = tk.IntVar(value=0)
        self.level = tk.IntVar(value=1)
        self.hp = tk.IntVar(value=32)
        self.temp_hp = tk.IntVar(value=0)
        self.ac = tk.IntVar(value=12)
        self.speed = tk.IntVar(value=30)
        self.spell_points = tk.IntVar(value=6)
        self.actions = tk.IntVar(value=2)
        self.sorcery_points = tk.IntVar(value=6)
        # D&D 5e XP thresholds (index = level, value = XP to reach that level)
        self.exp_thresholds = [0, 300, 900, 2700, 6500, 14000, 23000,
                            34000, 48000, 64000, 85000, 100000, 120000,
                            140000, 165000, 195000, 225000, 265000, 305000, 355000, float('inf')]
        self.inventory_items = {}  # Track inventory items
        self.max_values = {
            "EXP": tk.IntVar(value=self.exp_thresholds[self.level.get()]),
            "HP": tk.IntVar(value=10),
            "Spell Points": tk.IntVar(value=10),
            "Sorcery Points": tk.IntVar(value=6),
            "Temp HP": tk.IntVar(value=0),
            "AC": tk.IntVar(value=12),
        }

        # Spells are now loaded from CSV, starting with an empty dictionary
        self.spells = {0: [], 1: [], 2: [], 3: [], 4: [], 5: []}
        self.spell_notebook = ttk.Notebook(self.root)
        self.main_spell_notebook = ttk.Notebook(self.root)
        self.inventory_notebook = ttk.Notebook(self.root)
        self.traits_and_feats = ttk.Notebook(self.root)
        
        self.exp.trace_add("write", self.check_level_up)
        self.create_widgets()
        self.load_from_csv()  # Load data from CSV when the app starts
        
    def check_level_up(self, *_):
        current_exp = self.exp.get()
        current_level = self.level.get()
        if current_exp >= self.exp_thresholds[current_level]:
            self.level.set(current_level + 1)
            self.exp.set(0)
            self.max_values["EXP"].set(self.exp_thresholds[self.level.get()])
            print(f"Level Up! Now level {self.level.get()}.")

    def open_checks_window(self):
        win = tk.Toplevel(self.root)
        win.title("Ability Checks")
        filename = "character_data.csv"
        path = os.path.join(os.path.dirname(__file__), filename)
        search_var = tk.StringVar()

        # Load proficient skills and saving throws from CSV
        proficient_skills = set()
        proficient_saves = set()
        try:
            with open(path, newline='') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row[0] == "Info" and row[1] == "Skills":
                        proficient_skills = set(skill.strip().lower() for skill in row[2].split(","))
                    elif row[0] == "Info" and row[1] == "Saving Throws":
                        proficient_saves = set(stat.strip().lower() for stat in row[2].split(","))
        except FileNotFoundError:
            print("character_data.csv not found.")

        proficiency_bonus = 2
        text_font = ("TkDefaultFont", 10)
        bold_font = ("TkDefaultFont", 10, "bold")

        def update_check_list():
            target = search_var.get().lower()

            # Clear both columns
            skill_text.config(state=tk.NORMAL)
            skill_text.delete("1.0", tk.END)
            save_text.config(state=tk.NORMAL)
            save_text.delete("1.0", tk.END)

            # Update saving throws
            for stat in self.stat_vars:
                base = (self.stat_vars[stat].get() - 10) // 2
                is_proficient = stat.lower() in proficient_saves
                bonus = base + (proficiency_bonus if is_proficient else 0)
                line = f"{stat}: {bonus:+}\n"
                tag = "bold" if is_proficient else "normal"
                save_text.insert(tk.END, line, tag)

            # Update skill checks
            for stat, skills in CHECKS.items():
                stat_match = target in stat.lower()
                stat_bonus = (self.stat_vars[stat].get() - 10) // 2
                matched_skills = []

                for check in skills:
                    if stat_match or target in check.lower():
                        is_proficient = check.lower() in proficient_skills
                        bonus = stat_bonus + (proficiency_bonus if is_proficient else 0)
                        line = f"  {check}: {bonus:+}\n"
                        tag = "bold" if is_proficient else "normal"
                        matched_skills.append((line, tag))

                if matched_skills:
                    # Print stat header (not bold)
                    skill_text.insert(tk.END, f"{stat}: {stat_bonus:+}\n", "normal")
                    for line, tag in matched_skills:
                        skill_text.insert(tk.END, line, tag)

            skill_text.config(state=tk.DISABLED)
            save_text.config(state=tk.DISABLED)


        # Search bar 
        ttk.Entry(win, textvariable=search_var, width=30).pack(padx=10, pady=5)
        search_var.trace_add("write", lambda *args: update_check_list())

        # Two-column layout
        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Skill list (left)
        skill_text = tk.Text(frame, wrap="word", width=50)
        skill_text.tag_configure("bold", font=bold_font)
        skill_text.tag_configure("normal", font=text_font)
        skill_text.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Saving throw list (right)
        save_text = tk.Text(frame, wrap="word", width=25)
        save_text.tag_configure("bold", font=bold_font)
        save_text.tag_configure("normal", font=text_font)
        save_text.grid(row=0, column=1, sticky="nsew")

        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)

        update_check_list()

    
    
    def extract_damage(self, text):
        # Define patterns to match damage formulas, prioritize xdy + z first
        patterns = [
            # Match "1d4 + 1" or similar: xdy + z
            r"(\d+)d(\d+)\s*\+\s*(\d+)",  # Matches xdy + z
            # Match "1d4" or similar: xdy
            r"(\d+)d(\d+)",  # Matches xdy
        ]
        
        # First, check for xdy + z (with a plus)
        match = re.search(patterns[0], text.strip(), re.IGNORECASE)
        if match:
            # Extract the parts of the match
            num_dice = int(match.group(1))
            dice_type = int(match.group(2))
            bonus = int(match.group(3))  # Capture the bonus if it exists
            
            # Calculate the damage range (min, max)
            min_damage = num_dice + bonus
            max_damage = num_dice * dice_type + bonus
            
            # Return the formatted damage string and the calculated potential damage range
            damage_str = f"{num_dice}d{dice_type} + {bonus}"
            damage_range = f"{min_damage} to {max_damage}"
            return damage_str, damage_range
        
        # If no match for xdy + z, check for xdy (without a plus)
        match = re.search(patterns[1], text.strip(), re.IGNORECASE)
        if match:
            # Extract the parts of the match
            num_dice = int(match.group(1))
            dice_type = int(match.group(2))
            
            # Calculate the damage range (min, max)
            min_damage = num_dice
            max_damage = num_dice * dice_type
            
            # Return the formatted damage string and the calculated potential damage range
            damage_str = f"{num_dice}d{dice_type}"
            damage_range = f"{min_damage} to {max_damage}"
            return damage_str, damage_range
        
        # If no valid damage pattern is found, return None
        return None, None


    def show_spell(self, spell_name, level):
        directory = os.path.dirname(__file__)
        class_files = [f for f in os.listdir(directory) if f.endswith('_Spells.csv')]
        spell_data = None

        # Fetch spell data from the CSV
        for filename in class_files:
            path = os.path.join(directory, filename)
            with open(path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row["Name"].strip().lower() == spell_name.strip().lower():
                        spell_data = row
                        break
            if spell_data:
                break

        if not spell_data:
            full_text = f"Error: Spell '{spell_name}' not found in any spell files."
        else:
            source = spell_data.get("Source", "Unknown Source")
            spell_level = spell_data.get("Level", "Unknown Level")
            casting_time = spell_data.get("Casting Time", "Unknown")
            duration = spell_data.get("Duration", "Unknown")
            school = spell_data.get("School", "Unknown")
            range_ = spell_data.get("Range", "Unknown")
            components = spell_data.get("Components", "Unknown")
            classes = spell_data.get("Classes", "Unknown")
            optional_classes = spell_data.get("Optional/Variant Classes", "None")
            description = spell_data.get("Text", "No description available.")
            higher_levels = spell_data.get("At Higher Levels", "No additional effects at higher levels.")

            # Extract damage info
            damage_str, damage_range = self.extract_damage(description)
            damage_text = f"\nDamage: {damage_str} ({damage_range})" if damage_str else ""

            header = f"{source}\nLevel: {spell_level}\nCasting Time: {casting_time}\nDuration: {duration}\n"
            header += f"School: {school}\nRange: {range_}\nComponents: {components}\n"
            header += f"Classes: {classes}\nOptional Classes: {optional_classes}\n"
            header += f"At Higher Levels: {higher_levels}\n"

            full_text = f"{header}{damage_text}\n\n{description}"

        win = tk.Toplevel(self.root)
        win.title(spell_name)
        text = tk.Text(win, wrap=tk.WORD, width=70, height=25)
        text.insert(tk.END, full_text)
        text.config(state=tk.DISABLED)
        text.pack(padx=10, pady=10)

        # Spell level options (Cantrip through 9th)
        spell_level_options = ["Cantrip", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]

        # Ensure the level provided is valid
        current_level_index = spell_level_options.index(spell_level)  # Get the index of the current spell level

        # Filter valid levels based on the spell's current level
        valid_levels = spell_level_options[current_level_index:]  # Valid levels should be the current level and higher levels

        level_var = tk.StringVar(value=spell_level)  # Default to current spell level (or modify if needed)

        level_label = tk.Label(win, text="Select Spell Level:")
        level_label.pack(padx=10, pady=5)

        # Dropdown menu with valid levels
        level_menu = tk.OptionMenu(win, level_var, *valid_levels)
        level_menu.pack(padx=10, pady=5)

        # Function to handle spell casting
        def cast_spell():
            selected_level = level_var.get()  # Retrieve the selected level as a string (e.g., '1st')
            spell_point_cost = spell_point_costs[selected_level]  # Get the cost from spell_point_costs using the selected level
            current_points = self.spell_points.get()  # Get the current spell points
            
            if current_points >= spell_point_cost:  # Check if enough points are available
                self.spell_points.set(current_points - spell_point_cost)  # Subtract the points
                print(f"Spell cast at level {selected_level}. Remaining spell points: {self.spell_points.get()}")
            else:
                print(f"Not enough spell points to cast {spell_name} at level {selected_level}!")

        # Always show the "Use Spell" button
        ttk.Button(win, text="Use Spell", command=cast_spell).pack(pady=5)



    def open_metamagic_window(self):
        # Create a new window for metamagic options
        metamagic_window = tk.Toplevel(self.root)
        metamagic_window.title("Metamagic Options")

        # Create a frame to hold the list of metamagic options
        list_frame = ttk.Frame(metamagic_window)
        list_frame.pack(padx=10, pady=10)

        # Create a label for the description area
        desc_label = ttk.Label(metamagic_window, text="Select a metamagic to view its description.", wraplength=300, justify=tk.LEFT)
        desc_label.pack(padx=10, pady=10)

        # Define a function to show the description of each metamagic
        def show_description(name):
            short, full = ALL_METAMAGIC[name]
            desc_label.config(text=f"{name}\n\n{short}\n\n{full}")

        # Create buttons for each metamagic option
        for name in ALL_METAMAGIC:
            ttk.Button(list_frame, text=name, command=lambda n=name: show_description(n)).pack(fill=tk.X, pady=2)

        # Add a button to close the window
        ttk.Button(metamagic_window, text="Close", command=metamagic_window.destroy).pack(pady=10)

    def load_spells_from_csv(self):
        spells_by_level = defaultdict(list)
        try:
            with open(self.csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if len(row) >= 2 and row[0].isdigit():
                        level = int(row[0].strip())
                        spell = row[1].strip()
                        spells_by_level[level].append(spell)
        except FileNotFoundError:
            print("CSV file not found.")
        return spells_by_level

    def create_widgets(self):
        # Configure the grid layout for the root window
        self.root.grid_columnconfigure(0, weight=1)  # Left side for Stats, HP, and Spells
        self.root.grid_columnconfigure(1, weight=1)  # Middle column for Traits and Feats (equal space)
        self.root.grid_columnconfigure(2, weight=2)  # Right side for Inventory (more space)
        self.root.grid_rowconfigure(0, weight=1)  # Row for Stats, HP, and Spells at the top
        self.root.grid_rowconfigure(1, weight=2)  # Row for HP, Spell Points, etc.
        
        # Top Stats Frame (Left side - column 0)
        stats_frame = ttk.LabelFrame(self.root, text="Stats")
        stats_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        for i, stat in enumerate(STATS):
            ttk.Label(stats_frame, text=stat).grid(row=0, column=i)
            entry = ttk.Entry(stats_frame, textvariable=self.stat_vars[stat], width=5)
            entry.grid(row=1, column=i)
            mod_label = ttk.Label(stats_frame)
            mod_label.grid(row=2, column=i)
            self.update_modifier_label(self.stat_vars[stat], mod_label)
        # checks button in the i+1 column
        ttk.Button(stats_frame, text="Checks", command=self.open_checks_window).grid(row=1, column=len(STATS)+1, columnspan=1, sticky="ew")

        # HP and other fields (same as before)
        info_frame = ttk.Frame(self.root)
        info_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)  # Occupies column 0, row 1
        self.add_point_controls(info_frame, "EXP", self.exp, 1)
        self.add_point_controls(info_frame, "HP", self.hp, 2)
        self.add_point_controls(info_frame, "Temp HP", self.temp_hp, 3)
        self.add_point_controls(info_frame, "Spell Points", self.spell_points, 4)
        self.add_point_controls(info_frame, "Sorcery Points", self.sorcery_points, 5)
        self.add_point_controls(info_frame, "AC", self.ac, 6)
        self.add_point_controls(info_frame, "Speed", self.speed, 7)
        self.add_point_controls(info_frame, "Actions", self.actions, 8)
        ttk.Button(info_frame, text="Reset Sorcery Points", command=lambda: self.sorcery_points.set(self.max_values["Sorcery Points"].get()), width=24).grid(row=6, column=4, columnspan=2)
        ttk.Button(info_frame, text="Reset Spell Points", command=lambda: self.spell_points.set(self.max_values["Spell Points"].get()), width=24).grid(row=7, column=4, columnspan=2)
        ttk.Button(info_frame, text="Metamagic Options", command=self.open_metamagic_window).grid(row=8, column=4, columnspan=2)
        ttk.Label(info_frame, text="Level:").grid(row=0, column=2, sticky="e")
        ttk.Label(info_frame, textvariable=self.level).grid(row=0, column=3, sticky="w")


        # Spells Section (Left side - column 0)
        spells_frame = ttk.LabelFrame(self.root, text="Spells")
        spells_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        # Buttons for spell controls
        spells_button_frame = ttk.Frame(spells_frame)
        spells_button_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

        ttk.Button(spells_button_frame, text="Load Spells", command=lambda: self.update_spell_display(self.main_spell_notebook)).grid(row=0, column=0, padx=2)
        ttk.Button(spells_button_frame, text="Add/Delete Spell", command=self.add_delete_spell).grid(row=0, column=1, padx=2)
        ttk.Button(spells_button_frame, text="Show all Spells", command=self.show_all_spells).grid(row=0, column=2, padx=2)
        # Notebook for spells
        self.main_spell_notebook = ttk.Notebook(spells_frame)
        self.main_spell_notebook.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        # Make the notebook expand
        spells_frame.rowconfigure(1, weight=1)
        spells_frame.columnconfigure(0, weight=1)


        # Configure grid weights to allow the notebook to expand
        spells_frame.rowconfigure(2, weight=1)
        spells_frame.columnconfigure(0, weight=1)
        spells_frame.columnconfigure(1, weight=1)

        self.update_spell_display(self.main_spell_notebook)

        # Inventory Frame (Right side - column 1)
        extras_frame = ttk.LabelFrame(self.root, text="Extras")
        extras_frame.grid(row=0, column=2, rowspan=6, sticky="nsew", padx=10, pady=5)  # Occupies row 0, 1, 2
        extras_frame.grid_propagate(False)
        extras_frame.configure(width=200)  # Optional: set a fixed width
        # for i in range(4):
        #     extras_frame.rowconfigure(i, weight=1, minsize=0)  # minsize ensures uniform row height

        
        ttk.Button(extras_frame, text="Bestiary", command=self.open_bestiary).grid(row=0, column=0, padx=2, sticky="ew")
        ttk.Button(extras_frame, text="Items", command=self.open_items).grid(row=0, column=1, padx=2, sticky="ew")
        ttk.Button(extras_frame, text="Inventory", command=self.load_inventory_from_csv).grid(row=1, column=0, padx=2, columnspan=2, sticky="ew")
        ttk.Button(extras_frame, text="Classes", command=self.open_classes).grid(row=2, column=0, padx=2, sticky="ew", columnspan=2)
        ttk.Button(extras_frame, text="Character Infos", command=self.open_character_info).grid(row=3, column=0, padx=2, sticky="ew", columnspan=2)
        ttk.Button(extras_frame, text="Edit Character Info", command=self.edit_character_info).grid(row=4, column=0, columnspan=2, sticky="ew")

        extras_frame.rowconfigure(5, weight=1)  # Add a spacer row to push buttons to the bottom
        ttk.Button(extras_frame, text="Save CSV", command=self.save_to_csv).grid(row=6, column=0, padx=2, sticky="ew")
        ttk.Button(extras_frame, text="Load CSV", command=self.load_from_csv).grid(row=6, column=1, padx=2, sticky="ew")
    
    def edit_character_info(self):
        edit_win = tk.Toplevel(self.root)
        edit_win.title("Edit Character Info")
        edit_win.geometry("500x600")

        form_frame = ttk.Frame(edit_win)
        form_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Define the fields to edit
        fields = [
            "Race", "Class", "Background",
            "Armor Proficiencies", "Weapon Proficiencies", "Tool Proficiencies",
            "Saving Throws", "Skills",
            "Spellcasting Ability", "Spell Save DC", "Spell Attack Bonus",
            "Features", "Languages"
        ]

        self.char_info_vars = {}

        # Create entry widgets
        for i, field in enumerate(fields):
            ttk.Label(form_frame, text=field + ":").grid(row=i, column=0, sticky="e", pady=2)
            var = tk.StringVar(value=self.character_info_data.get(field, ""))
            entry = ttk.Entry(form_frame, textvariable=var, width=50)
            entry.grid(row=i, column=1, sticky="w", pady=2)
            self.char_info_vars[field] = var

        # Save Button
        def save_edited_info():
            # Update internal data
            self.character_info_data.clear()
            for field, var in self.char_info_vars.items():
                self.character_info_data[field] = var.get()

            # Now save to CSV
            self.save_to_csv()
            edit_win.destroy()
            messagebox.showinfo("Saved", "Character info saved successfully.")

        ttk.Button(edit_win, text="Save", command=save_edited_info).pack(pady=10)

    def open_character_info(self):
        # Toggle the frame if it's already open
        if hasattr(self, 'charinfo_frame') and self.charinfo_frame.winfo_exists():
            self.charinfo_frame.destroy()
            return

        self.charinfo_frame = tk.Frame(self.root, width=500)
        self.charinfo_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10, rowspan=3)
        self.charinfo_frame.grid_propagate(False)

        # Sidebar for quick navigation or category list (optional, can be expanded)
        listbox = tk.Listbox(self.charinfo_frame, width=25)
        listbox.grid(row=0, column=0, sticky="ns", padx=(0, 10), pady=5)

        # Main content display frame
        text_frame = tk.Frame(self.charinfo_frame)
        text_frame.grid(row=0, column=1, sticky="nsew", pady=5)
        # Allow text_frame to expand
        self.charinfo_frame.columnconfigure(1, weight=1)
        self.charinfo_frame.rowconfigure(0, weight=1)


        # Organize keys into categories
        raw_info = self.character_info_data
        sections = {
            "Race & Class": {
                "Race": raw_info.get("Race", ""),
                "Class": raw_info.get("Class", ""),
                "Background": raw_info.get("Background", "")
            },
            "Proficiencies": {
                "Armor": raw_info.get("Armor Proficiencies", ""),
                "Weapons": raw_info.get("Weapon Proficiencies", ""),
                "Tools": raw_info.get("Tool Proficiencies", ""),
                "Saving Throws": raw_info.get("Saving Throws", ""),
                "Skills": raw_info.get("Skills", ""),
                "Languages": raw_info.get("Languages", "")
            },
            "Spellcasting": {
                "Spellcasting Ability": raw_info.get("Spellcasting Ability", ""),
                "Spell Save DC": raw_info.get("Spell Save DC", ""),
                "Spell Attack Bonus": raw_info.get("Spell Attack Bonus", "")
            },
            "Features & Traits": {
                "Features": raw_info.get("Features", ""),
                "Languages": raw_info.get("Languages", "")
            }
        }

        # Populate listbox and define selection callback
        section_names = list(sections.keys())
        for name in section_names:
            listbox.insert(tk.END, name)

        def show_section(event):
            selection = listbox.curselection()
            if not selection:
                return
            section = section_names[selection[0]]
            content = sections[section]

            # Clear existing content
            for widget in text_frame.winfo_children():
                widget.destroy()

            if section == "Race & Class":
                # Create a frame for displaying labels and buttons (like Class and Race)
                label_button_frame = tk.Frame(text_frame)
                label_button_frame.pack(side="top", fill="both", expand=True)

                    # Display Race (if present)
                if "Race" in content and content["Race"]:
                    race_label = tk.Label(label_button_frame, text="Race:", font=("Consolas", 12, 'bold'))
                    race_label.pack(side="top", anchor="w", pady=(5, 0))
                    race_button = tk.Button(label_button_frame, text=content["Race"], command=lambda race=content["Race"]: self.open_single_race_window(race))
                    race_button.pack(side="top", pady=5, anchor="w")

                # Display Class (if present)
                if "Class" in content and content["Class"]:
                    class_label = tk.Label(label_button_frame, text="Class:", font=("Consolas", 12, 'bold'))
                    class_label.pack(side="top", anchor="w", pady=(5, 0))
                    class_button = tk.Button(label_button_frame, text=content["Class"], command=lambda cls=content["Class"]: self.open_single_class_window(cls))
                    class_button.pack(side="top", pady=5, anchor="w")

                # Display Background (if present)
                if "Background" in content and content["Background"]:
                    background_label = tk.Label(label_button_frame, text="Background:", font=("Consolas", 12, 'bold'))
                    background_label.pack(side="top", anchor="w", pady=(5, 0))
                    background_button = tk.Button(label_button_frame, text=content["Background"], command=lambda bg=content["Background"]: self.open_single_background_window(bg))
                    background_button.pack(side="top", pady=5, anchor="w")
            elif section == "Spellcasting":
                for widget in text_frame.winfo_children():
                    widget.destroy()

                spellcasting_frame = tk.Frame(text_frame)
                spellcasting_frame.pack(fill="both", expand=True, padx=10, pady=10)

                ability = content.get("Spellcasting Ability", "")
                prof_bonus = 2

                ability_score = self.stat_vars.get(ability, tk.StringVar(value="10")).get()
                try:
                    ability_score = int(ability_score)
                except ValueError:
                    ability_score = 10  # Default if invalid

                ability_mod = (ability_score - 10) // 2

                spell_save_dc = 8 + prof_bonus + ability_mod
                spell_attack_bonus = prof_bonus + ability_mod

                # Display calculated values
                labels = [
                    ("Spellcasting Ability", ability),
                    ("Spell Save DC", str(spell_save_dc)),
                    ("Spell Attack Bonus", f"+{spell_attack_bonus}")
                ]

                for label, value in labels:
                    lbl = tk.Label(spellcasting_frame, text=f"{label}:", font=("Consolas", 12, 'bold'), anchor="w")
                    lbl.pack(anchor="w", pady=(5, 0))
                    val_lbl = tk.Label(spellcasting_frame, text=value, font=("Consolas", 11), anchor="w")
                    val_lbl.pack(anchor="w", pady=(0, 5))

            
            elif section == "Features & Traits":
                # Create a container frame with fixed height (you can tweak this)
                container = tk.Frame(text_frame)
                container.pack(fill="both", expand=True)

                # Create a canvas and vertical scrollbar
                canvas = tk.Canvas(container, borderwidth=0)
                scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
                canvas.configure(yscrollcommand=scrollbar.set)

                scrollbar.pack(side="left", fill="y")
                canvas.pack(side="left", fill="both", expand=True)

                # Create scrollable inner frame
                scrollable_frame = tk.Frame(canvas)
                scroll_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

                def resize_scrollable(event):
                    canvas.itemconfig(scroll_window, width=event.width)
                canvas.bind("<Configure>", resize_scrollable)

                # Update scrollregion when contents change
                def on_frame_configure(event):
                    canvas.configure(scrollregion=canvas.bbox("all"))
                scrollable_frame.bind("<Configure>", on_frame_configure)

                # === Load and display race traits ===
                race_name = self.character_info_data.get("Race", "")

                path = os.path.join(os.path.dirname(__file__), 'data.json')
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                selected_race = None
                for race in data.get("race", []):
                    if race_name.lower() in race.get("name", "").lower():
                        selected_race = race
                        break

                if selected_race and "trait" in selected_race:
                    title_label = tk.Label(scrollable_frame, text=f"Traits of {selected_race['name']}:", font=("Consolas", 12, "bold"))
                    title_label.pack(anchor="w", pady=(10, 5), padx=10)

                    for trait in selected_race["trait"]:
                        name = trait.get("name", "Unnamed Trait")
                        text = trait.get("text", "")

                        name_label = tk.Label(scrollable_frame, text=name, font=("Consolas", 11, "bold"), wraplength=300, justify="left")
                        name_label.pack(anchor="w", padx=10, pady=(10, 0))

                        text_label = tk.Label(scrollable_frame, text=text, font=("Consolas", 10), wraplength=300, justify="left")
                        text_label.pack(anchor="w", padx=(20, 10), pady=(0, 5))

                else:
                    no_traits_label = tk.Label(scrollable_frame, text="No traits found for this race.", font=("Consolas", 11))
                    no_traits_label.pack(anchor="w", padx=10, pady=10)
                
                # === Load and display background traits ===
                background_name = self.character_info_data.get("Background", "")

                if background_name:
                    for bg in data.get("background", []):
                        if background_name.lower() in bg.get("name", "").lower():
                            if "trait" in bg:
                                # Add horizontal separator line
                                separator = ttk.Separator(scrollable_frame, orient='horizontal')
                                separator.pack(fill='x', padx=10, pady=15)

                                bg_title = tk.Label(scrollable_frame, text=f"Traits from {bg['name']}:", font=("Consolas", 12, "bold"))
                                bg_title.pack(anchor="w", pady=(10, 5), padx=10)

                                for trait in bg["trait"]:
                                    name = trait.get("name", "Unnamed Trait")
                                    text = trait.get("text", "")

                                    name_label = tk.Label(scrollable_frame, text=name, font=("Consolas", 11, "bold"), wraplength=300, justify="left")
                                    name_label.pack(anchor="w", padx=10, pady=(10, 0))

                                    text_label = tk.Label(scrollable_frame, text=text, font=("Consolas", 10), wraplength=300, justify="left")
                                    text_label.pack(anchor="w", padx=(20, 10), pady=(0, 5))
                # === Load and display class features up to current level ===
                exclude_words = ["Sorcerous", "Dragon", "Storm:", "Draconic", "Wild Magic","Shadow","Favored Soul","Phoenix Sorcery","Sea Sorcery","Stone Sorcery"]  # Add any other words you want to exclude
                class_name = self.character_info_data.get("Class", "")
                level = self.level.get()

                if isinstance(level, str):
                    try:
                        level = int(level)
                    except ValueError:
                        level = 1  # default if invalid

                if class_name:
                    for cls in data.get("class", []):
                        if class_name.lower() in cls.get("name", "").lower():
                            # Add horizontal separator line before class features
                            separator = ttk.Separator(scrollable_frame, orient='horizontal')
                            separator.pack(fill='x', padx=10, pady=15)

                            cls_title = tk.Label(scrollable_frame, text=f"Class Features (up to level {level})\n - {cls['name']}:", font=("Consolas", 12, "bold"))
                            cls_title.pack(anchor="w", pady=(10, 5), padx=10)

                            features_by_level = {}

                            for entry in cls.get("autolevel", []):
                                try:
                                    entry_level = int(entry.get("level", 0))
                                except ValueError:
                                    continue

                                if entry_level <= level:
                                    for feature in entry.get("feature", []):
                                        feature_name = feature.get("name", "Unnamed Feature")
                                        feature_texts = feature.get("text", [])
                                        
                                        # Check if the feature name contains any excluded words
                                        if any(exclude_word.lower() in feature_name.lower() for exclude_word in exclude_words):
                                            continue  # Skip this feature if it matches any exclusion word

                                        # Group features by level
                                        if entry_level not in features_by_level:
                                            features_by_level[entry_level] = []

                                        features_by_level[entry_level].append({
                                            "name": feature_name,
                                            "text": feature_texts
                                        })

                            # Now display features, grouped by level
                            for lvl in sorted(features_by_level.keys()):
                                level_label = tk.Label(scrollable_frame, text=f"Level {lvl} Features:", font=("Consolas", 12, "bold"))
                                level_label.pack(anchor="w", pady=(10, 5), padx=10)

                                for feature in features_by_level[lvl]:
                                    name_label = tk.Label(scrollable_frame, text=feature["name"], font=("Consolas", 11, "bold"), wraplength=300, justify="left")
                                    name_label.pack(anchor="w", padx=10, pady=(10, 0))

                                    # If text is a list, join with newlines
                                    if isinstance(feature["text"], list):
                                        feature_text = "\n".join(feature["text"])
                                    else:
                                        feature_text = str(feature["text"])

                                    text_label = tk.Label(scrollable_frame, text=feature_text, font=("Consolas", 10), wraplength=300, justify="left")
                                    text_label.pack(anchor="w", padx=(20, 10), pady=(0, 5))

            else:
                # For other sections, print them in the same old way
                text_widget = tk.Text(text_frame, wrap='word', font=("Consolas", 11))
                text_widget.tag_configure('bold', font=('Consolas', 11, 'bold'))
                text_widget.pack(side='top', fill='both', expand=True)
                scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
                scrollbar.pack(side='right', fill='y')
                text_widget.configure(yscrollcommand=scrollbar.set, state='disabled')

                text_widget.configure(state='normal')
                text_widget.delete("1.0", tk.END)
                text_widget.insert(tk.END, f"{section}\n", 'bold')
                text_widget.insert(tk.END, "-" * len(section) + "\n\n")

                for key, value in content.items():
                    text_widget.insert(tk.END, f"{key}: ", 'bold')
                    text_widget.insert(tk.END, f"{value}\n\n")
                text_widget.configure(state='disabled')

        listbox.bind("<<ListboxSelect>>", show_section)

        # Default to first section
        listbox.selection_set(0)
        listbox.event_generate("<<ListboxSelect>>")
    
    def open_single_background_window(self, background_name):
        # Load JSON data
        path = os.path.join(os.path.dirname(__file__), 'data.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        background_data = data.get("background", [])  # Assuming backgrounds are stored under the "background" key
        background_name_lower = background_name.lower()

        # Try to find the background in the list
        selected_background = None
        for background in background_data:
            if background_name_lower in background.get("name", "").lower():
                selected_background = background
                break

        if not selected_background:
            messagebox.showinfo("Background Not Found", f"No background info found for '{background_name}'")
            return

        # Create a new window
        win = tk.Toplevel(self.root)
        win.title(selected_background["name"])
        win.geometry("600x600")

        text_widget = tk.Text(win, wrap='word', font=("Consolas", 11))
        text_widget.tag_configure('bold', font=('Consolas', 11, 'bold'))
        text_widget.pack(fill='both', expand=True)
        scrollbar = ttk.Scrollbar(win, command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget.configure(yscrollcommand=scrollbar.set, state='normal')

        def print_json_to_text(widget, obj, indent=0, in_text_block=False):
            spacing = '    ' * indent
            bullet = "•"

            if isinstance(obj, dict):
                keys = list(obj.keys())
                i = 0
                while i < len(keys):
                    key = keys[i]
                    value = obj[key]

                    # Special case: "Name" followed by "Text"
                    if key.lower() == "name" and i + 1 < len(keys) and keys[i + 1].lower() == "text":
                        name_value = value
                        text_value = obj[keys[i + 1]]
                        widget.insert('end', f"\n{name_value}\n", 'bold')
                        if isinstance(text_value, str):
                            widget.insert('end', f"{text_value.strip()}\n\n")
                        else:
                            print_json_to_text(widget, text_value, indent + 1, in_text_block=True)
                        i += 2
                        continue

                    if key.lower() in ["name", "text"]:
                        i += 1
                        continue

                    display_key = key.replace('_', ' ').capitalize()
                    widget.insert('end', f"{display_key}:\n", 'bold')
                    print_json_to_text(widget, value, indent + 1, in_text_block)
                    i += 1

                if indent == 1:
                    widget.insert('end', '\n')

            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        print_json_to_text(widget, item, indent, in_text_block)
                    else:
                        widget.insert('end', f"{item}\n")
                widget.insert('end', '\n')

            else:
                widget.insert('end', f"{obj}\n")

        # Call the function to print the selected background data to the text widget
        print_json_to_text(text_widget, selected_background)
        text_widget.config(state='disabled')

    def open_single_class_window(self, class_name):
        # Load JSON data
        path = os.path.join(os.path.dirname(__file__), 'data.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        class_data = data.get("class", [])
        class_name_lower = class_name.lower()

        # Try to find the class in the list
        selected_class = None
        for cls in class_data:
            if class_name_lower in cls.get("name", "").lower():
                selected_class = cls
                break

        if not selected_class:
            messagebox.showinfo("Class Not Found", f"No class info found for '{class_name}'")
            return

        # Create window
        win = tk.Toplevel(self.root)
        win.title(selected_class["name"])
        win.geometry("600x600")

        text_widget = tk.Text(win, wrap='word', font=("Consolas", 11))
        text_widget.tag_configure('bold', font=('Consolas', 11, 'bold'))
        text_widget.pack(fill='both', expand=True)
        scrollbar = ttk.Scrollbar(win, command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget.configure(yscrollcommand=scrollbar.set, state='normal')

        def print_json_to_text(widget, obj, indent=0, in_text_block=False):
            spacing = '    ' * indent
            bullet = "•"

            if isinstance(obj, dict):
                keys = list(obj.keys())
                i = 0
                while i < len(keys):
                    key = keys[i]
                    value = obj[key]

                    # Special case: "Name" followed by "Text"
                    if key.lower() == "name" and i + 1 < len(keys) and keys[i + 1].lower() == "text":
                        name_value = value
                        text_value = obj[keys[i + 1]]
                        widget.insert('end', f"\n{name_value}\n", 'bold')
                        if isinstance(text_value, str):
                            widget.insert('end', f"{text_value.strip()}\n\n")
                        else:
                            print_json_to_text(widget, text_value, indent + 1, in_text_block=True)
                        i += 2
                        continue

                    if key.lower() in ["name", "text"]:
                        i += 1
                        continue

                    display_key = key.replace('_', ' ').capitalize()
                    widget.insert('end', f"{display_key}:\n", 'bold')
                    print_json_to_text(widget, value, indent + 1, in_text_block)
                    i += 1

                if indent == 1:
                    widget.insert('end', '\n')

            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        print_json_to_text(widget, item, indent, in_text_block)
                    else:
                        widget.insert('end', f"{item}\n")
                widget.insert('end', '\n')

            else:
                widget.insert('end', f"{obj}\n")

        print_json_to_text(text_widget, selected_class)
        text_widget.config(state='disabled')

    def open_single_race_window(self, race_name):
        # Load JSON data
        path = os.path.join(os.path.dirname(__file__), 'data.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        race_data = data.get("race", [])  # Assuming races are stored under the "race" key
        race_name_lower = race_name.lower()

        # Try to find the race in the list
        selected_race = None
        for race in race_data:
            if race_name_lower in race.get("name", "").lower():
                selected_race = race
                break

        if not selected_race:
            messagebox.showinfo("Race Not Found", f"No race info found for '{race_name}'")
            return

        # Create a new window
        win = tk.Toplevel(self.root)
        win.title(selected_race["name"])
        win.geometry("600x600")

        text_widget = tk.Text(win, wrap='word', font=("Consolas", 11))
        text_widget.tag_configure('bold', font=('Consolas', 11, 'bold'))
        text_widget.pack(fill='both', expand=True)
        scrollbar = ttk.Scrollbar(win, command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget.configure(yscrollcommand=scrollbar.set, state='normal')

        def print_json_to_text(widget, obj, indent=0, in_text_block=False):
            spacing = '    ' * indent
            bullet = "•"

            if isinstance(obj, dict):
                keys = list(obj.keys())
                i = 0
                while i < len(keys):
                    key = keys[i]
                    value = obj[key]

                    # Special case: "Name" followed by "Text"
                    if key.lower() == "name" and i + 1 < len(keys) and keys[i + 1].lower() == "text":
                        name_value = value
                        text_value = obj[keys[i + 1]]
                        widget.insert('end', f"\n{name_value}\n", 'bold')
                        if isinstance(text_value, str):
                            widget.insert('end', f"{text_value.strip()}\n\n")
                        else:
                            print_json_to_text(widget, text_value, indent + 1, in_text_block=True)
                        i += 2
                        continue

                    if key.lower() in ["name", "text"]:
                        i += 1
                        continue

                    display_key = key.replace('_', ' ').capitalize()
                    widget.insert('end', f"{display_key}:\n", 'bold')
                    print_json_to_text(widget, value, indent + 1, in_text_block)
                    i += 1

                if indent == 1:
                    widget.insert('end', '\n')

            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        print_json_to_text(widget, item, indent, in_text_block)
                    else:
                        widget.insert('end', f"{item}\n")
                widget.insert('end', '\n')

            else:
                widget.insert('end', f"{obj}\n")

        # Call the function to print the selected race data to the text widget
        print_json_to_text(text_widget, selected_race)
        text_widget.config(state='disabled')

    
    def update_inventory_display(self, notebook):
        """Update the inventory display table."""
        for widget in notebook.winfo_children():
            widget.destroy()

        inventory_frame = tk.Frame(notebook)
        inventory_frame.pack(fill='both', expand=True)

        # Table headers
        headers = ["Item", "Quantity", "Equipped"]
        for col_num, header in enumerate(headers):
            header_label = tk.Label(inventory_frame, text=header, font=("Arial", 10, "bold"))
            header_label.grid(row=0, column=col_num, sticky="w", padx=10, pady=5)

        for idx, (item, data) in enumerate(self.inventory_items.items()):
            item_label = tk.Label(inventory_frame, text=item, fg="blue", cursor="hand2")
            item_label.grid(row=idx+1, column=0, padx=10, pady=5, sticky="w")
            item_label.bind("<Button-1>", lambda e, item_name=item: self.show_inventory_item_info(item_name))

            qty_label = tk.Label(inventory_frame, text=str(data["quantity"]))
            qty_label.grid(row=idx+1, column=1, padx=10, pady=5)

            # Determine if it's an armor item
            is_armor = "armor" in item.lower()

            if is_armor:
                equip_var = tk.BooleanVar(value=data["equipped"])

                def toggle_equipped(item_name=item, var=equip_var):
                    self.inventory_items[item_name]["equipped"] = var.get()
                    armor_AC = self.extract_armor_ac(item_name)["base_ac"]
                    print(f"Armor AC for {item_name}: {armor_AC}")
                    AC = armor_AC
                    if self.extract_armor_ac(item_name)["adds_dex"]:
                        AC += (self.stat_vars["Dexterity"].get() - 10) // 2
                    self.ac.set(AC if var.get() else self.max_values["AC"].get())

                equip_check = ttk.Checkbutton(inventory_frame, variable=equip_var, command=toggle_equipped)
                equip_check.grid(row=idx+1, column=2, padx=10, pady=5)
            else:
                equipped_label = tk.Label(inventory_frame, text="Yes" if data["equipped"] else "No")
                equipped_label.grid(row=idx+1, column=2, padx=10, pady=5)

        notebook.add(inventory_frame, text="Inventory")

    def extract_armor_ac(self, item_name: str):
        path = os.path.join(os.path.dirname(__file__), "Items.csv")
        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row["Name"] == item_name:
                    if "armor" in row["Type"].lower():
                        AC = row["Damage"]
                        base_ac = int(re.search(r'\d+', AC).group())
                        adds_dex = bool(re.search(r'\+\s*Dex', AC, re.IGNORECASE))
                        return {'base_ac': base_ac, 'adds_dex': adds_dex}
        return {'base_ac': None, 'adds_dex': False}



    def show_inventory_item_info(self, item_name):
        path = os.path.join(os.path.dirname(__file__), "Items.csv")

        if not os.path.exists(path):
            messagebox.showerror("Error", "Items.csv not found.")
            return

        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row["Name"] == item_name:
                    self.show_full_item_info(row)
                    return

        messagebox.showinfo("Item Info", f"No detailed info found for: {item_name}")

    
    def load_inventory_from_csv(self):
        # Toggle visibility: close if already open
        if hasattr(self, 'inventory_frame') and self.inventory_frame.winfo_exists():
            self.inventory_frame.destroy()
            return

        # Create and show the inventory panel
        self.inventory_frame = tk.Frame(self.root)
        self.inventory_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10, rowspan=3)

        ttk.Button(self.inventory_frame, text="Add Item", command=self.open_add_item_window).grid(row=0, column=0)
        ttk.Button(self.inventory_frame, text="Delete Item", command=self.delete_item).grid(row=0, column=1)
        ttk.Button(self.inventory_frame, text="Save Inventory", command=self.save_to_csv).grid(row=0, column=2)

        self.inventory_notebook = ttk.Notebook(self.inventory_frame)
        self.inventory_notebook.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

        self.inventory_frame.rowconfigure(1, weight=1)
        self.inventory_frame.columnconfigure(0, weight=1)
        self.inventory_frame.columnconfigure(1, weight=1)

        self.update_inventory_display(self.inventory_notebook)

        # Ensure main window expands correctly
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)


        
        self.inventory_items.clear()
        try:
            with open(self.csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if len(row) >= 3 and row[0] == "Inventory":
                        item = row[1].strip()
                        try:
                            qty = int(row[2].strip())
                        except ValueError:
                            qty = 1

                        # Handle equipped flag if present
                        equipped = False
                        if len(row) >= 4:
                            equipped_str = row[3].strip().lower()
                            equipped = equipped_str in ("true", "1", "yes")

                        self.inventory_items[item] = {
                            "quantity": qty,
                            "equipped": equipped
                        }

        except FileNotFoundError:
            print("Character CSV file not found.")

        self.update_inventory_display(self.inventory_notebook)



    def open_add_item_window(self):
        path = os.path.join(os.path.dirname(__file__), "Items.csv")
        if not os.path.exists(path):
            messagebox.showerror("Error", "Items.csv not found.")
            return

        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = list(csv.DictReader(csvfile))
            item_rows = reader
            item_names = [row["Name"] for row in item_rows]
            item_data_by_name = {row["Name"]: row for row in item_rows}

        win = tk.Toplevel(self.root)
        win.title("Add Item to Inventory")

        # Item Name Entry
        tk.Label(win, text="Item Name (select or type custom):").pack(anchor="w", padx=10, pady=(10, 0))
        item_name_var = tk.StringVar()
        item_entry = tk.Entry(win, textvariable=item_name_var)
        item_entry.pack(fill="x", padx=10)

        # Suggestion Listbox
        suggestion_listbox = tk.Listbox(win, height=5)
        suggestion_listbox.pack(fill="both", expand=False, padx=10, pady=5)

        # Equip checkbox (initially disabled)
        equipped_var = tk.BooleanVar(value=False)
        equip_checkbox = tk.Checkbutton(win, text="Equip this item (if valid)", variable=equipped_var)
        equip_checkbox.pack(anchor="w", padx=10, pady=(5, 0))
        equip_checkbox.config(state=tk.DISABLED)

        # Description (only used for custom items)
        description_label = tk.Label(win, text="Custom Item Description (optional):")
        description_entry = tk.Entry(win)

        def update_suggestions(*_):
            search = item_name_var.get().lower()
            suggestion_listbox.delete(0, tk.END)
            for name in item_names:
                if search in name.lower():
                    suggestion_listbox.insert(tk.END, name)
            check_custom_item()

        def check_custom_item():
            item = item_name_var.get().strip()
            is_known = item in item_data_by_name
            if is_known:
                item_type = item_data_by_name[item].get("Type", "").lower()
                if "armor" in item_type or "weapon" in item_type:
                    equip_checkbox.config(state=tk.NORMAL)
                else:
                    equip_checkbox.config(state=tk.DISABLED)
                    equipped_var.set(False)
                description_label.pack_forget()
                description_entry.pack_forget()
            else:
                equip_checkbox.config(state=tk.DISABLED)
                equipped_var.set(False)
                description_label.pack(anchor="w", padx=10, pady=(5, 0))
                description_entry.pack(fill="x", padx=10)

        def on_suggestion_select(_):
            selection = suggestion_listbox.curselection()
            if selection:
                selected = suggestion_listbox.get(selection[0])
                item_name_var.set(selected)
                check_custom_item()

        suggestion_listbox.bind("<<ListboxSelect>>", on_suggestion_select)
        item_name_var.trace_add("write", update_suggestions)
        update_suggestions()

        # Quantity Input
        tk.Label(win, text="Quantity:").pack(anchor="w", padx=10, pady=(10, 0))
        qty_entry = tk.Entry(win)
        qty_entry.pack(fill="x", padx=10)

        # Add Button
        def add_item_to_inventory():
            item = item_name_var.get().strip()
            try:
                qty = int(qty_entry.get())
                if not item or qty < 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid input", "Enter a valid item name and a positive quantity.")
                return

            equip = equipped_var.get()
            is_known = item in item_data_by_name
            description = description_entry.get().strip() if not is_known else item_data_by_name[item].get("Description", "")

            # Store item
            if item in self.inventory_items:
                self.inventory_items[item]["quantity"] += qty
                if is_known and ("armor" in item_data_by_name[item]["Type"].lower() or "weapon" in item_data_by_name[item]["Type"].lower()):
                    self.inventory_items[item]["equipped"] = self.inventory_items[item]["equipped"] or equip
            else:
                self.inventory_items[item] = {
                    "quantity": qty,
                    "equipped": equip if is_known else False,
                    "description": description
                }

            self.update_inventory_display(self.inventory_notebook)
            win.destroy()

        add_btn = tk.Button(win, text="Add Item", command=add_item_to_inventory)
        add_btn.pack(pady=10)





    def delete_item(self):
        def perform_delete():
            # Get the selected item text from the listbox
            selected_item_text = listbox.get(tk.ACTIVE).strip()

            # Extract item name from the listbox text (remove "(Qty: X)" part)
            item_name = selected_item_text.split(" (Qty:")[0].strip()

            try:
                qty = int(qty_var.get())
                if item_name in self.inventory_items:
                    item_data = self.inventory_items[item_name]

                    # Check if item is equipped and handle accordingly
                    if item_data.get("equipped", False):
                        if messagebox.askyesno("Confirm", f"Item {item_name} is equipped. Do you want to unequip it before deleting?"):
                            self.inventory_items[item_name]["equipped"] = False

                    # Decrease quantity or delete item entirely
                    if item_data["quantity"] > qty:
                        self.inventory_items[item_name]["quantity"] -= qty
                    else:
                        del self.inventory_items[item_name]  # Delete the item entirely

                    self.update_inventory_display(self.inventory_notebook)
                    delete_window.destroy()
                else:
                    messagebox.showerror("Error", "Item not found.")
            except ValueError:
                messagebox.showerror("Invalid Input", "Quantity must be an integer.")

        # Create the delete item window
        delete_window = tk.Toplevel(self.root)
        delete_window.title("Delete Inventory Item")

        # Create Listbox to display inventory items
        tk.Label(delete_window, text="Select Item to Delete:").grid(row=0, column=0, columnspan=2, padx=10, pady=5)

        listbox = tk.Listbox(delete_window, height=10, width=50)
        listbox.grid(row=1, column=0, columnspan=2, padx=10, pady=5)

        # Populate the listbox with inventory items and quantities
        for item, data in self.inventory_items.items():
            listbox.insert(tk.END, f"{item} (Qty: {data['quantity']})")

        # Label and input for quantity to delete
        tk.Label(delete_window, text="Quantity:").grid(row=2, column=0)
        qty_var = tk.StringVar(value="1")
        tk.Entry(delete_window, textvariable=qty_var).grid(row=2, column=1)

        # Delete button
        tk.Button(delete_window, text="Delete", command=perform_delete).grid(row=3, column=0, columnspan=2, pady=10)

        # Ensure window is responsive
        delete_window.resizable(False, False)


    def open_classes(self):
        # Toggle the frame if it's already open
        if hasattr(self, 'class_frame') and self.class_frame.winfo_exists():
            self.class_frame.destroy()
            return

        # Load the JSON file
        path = os.path.join(os.path.dirname(__file__), 'data.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        class_data = data.get("class", [])

        # Create the class frame
        self.class_frame = tk.Frame(self.root, width=500)
        self.class_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10, rowspan=3)
        self.class_frame.grid_propagate(False)  # Prevent auto-resizing

        # Left: Class List
        listbox = tk.Listbox(self.class_frame, width=25)
        listbox.grid(row=0, column=0, sticky="ns", padx=(0, 10), pady=5)

        # Right: Text Display Area
        text_frame = tk.Frame(self.class_frame)
        text_frame.grid(row=0, column=1, sticky="nsew", pady=5)

        text_widget = tk.Text(text_frame, wrap='word', font=("Consolas", 11))
        text_widget.tag_configure('bold', font=('Consolas', 11, 'bold'))
        text_widget.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget.configure(yscrollcommand=scrollbar.set, state='disabled')

        # Function to print class info
        def print_class_info(index):
            text_widget.configure(state='normal')
            text_widget.delete('1.0', 'end')
            cls = class_data[index]
            print_json_to_text(text_widget, cls)
            text_widget.configure(state='disabled')

        # Function to pretty-print the JSON
        def print_json_to_text(widget, obj, indent=0, in_text_block=False):
            spacing = '    ' * indent
            bullet = "•"

            if isinstance(obj, dict):
                keys = list(obj.keys())
                i = 0
                while i < len(keys):
                    key = keys[i]
                    value = obj[key]

                    # Special handling for "Name" followed by "Text"
                    if key.lower() == "name" and i + 1 < len(keys) and keys[i + 1].lower() == "text":
                        name_value = value
                        text_value = obj[keys[i + 1]]

                        widget.insert('end', f"\n{name_value}\n", 'bold')  # Bold class section title
                        if isinstance(text_value, str):
                            widget.insert('end', f"{text_value.strip()}\n\n")
                        else:
                            print_json_to_text(widget, text_value, indent + 1, in_text_block=True)

                        i += 2  # Skip "Text" since we've already handled it
                        continue

                    # Skip standalone "Name" or "Text"
                    if key.lower() in ["name", "text"]:
                        i += 1
                        continue

                    display_key = key.replace('_', ' ').capitalize()
                    widget.insert('end', f"{display_key}:\n", 'bold')
                    print_json_to_text(widget, value, indent + 1, in_text_block=in_text_block)
                    i += 1

                if indent == 1:
                    widget.insert('end', '\n')

            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        print_json_to_text(widget, item, indent, in_text_block)
                    else:
                        widget.insert('end', f"{item}\n")
                widget.insert('end', '\n')

            else:
                widget.insert('end', f"{obj}\n")



        # Populate the listbox
        for idx, cls in enumerate(class_data):
            name = cls.get("name", f"Class {idx+1}")
            listbox.insert('end', name)

        listbox.bind('<<ListboxSelect>>', lambda event: print_class_info(listbox.curselection()[0]))

        # Optional: configure grid weights for resizing
        self.class_frame.columnconfigure(1, weight=1)
        self.class_frame.rowconfigure(0, weight=1)


    def open_bestiary(self):
        filename = "Bestiary.csv"
        path = os.path.join(os.path.dirname(__file__), filename)

        if not os.path.exists(path):
            messagebox.showerror("Error", f"{filename} not found.")
            return

        # Toggle visibility: destroy if already open
        if hasattr(self, 'bestiary_frame') and self.bestiary_frame.winfo_exists():
            self.bestiary_frame.destroy()
            return

        # Create and show the Bestiary frame
        self.bestiary_frame = tk.Frame(self.root, width=500)
        self.bestiary_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10, rowspan=3)
        self.bestiary_frame.grid_propagate(False)  # Prevent auto-resizing  
        
        search_frame = tk.Frame(self.bestiary_frame)
        search_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(search_frame, text="Search:").pack(side='left')
        search_entry = tk.Entry(search_frame)
        search_entry.pack(side='left', fill='x', expand=True, padx=(5, 10))

        tree = ttk.Treeview(self.bestiary_frame, show='headings')
        tree.pack(fill='both', expand=True)

        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = list(csv.DictReader(csvfile))
            all_headers = reader[0].keys()
            visible_cols = ["Name", "Type", "CR", "AC", "HP"]
            rows = reader

        tree["columns"] = visible_cols
        for col in visible_cols:
            tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview(tree, _col, False))
            col_widths = {"Name": 150, "Type": 100, "CR": 50, "AC": 50, "HP": 60}
            tree.column(col, anchor="w", width=col_widths.get(col, 100), stretch=False)


        def populate_tree(filtered):
            tree.delete(*tree.get_children())
            for row in filtered:
                values = [row[col] for col in visible_cols]
                tree.insert("", "end", values=values, tags=(row["Name"],))

        populate_tree(rows)

        def on_search(*_):
            search_text = search_entry.get().lower()
            filtered = [row for row in rows if search_text in row["Name"].lower()]
            populate_tree(filtered)

        def on_item_click(event):
            item_id = tree.identify_row(event.y)
            if not item_id:
                return
            name = tree.item(item_id)["values"][0]
            for row in rows:
                if row["Name"] == name:
                    self.show_full_monster_info(row)
                    break

        tree.bind("<ButtonRelease-1>", on_item_click)
        search_entry.bind("<KeyRelease>", on_search)

        # Ensure layout expands correctly
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(0, weight=1)


    
    def open_items(self):
        filename = "Items.csv"
        path = os.path.join(os.path.dirname(__file__), filename)

        if not os.path.exists(path):
            messagebox.showerror("Error", f"{filename} not found.")
            return

        # Toggle visibility: destroy if already open
        if hasattr(self, 'item_frame') and self.item_frame.winfo_exists():
            self.item_frame.destroy()
            return

        # Create and show the Bestiary frame
        self.item_frame = tk.Frame(self.root, width=500)
        self.item_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10, rowspan=3)
        self.item_frame.grid_propagate(False)

        search_frame = tk.Frame(self.item_frame)
        search_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(search_frame, text="Search:").pack(side='left')
        search_entry = tk.Entry(search_frame)
        search_entry.pack(side='left', fill='x', expand=True, padx=(5, 10))

        tree = ttk.Treeview(self.item_frame, show='headings')
        tree.pack(fill='both', expand=True)

        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = list(csv.DictReader(csvfile))
            all_headers = reader[0].keys()
            visible_cols = ["Name", "Rarity", "Type", "Value", "Weight"]
            rows = reader

        tree["columns"] = visible_cols
        for col in visible_cols:
            tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview(tree, _col, False))
            tree.column(col, anchor="w", stretch=True) 
            # restricks size of columns to fit the frame
            col_widths = {"Name": 150, "Rarity": 100, "Type": 100, "Value": 50, "Weight": 50}
            tree.column(col, anchor="w", width=col_widths.get(col, 100), stretch=False)

        def populate_tree(filtered):
            tree.delete(*tree.get_children())
            for row in filtered:
                values = [row[col] for col in visible_cols]
                tree.insert("", "end", values=values, tags=(row["Name"],))

        populate_tree(rows)

        def on_search(*_):
            search_text = search_entry.get().lower()
            filtered = [row for row in rows if search_text in row["Name"].lower()]
            populate_tree(filtered)

        def on_item_click(event):
            item_id = tree.identify_row(event.y)
            if not item_id:
                return
            name = tree.item(item_id)["values"][0]
            for row in rows:
                if row["Name"] == name:
                    self.show_full_item_info(row)
                    break

        tree.bind("<ButtonRelease-1>", on_item_click)
        search_entry.bind("<KeyRelease>", on_search)


    def sort_treeview(self, tree, col, reverse):
        data = [(tree.set(k, col), k) for k in tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0]) if t[0].replace('.', '', 1).isdigit() else t[0].lower(), reverse=reverse)
        except Exception:
            data.sort(key=lambda t: t[0].lower(), reverse=reverse)

        for index, (_, k) in enumerate(data):
            tree.move(k, "", index)

        tree.heading(col, command=lambda: self.sort_treeview(tree, col, not reverse))

    def show_full_monster_info(self, monster_data):
        win = tk.Toplevel(root)
        win.title(monster_data["Name"])
        text = tk.Text(win, wrap=tk.WORD, width=80, height=30)
        for key, value in monster_data.items():
            text.insert(tk.END, f"{key}: {value}\n")
        text.config(state=tk.DISABLED)
        text.pack(padx=10, pady=10)

    def show_full_item_info(self, item_data):
        win = tk.Toplevel(root)
        win.title(item_data["Name"])
        text = tk.Text(win, wrap=tk.WORD, width=80, height=30)
        for key, value in item_data.items():
            text.insert(tk.END, f"{key}: {value}\n")
        text.config(state=tk.DISABLED)
        text.pack(padx=10, pady=10)

    def add_point_controls(self, frame, label, var, row):
        tracked_bars = {"EXP": "purple","HP": "red", "Spell Points": "blue", "Sorcery Points": "green", "Temp HP": "yellow"}

        if label in tracked_bars:
            ttk.Label(frame, text=label + ":").grid(row=row, column=0, sticky="e")
            bar_frame = tk.Frame(frame)
            bar_frame.grid(row=row, column=1, columnspan=2, sticky="ew")
            bar_frame.columnconfigure(0, weight=1)

            bar_canvas = tk.Canvas(bar_frame, height=20, width=150, bg="white", highlightthickness=1, relief="sunken")
            bar_canvas.grid(row=row, column=0, sticky="ew")

            value_label = tk.Label(bar_frame, bg="white")
            value_label.place(relx=0.5, rely=0.5, anchor="center")

            max_entry = ttk.Entry(frame, textvariable=self.max_values[label], width=4)
            max_entry.grid(row=row, column=3)

            def update_bar(*_):
                val = var.get()
                max_val = max(self.max_values[label].get(), 1)
                percent = min(max(val / max_val, 0), 1)

                bar_canvas.delete("all")
                bar_canvas.create_rectangle(0, 0, 150 * percent, 20, fill=tracked_bars[label])
                value_label.config(text=f"{val} / {max_val}")
            
            bar_canvas.bind("<Configure>", lambda e: update_bar())
            var.trace_add("write", lambda *_: update_bar())
            self.max_values[label].trace_add("write", lambda *_: update_bar())
            update_bar()

            if label == "EXP":
                ttk.Button(frame, text="+", command=lambda: var.set(min(var.get() + 100, self.max_values[label].get()))).grid(row=row, column=4)
                ttk.Button(frame, text="-", command=lambda: var.set(max(var.get() - 100, 0))).grid(row=row, column=5)
            else:
                ttk.Button(frame, text="+", command=lambda: var.set(min(var.get() + 1, self.max_values[label].get()))).grid(row=row, column=4)
                ttk.Button(frame, text="-", command=lambda: var.set(max(var.get() - 1, 0))).grid(row=row, column=5)
        else:
            ttk.Label(frame, text=label + ":").grid(row=row, column=0, sticky="e")
            ttk.Entry(frame, textvariable=var, width=4).grid(row=row, column=1)

            if label == "AC":
                ttk.Label(frame, text="Base " + label + ":").grid(row=row, column=2, sticky="e")
                ttk.Entry(frame, textvariable=self.max_values["AC"], width=4).grid(row=row, column=3)

            # ttk.Button(frame, text="+", command=lambda: var.set(var.get() + 1)).grid(row=row, column=4)
            # ttk.Button(frame, text="-", command=lambda: var.set(var.get() - 1)).grid(row=row, column=5)

    def update_modifier_label(self, var, label):
        def update(*args):
            value = var.get()
            mod = (value - 10) // 2
            label.config(text=f"Mod: {mod:+}")
        var.trace_add("write", update)
        update()

    def add_delete_spell(self):
        # Create a new window for adding/deleting spells
        spell_window = tk.Toplevel(self.root)
        spell_window.title("Add/Delete Spell")

        # Create a frame for the top controls (search bar, add/delete buttons)
        top_frame = ttk.Frame(spell_window)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # Create a label and dropdown for spell level
        ttk.Label(top_frame, text="Spell Level:").grid(row=0, column=0, padx=5)
        self.spell_level_var = tk.IntVar(value=0)
        level_dropdown = ttk.Combobox(top_frame, textvariable=self.spell_level_var, values=list(range(6)), state="readonly")
        level_dropdown.grid(row=0, column=1, padx=5)

        # Create an entry for the spell name
        self.spell_entry = ttk.Entry(top_frame, width=30)
        self.spell_entry.grid(row=0, column=2, padx=5)

        # Create buttons to add and delete spells
        ttk.Button(top_frame, text="Add Spell", command=self.add_spell).grid(row=0, column=3, padx=5)
        ttk.Button(top_frame, text="Delete Spell", command=self.delete_spell).grid(row=0, column=4, padx=5)
        ttk.Button(top_frame, text="Load Spells", command=lambda: self.update_spell_display(self.spell_notebook)).grid(row=0, column=5, padx=5)

        # Create a frame for the spell list
        spell_frame = ttk.Frame(spell_window)
        spell_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.spell_notebook = ttk.Notebook(spell_frame)
        self.spell_notebook.pack(expand=True, fill='both')
        self.update_spell_display(self.spell_notebook)

        # Add a close button at the bottom
        ttk.Button(spell_window, text="Close", command=spell_window.destroy).pack(pady=10)

    def show_all_spells(self):
        classes_window = tk.Toplevel(self.root)
        classes_window.title("Spellcasting Classes")

        for i, cls in enumerate(SPELL_CLASSES):
            display_name = cls.capitalize()
            btn = ttk.Button(
                classes_window,
                text=display_name,
                command=lambda c=cls: self.show_class_spells(c)
            )
            btn.grid(row=i, column=0, padx=10, pady=5)

    def show_class_spells(self, class_name):
        filename = f"{class_name.capitalize()}_Spells.csv"
        path = os.path.join(os.path.dirname(__file__), filename)

        if not os.path.exists(path):
            print(f"{filename} not found at {path}")
            return

        spells_by_level = {}

        def level_to_int(level_str):
            """Converts level like '1st', '2nd', '3rd', etc. to int, Cantrip -> 0"""
            level_str = level_str.strip().lower()
            if level_str == "cantrip" or level_str == "0":
                return 0
            match = re.match(r"(\d+)(st|nd|rd|th)?", level_str)
            return int(match.group(1)) if match else 99  # fallback for unknowns

        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                raw_level = row["Level"].strip()
                spell_name = row["Name"].strip()

                level_int = level_to_int(raw_level)
                level_key = "Cantrips" if level_int == 0 else f"Level {level_int}"

                if level_key not in spells_by_level:
                    spells_by_level[level_key] = []

                spells_by_level[level_key].append(spell_name)

        # New window for class spells
        spells_window = tk.Toplevel(root)
        spells_window.title(f"{class_name.capitalize()} Spells")

        notebook = ttk.Notebook(spells_window)
        notebook.pack(fill='both', expand=True)

        # Sort by level integer, with Cantrips (0) first
        def level_sort_key(label):
            if label == "Cantrips":
                return 0
            return int(label.split(" ")[1])  # "Level X" -> X

        max_columns = 3  # Number of columns per level tab
        for level in sorted(spells_by_level.keys(), key=level_sort_key):
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=level)

            spells = sorted(spells_by_level[level])
            for i, spell in enumerate(spells):
                row = i // max_columns
                col = i % max_columns
                btn = ttk.Button(frame, text=spell, command=lambda s=spell: self.show_spell(s, level))
                btn.grid(row=row, column=col, sticky="w", padx=10, pady=2)





    def update_spell_display(self, notebook):
        # Clear existing tabs
        for tab_id in notebook.tabs():
            notebook.forget(tab_id)

        spells_by_level = self.load_spells_from_csv()
        for level, spells in sorted(spells_by_level.items()):
            title = "Cantrips" if level == 0 else f"Level {level}"
            frame = ttk.Frame(notebook, padding=10)
            notebook.add(frame, text=title)

            for idx, spell_name in enumerate(spells):
                btn = ttk.Button(frame, text=spell_name, width=25,
                                command=lambda spell=spell_name: self.show_spell(spell,level))
                btn.grid(row=idx // 2, column=idx % 2, padx=5, pady=5)

    def add_spell(self):
        spell_name = self.spell_entry.get().strip()
        level = self.spell_level_var.get()
        if spell_name:
            if level not in self.spells:
                self.spells[level] = []
            self.spells[level].append(spell_name)
            self.spell_entry.delete(0, tk.END)
            self.update_spell_display(self.spell_notebook)

            # Append the new spell as [level, spell_name]
            if self.csv_path:
                with open(self.csv_path, 'a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow([level, spell_name])

                self.sort_csv_spells_by_level()


    def sort_csv_spells_by_level(self):
        if not self.csv_path:
            return

        with open(self.csv_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)

        # Split rows into stats and spells
        stats_rows = [row for row in rows if not row[0].isdigit()]
        spell_rows = [row for row in rows if row[0].isdigit()]

        # Sort spell rows by level (as integers), then spell name
        spell_rows.sort(key=lambda row: (int(row[0]), row[1].lower()))

        # Write stats + sorted spells back to file
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(stats_rows + spell_rows)

    def delete_spell(self):
        spell_name = self.spell_entry.get().strip()
        level = self.spell_level_var.get()
        path = os.path.join(os.path.dirname(__file__), 'character_data.csv')
        if spell_name:
            try:
                # Open the character_data.csv file
                with open(path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    rows = list(reader)

                # Find the row corresponding to the spell level (e.g., 0 for Cantrips, 1 for Level 1 spells)
                found = False
                for row in rows:
                    if row[0] == str(level):
                        if spell_name in row:
                            row.remove(spell_name)
                            found = True
                        break 

                if not found:
                    raise ValueError(f"Spell '{spell_name}' not found at level {level}.")

                # Write the updated data back to the CSV
                with open(path, mode='w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows(rows)

                # Clear the entry field and update the display
                self.spell_entry.delete(0, tk.END)
                self.update_spell_display(self.spell_notebook)
                self.save_to_csv()  # Persist the changes

            except (ValueError, KeyError) as e:
                messagebox.showerror("Error", str(e))

    def save_to_csv(self):
        spells_by_level_from_csv = self.load_spells_from_csv()
        self.spells = spells_by_level_from_csv
        if not self.csv_path:
            return

        with open(self.csv_path, 'w', newline='') as file:
            writer = csv.writer(file)

            # Save stats
            for key, var in self.stat_vars.items():
                writer.writerow([key, var.get()])
            
            # Save key stats
            writer.writerow(["Level", self.level.get()])
            writer.writerow(["EXP", self.exp.get()])
            writer.writerow(["HP", self.hp.get()])
            writer.writerow(["Temp HP", self.temp_hp.get()])
            writer.writerow(["AC", self.ac.get()])
            writer.writerow(["Speed", self.speed.get()])
            writer.writerow(["Spell Points", self.spell_points.get()])
            writer.writerow(["Actions", self.actions.get()])
            writer.writerow(["Sorcery Points", self.sorcery_points.get()])

            # Save max values
            for key, max_var in self.max_values.items():
                writer.writerow([f"Max {key}", max_var.get()])
                
            # Save character info
            character_info = {
                "Race": "Half-Elf",
                "Class": "Sorcerer (Draconic Bloodline)",
                "Background": "Sage",
                "Armor Proficiencies": "None",
                "Weapon Proficiencies": "Daggers, slings, quarterstaffs, light crossbows",
                "Tool Proficiencies": "None",
                "Saving Throws": "Constitution, Charisma",
                "Skills": "Arcana, Insight, Persuasion, History",
                "Spellcasting Ability": "Charisma",
                "Spell Save DC": "8 + Proficiency + CHA mod",
                "Spell Attack Bonus": "Proficiency + CHA mod",
                "Features": "Draconic Resilience: HP increase, AC = 13 + Dex mod if unarmored",
                "Languages": "Common, Elvish, Draconic"
            }

            # Save character info
            for key, value in self.character_info_data.items():
                writer.writerow(["Info", key, value])

            
            # Save spells
            for level, spells in self.spells.items():
                for spell in spells:
                    writer.writerow([f"{level}", spell])

            # Save inventory
            for item, data in self.inventory_items.items():
                writer.writerow(["Inventory", item, data["quantity"], data.get("equipped", False)])



    def load_from_csv(self):
        if not os.path.exists(self.csv_path):
            return  # If the file doesn't exist, skip loading
        self.character_info_data = {}
        self.spells.clear()
        self.inventory_items.clear()

        with open(self.csv_path, 'r') as file:
            reader = csv.reader(file)
            current_level = None
            for row in reader:
                if len(row) >= 3 and row[0] == "Inventory":
                    item = row[1].strip()
                    try:
                        qty = int(row[2].strip())
                    except ValueError:
                        qty = 1

                    # Handle equipped flag if present
                    equipped = False
                    if len(row) >= 4:
                        equipped_str = row[3].strip().lower()
                        equipped = equipped_str in ("true", "1", "yes")

                    self.inventory_items[item] = {
                        "quantity": qty,
                        "equipped": equipped
                    }
                    
                if len(row) >= 3 and row[0] == "Info":
                    self.character_info_data[row[1]] = row[2]

                if len(row) != 2:
                    continue

                key, value = row

                if key.startswith("Spell Level"):
                    try:
                        level = int(key.split()[-1])
                        current_level = level
                        self.spells[current_level] = []
                        continue
                    except ValueError:
                        pass

                try:
                    value = int(value)
                    if key in self.stat_vars:
                        self.stat_vars[key].set(value)
                    elif key == "Level":
                        self.level.set(value)
                    elif key == "EXP":
                        self.exp.set(value)
                    elif key == "HP":
                        self.hp.set(value)
                    elif key == "Temp HP":
                        self.temp_hp.set(value)
                    elif key == "AC":
                        self.ac.set(value)
                    elif key == "Speed":
                        self.speed.set(value)
                    elif key == "Spell Points":
                        self.spell_points.set(value)
                    elif key == "Actions":
                        self.actions.set(value)
                    elif key == "Sorcery Points":
                        self.sorcery_points.set(value)
                    elif key.startswith("Max "):
                        stat_name = key.split("Max ")[-1]
                        if stat_name in self.max_values:
                            self.max_values[stat_name].set(value)
                    elif current_level is not None:
                        self.spells[current_level].append(value)
                except ValueError:
                    pass

        self.update_spell_display(self.main_spell_notebook)
        self.update_inventory_display(self.inventory_notebook)

if __name__ == '__main__':
    root = tk.Tk()
    app = CharacterUI(root)
    root.mainloop()
