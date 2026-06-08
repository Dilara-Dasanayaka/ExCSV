# ExCSV 📊

ExCSV is a sleek, lightweight, and interactive command-line interface (CLI) tool for exploring and diagnosing CSV files directly inside Windows Command Prompt (CMD) or PowerShell. 

Designed for speed and memory efficiency, it analyzes CSV files of any size without heavy library overhead, providing key metadata, column types, and data quality insights instantly.

---

## Key Features

- **Interactive File Picker:** Automatically lists CSV files in the current folder with their file sizes, allowing selection via arrow keys.
- **Smart Path Input:** Fallback option to type or paste a custom path manually.
- **Auto-Detect Architecture:**
  - Delimiter and quote sniffing (handles comma, tab, semicolon, etc.).
  - File encoding detection (fallback to `latin-1` if `utf-8` fails).
- **Column-Level Analysis:**
  - Auto-infers dominant data types per column (`Integer`, `Float`, `Boolean`, `Date`, `String`).
  - Identifies missing value variants (e.g. empty strings, `N/A`, `NaN`, `null`, `none`, `-`).
  - Displays missing counts and percentage color-coding (Green = 0%, Yellow <= 10%, Red > 10%).
  - Extracts the first non-null sample value for each column.
- **Y-Variable Cleaning & Row Deletion:** Prompts selection of a Y variable (dependent variable) via arrow keys. If missing values are present, it asks to delete those rows and exports the result as a copy (`{name}_ExCSV.csv`) in the same location, keeping the original file completely safe.
- **Train/Test Dataset Splitting:** Optionally separates the cleaned dataset into training and testing datasets.
  - Allows selecting from 5 predefined split intervals: `10-90`, `15-85`, `20-80`, `25-75`, and `30-70` (where left side is Test % and right side is Train %).
  - Accepts a custom random seed (integer) to ensure reproducible splits.
  - Automatically exports `{name}_Test_ExCSV.csv` and `{name}_Train_ExCSV.csv` to the exact same directory.
- **Premium Aesthetics:** Outputs metadata and metrics in beautifully formatted, centered terminal panels and tables powered by the `rich` library.

---

## Installation

### Prerequisites
- Python 3.8 or higher installed on your system.

### Dependencies
Install the required packages using `pip`:

```bash
pip install -r requirements.txt
```

---

## How to Run

Simply launch the Python script from your terminal:

```bash
python explorer.py
```

### Usage Steps:
1. **Select a File:** Choose from the list of `.csv` files found in the current folder, or select `[Enter file path manually]` to input a custom absolute/relative file path.
2. **View Diagnostics:** Review the visual summary panel (rows, columns, encoding, delimiter) and the detailed variable statistics table.
3. **Select & Clean Y-Variable:** Choose a Y-variable using arrow keys. If it has missing rows, select whether to delete those rows to make the dataset suitable for analysis.
4. **Train/Test Split:** Choose whether to split your data, select one of the 5 split proportions, and provide a random seed.
5. **Auto-Export:** Exports `{name}_ExCSV.csv` (main cleaned file), as well as `{name}_Test_ExCSV.csv` and `{name}_Train_ExCSV.csv` (split sets) to the exact same location.
6. **Loop or Exit:** Confirm if you want to explore another CSV or exit the application.

---

## Project Structure

```text
ExCSV/
│
├── explorer.py         # Main interactive CLI application script
├── requirements.txt    # Project Python dependencies (rich, questionary)
├── employees.csv       # Test dataset (employee registry with missing cells)
├── sales.csv           # Test dataset (sales transactions with missing cells)
└── README.md           # Project documentation
```

---

## Future Roadmap (Next Stages)

- **Descriptive Statistics:** Calculate mean, median, min, max, and unique counts for numeric columns.
- **Data Filtering:** Select and filter rows based on column conditions.
- **Export Reports:** Generate HTML or Markdown reports of the CSV health diagnostics.
