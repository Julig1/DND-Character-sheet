# DND-Tracker: A Tkinter-Based D&D 5e Character Management System

This repository contains `dnd_tracker.py`, a Python-based desktop application designed to support the management of Dungeons & Dragons 5th Edition (D&D 5e) characters. The application is implemented using the Tkinter GUI framework and includes comprehensive modules for character statistics, spellcasting mechanics, inventory tracking, and character metadata.

## Overview

The application provides a structured interface for real-time character sheet manipulation, tailored particularly to spellcasting classes (with a focus on sorcerers). It facilitates dynamic interactions such as experience point tracking with automatic level adjustment, spell point consumption, inventory management with equip status, and spellcasting customization via metamagic options.

## Features

- **Statistical Tracking**: Monitors base attributes (Strength, Dexterity, etc.), derived values (Armor Class, Hit Points, Speed), and progression metrics (Level, Experience Points).
- **Spellbook Management**: Loads spell data from CSV sources. Provides spell browsing, detailed descriptions, and contextual spellcasting actions with resource cost calculations.
- **Metamagic Module**: Displays all available metamagic effects. Allows review of descriptions and integration with casting logic.
- **Inventory System**: Supports addition, deletion, and equipment of items. Includes basic AC adjustment for equipped armor.
- **Bestiary Access**: Reads from a structured CSV file to allow filtered searching and detailed monster data presentation.
- **Character Metadata Editor**: Provides a GUI for modifying race, class, proficiencies, languages, and background features. Traits and class features are dynamically loaded from a structured JSON file (`data.json`).
- **Persistence**: Saves and loads character state through structured CSV files, enabling continuity between sessions.

## Installation

### Prerequisites

- Python 3.10.0 or higher
- Platform: Windows
- Tkinter version: 8.6

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/dnd_tracker.git
   cd dnd_tracker

2. Ensure the following auxiliary data files are present in the root directory:

  - character_data.csv
  - One or more *_Spells.csv files
  - Items.csv
  - Bestiary.csv
  - data.json

3. Run the application:

   ```bash
   python dnd_tracker.py
