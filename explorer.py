#!/usr/bin/env python3
import os
import re
import csv
import random
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.status import Status
from rich.text import Text
from rich import box
from rich.align import Align
import questionary

console = Console()

STYLE_CYAN = questionary.Style([
    ('qmark', 'fg:#00ffff bold'),
    ('question', 'bold'),
    ('selected', 'fg:#00ffff bold'),
    ('pointer', 'fg:#00ffff bold'),
    ('highlighted', 'fg:#00ffff bold'),
    ('answer', 'fg:#00ffff bold'),
])

# Common date formats to check
DATE_PATTERNS = [
    re.compile(r'^\d{4}-\d{2}-\d{2}$'),          # YYYY-MM-DD
    re.compile(r'^\d{2}/\d{2}/\d{4}$'),          # MM/DD/YYYY or DD/MM/YYYY
    re.compile(r'^\d{2}-\d{2}-\d{4}$'),          # MM-DD-YYYY or DD-MM-YYYY
    re.compile(r'^\d{4}/\d{2}/\d{2}$'),          # YYYY/MM/DD
]

def clean_path(path_str):
    """Cleans paths copied or drag-and-dropped into the terminal."""
    if not path_str:
        return ""
    p = path_str.strip()
    # PowerShell sometimes prefixes paths with '& '
    if p.startswith('& '):
        p = p[2:].strip()
    # Strip enclosing quotes
    p = p.strip('"').strip("'")
    # Replace backslash-escaped spaces
    p = p.replace('\\ ', ' ')
    return p

def is_missing(val_str):
    """Checks if a string value counts as a missing/null cell."""
    val_clean = val_str.strip()
    if not val_clean:
        return True
    # Common representations of missing data
    if val_clean.lower() in {'na', 'n/a', 'null', 'nan', 'none', '-'}:
        return True
    return False

def get_value_type(val_str):
    """Detects the likely data type of a single string value."""
    val_clean = val_str.strip()
    if not val_clean:
        return None
    
    # Try Boolean
    if val_clean.lower() in {'true', 'false'}:
        return 'Boolean'
    
    # Try Integer
    try:
        int(val_clean)
        return 'Integer'
    except ValueError:
        pass
    
    # Try Float
    try:
        float(val_clean)
        return 'Float'
    except ValueError:
        pass
        
    # Try Date
    for pattern in DATE_PATTERNS:
        if pattern.match(val_clean):
            return 'Date'
            
    return 'String'

def read_csv_encoding(filepath):
    """Detects if the file is UTF-8 or requires a fallback like latin-1."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read(4096)
        return 'utf-8'
    except UnicodeDecodeError:
        return 'latin-1'

def detect_dialect(filepath, encoding):
    """Detects the CSV delimiter and quotation dialect using csv.Sniffer."""
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            sample = f.read(4096)
        if not sample.strip():
            return None
        dialect = csv.Sniffer().sniff(sample)
        return dialect
    except Exception:
        # Fallback to None if sniffing fails
        return None

def get_csv_files():
    """Lists all .csv files in the current directory."""
    files = [f for f in os.listdir('.') if f.lower().endswith('.csv') and os.path.isfile(f)]
    return sorted(files)

def print_header():
    """Prints the application header."""
    console.clear()
    title = "[bold cyan]ExCSV[/bold cyan]\n[dim white]Sleek CSV Diagnostics & Analysis[/dim white]"
    console.print(Align.center(Panel(
        title,
        border_style="cyan",
        padding=(1, 4),
        box=box.ROUNDED,
        expand=False
    )))

def prompt_file_selection():
    """Prompts the user to select a CSV file interactively."""
    csv_files = get_csv_files()
    choices = []
    
    for f in csv_files:
        try:
            size_bytes = os.path.getsize(f)
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            choices.append(f"{f} ({size_str})")
        except Exception:
            choices.append(f)
        
    choices.append("[Enter file path manually]")
    choices.append("[Exit]")
    
    choice = questionary.select(
        "Select a CSV file to explore:",
        choices=choices,
        style=STYLE_CYAN
    ).ask()
    
    if not choice or choice == "[Exit]":
        return None
        
    if choice == "[Enter file path manually]":
        path = questionary.text("Enter the path to the CSV file:").ask()
        if not path:
            return None
        path = clean_path(path)
        if not os.path.isfile(path):
            console.print(f"[bold red]Error:[/bold red] File not found at '{path}'")
            questionary.press_any_key_to_continue().ask()
            return prompt_file_selection()
        return path
        
    # Extract filename from selection (reversing size label)
    if " (" in choice:
        filename = choice.rsplit(" (", 1)[0]
    else:
        filename = choice
    return filename

def analyze_csv(filepath):
    """Parses and calculates descriptive statistics for the CSV file."""
    encoding = read_csv_encoding(filepath)
    dialect = detect_dialect(filepath, encoding)
    
    # File size string
    try:
        file_size = os.path.getsize(filepath)
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
    except Exception:
        size_str = "Unknown"

    headers = []
    row_count = 0
    column_count = 0
    
    col_missing_counts = []
    col_type_counts = []  
    col_samples = []      
    
    with Status(f"[bold yellow]Parsing and analyzing '{os.path.basename(filepath)}'...[/bold yellow]", spinner="dots"):
        try:
            with open(filepath, 'r', encoding=encoding, newline='') as f:
                if dialect:
                    reader = csv.reader(f, dialect)
                else:
                    reader = csv.reader(f)
                
                try:
                    headers = next(reader)
                except StopIteration:
                    return {
                        "error": "The selected file is empty.",
                        "filename": os.path.basename(filepath),
                        "filepath": filepath,
                        "filesize": size_str
                    }
                
                # Trim spaces from header names to look clean
                headers = [h.strip() if h else f"Unnamed_Col_{i}" for i, h in enumerate(headers)]
                column_count = len(headers)
                
                col_missing_counts = [0] * column_count
                col_type_counts = [{"Integer": 0, "Float": 0, "Boolean": 0, "Date": 0, "String": 0} for _ in range(column_count)]
                col_samples = [None] * column_count
                
                for row in reader:
                    # Skip completely empty rows
                    if not row or all(not cell.strip() for cell in row):
                        continue
                        
                    row_count += 1
                    
                    for col_idx in range(column_count):
                        val = row[col_idx] if col_idx < len(row) else ""
                        
                        if is_missing(val):
                            col_missing_counts[col_idx] += 1
                        else:
                            # Keep first non-missing value as sample
                            if col_samples[col_idx] is None:
                                col_samples[col_idx] = val.strip()
                            
                            val_type = get_value_type(val)
                            if val_type:
                                col_type_counts[col_idx][val_type] += 1
                                
        except Exception as e:
            return {
                "error": f"Error parsing CSV: {str(e)}",
                "filename": os.path.basename(filepath),
                "filepath": filepath,
                "filesize": size_str
            }
            
    # Compile variable details
    columns_stats = []
    for col_idx in range(column_count):
        header_name = headers[col_idx]
        missing_cnt = col_missing_counts[col_idx]
        missing_pct = (missing_cnt / row_count * 100) if row_count > 0 else 0.0
        
        # Determine dominant data type
        t_counts = col_type_counts[col_idx]
        dominant_type = 'Empty'
        max_count = 0
        for t, count in t_counts.items():
            if count > max_count:
                max_count = count
                dominant_type = t
                
        # Handle fallback for sample values but no dominant type
        if dominant_type == 'Empty' and col_samples[col_idx] is not None:
            dominant_type = 'String'
            
        columns_stats.append({
            "index": col_idx + 1,
            "name": header_name,
            "type": dominant_type,
            "missing_count": missing_cnt,
            "missing_pct": missing_pct,
            "sample": col_samples[col_idx] if col_samples[col_idx] is not None else "[ALL MISSING]"
        })
        
    total_cells = row_count * column_count
    total_missing_cells = sum(col_missing_counts)
    overall_missing_pct = (total_missing_cells / total_cells * 100) if total_cells > 0 else 0.0
    
    return {
        "filename": os.path.basename(filepath),
        "filepath": os.path.abspath(filepath),
        "filesize": size_str,
        "encoding": encoding,
        "delimiter": dialect.delimiter if (dialect and dialect.delimiter) else ",",
        "nrows": row_count,
        "ncolumns": column_count,
        "total_cells": total_cells,
        "total_missing": total_missing_cells,
        "overall_missing_pct": overall_missing_pct,
        "columns": columns_stats
    }

def display_results(stats):
    """Outputs the diagnostic results in a beautiful Rich interface."""
    console.print()
    if "error" in stats:
        console.print(Panel(
            f"[bold red]Analysis Failed[/bold red]\n\n[white]{stats['error']}[/white]",
            border_style="red",
            title=f"Error: {stats['filename']}"
        ))
        return
        
    # Set overall missing style color coding
    overall_missing_style = "green"
    if stats['overall_missing_pct'] > 10.0:
        overall_missing_style = "bold red"
    elif stats['overall_missing_pct'] > 0.0:
        overall_missing_style = "yellow"
        
    summary_text = (
        f"[bold white]File Location:[/bold white] {stats['filepath']}\n"
        f"[bold white]File Size:[/bold white]     {stats['filesize']}  |  "
        f"[bold white]Encoding:[/bold white]  {stats['encoding']}  |  "
        f"[bold white]Delimiter:[/bold white] '{stats['delimiter']}'\n\n"
        f"[bold green]Rows (nrows):[/bold green]      {stats['nrows']:,}\n"
        f"[bold green]Columns (ncols):[/bold green]  {stats['ncolumns']:,}\n"
        f"[bold white]Total Cells:[/bold white]      {stats['total_cells']:,}\n"
        f"[bold white]Missing Cells:[/bold white]    [{overall_missing_style}]{stats['total_missing']:,} ({stats['overall_missing_pct']:.2f}%)[/{overall_missing_style}]"
    )
    
    console.print(Align.center(Panel(
        summary_text,
        title=f"[bold green]CSV Summary: {stats['filename']}[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        expand=False
    )))
    console.print()
    
    # Columns statistics table
    table = Table(
        title="[bold cyan]Column (Variable) Analysis & Details[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
        border_style="dim blue",
        box=box.ROUNDED
    )
    
    table.add_column("#", justify="center", style="dim", width=4)
    table.add_column("Variable Name", style="bold cyan")
    table.add_column("Type", style="bright_green")
    table.add_column("Missing Count", justify="right")
    table.add_column("Missing %", justify="right")
    table.add_column("Sample Value", style="italic yellow", max_width=40)
    
    for col in stats['columns']:
        missing_cnt = col['missing_count']
        missing_pct = col['missing_pct']
        
        # Highlight missing percentage
        if missing_pct == 0.0:
            missing_cnt_str = "[green]0[/green]"
            missing_pct_str = "[green]0.0%[/green]"
        elif missing_pct <= 10.0:
            missing_cnt_str = f"[yellow]{missing_cnt:,}[/yellow]"
            missing_pct_str = f"[yellow]{missing_pct:.1f}%[/yellow]"
        else:
            missing_cnt_str = f"[bold red]{missing_cnt:,}[/bold red]"
            missing_pct_str = f"[bold red]{missing_pct:.1f}%[/bold red]"
            
        sample_val = str(col['sample']).replace('\n', ' ').replace('\r', '')
        if len(sample_val) > 37:
            sample_val = sample_val[:37] + "..."
            
        table.add_row(
            str(col['index']),
            col['name'],
            col['type'],
            missing_cnt_str,
            missing_pct_str,
            sample_val
        )
        
    console.print(Align.center(table))
def select_and_clean_y_variable(filepath, stats):
    """Prompts the user to select the Y variable and handles cleaning/saving to a copy."""
    if "error" in stats:
        return
        
    console.print()
    console.print(Align.center("[bold cyan]Y Variable Selection & Cleaning[/bold cyan]"))
    console.print()
    
    # 1. Build selection choices from columns
    choices = []
    for col in stats['columns']:
        choices.append(f"#{col['index']}: {col['name']} ({col['type']}) - {col['missing_count']} missing")
    choices.append("[Cancel]")
    
    choice = questionary.select(
        "Select the Y variable (dependent variable) using up/down arrows:",
        choices=choices,
        style=STYLE_CYAN
    ).ask()
    
    if not choice or choice == "[Cancel]":
        console.print("[yellow]Y variable selection cancelled.[/yellow]")
        return
        
    # Find matching column stats
    selected_col = None
    for col in stats['columns']:
        if choice.startswith(f"#{col['index']}: "):
            selected_col = col
            break
            
    if not selected_col:
        console.print("[red]Invalid selection.[/red]")
        return
        
    y_name = selected_col['name']
    col_idx = selected_col['index'] - 1
    missing_cnt = selected_col['missing_count']
    
    delete_missing = False
    if missing_cnt > 0:
        delete_confirm = questionary.confirm(
            f"Y variable '{y_name}' has {missing_cnt} missing values. Is it okay to delete these rows?",
            style=STYLE_CYAN
        ).ask()
        if delete_confirm:
            delete_missing = True
        else:
            console.print("[yellow]Retaining rows with missing Y values.[/yellow]")
    else:
        console.print(f"[green]Y variable '{y_name}' has no missing values.[/green]")
        
    # 2. Save copy of the CSV to exact same location with {name}_ExCSV.csv
    dir_name = os.path.dirname(filepath)
    base_name = os.path.basename(filepath)
    name_part, ext = os.path.splitext(base_name)
    new_filename = f"{name_part}_ExCSV.csv"
    new_filepath = os.path.join(dir_name, new_filename) if dir_name else new_filename
    
    encoding = stats['encoding']
    delimiter = stats['delimiter']
    
    rows_to_write = []
    header_row = None
    deleted_count = 0
    
    try:
        with open(filepath, 'r', encoding=encoding, newline='') as f:
            reader = csv.reader(f, delimiter=delimiter)
            header_row = next(reader)
            
            for row in reader:
                # Skip completely empty rows
                if not row or all(not cell.strip() for cell in row):
                    continue
                    
                val = row[col_idx] if col_idx < len(row) else ""
                if delete_missing and is_missing(val):
                    deleted_count += 1
                    continue
                    
                rows_to_write.append(row)
    except Exception as e:
        console.print(f"[bold red]Error reading original file for copying:[/bold red] {e}")
        return
        
    try:
        with open(new_filepath, 'w', encoding=encoding, newline='') as f:
            writer = csv.writer(f, delimiter=delimiter)
            writer.writerow(header_row)
            writer.writerows(rows_to_write)
            
        message = f"Saved a copy of the CSV to:\n[cyan]{new_filepath}[/cyan]\n\n"
        if delete_missing:
            message += f"Deleted {deleted_count} rows with missing values in Y variable '[bold]{y_name}[/bold]'.\n"
        else:
            message += f"No rows were deleted (retained all data with Y variable '[bold]{y_name}[/bold]').\n"
        message += "Original file remains untouched."
        
        console.print(Align.center(Panel(
            message,
            title="Export Successful",
            border_style="green",
            box=box.ROUNDED,
            expand=False
        )))
        
        # 3. Train/Test split option
        console.print()
        split_confirm = questionary.confirm(
            "Would you like to split the cleaned dataset into Train and Test sets?",
            style=STYLE_CYAN
        ).ask()
        
        if split_confirm:
            # Proportion selection (5 intervals)
            prop_choices = [
                "10-90 (10% Test / 90% Train)",
                "15-85 (15% Test / 85% Train)",
                "20-80 (20% Test / 80% Train)",
                "25-75 (25% Test / 75% Train)",
                "30-70 (30% Test / 70% Train)"
            ]
            prop_choice = questionary.select(
                "Select split proportion (left side is test %, right is train %):",
                choices=prop_choices,
                style=STYLE_CYAN
            ).ask()
            
            if prop_choice:
                # Parse test size
                test_pct = int(prop_choice.split('-')[0])
                test_fraction = test_pct / 100.0
                
                # Seed prompt
                seed_input = questionary.text(
                    "Enter random seed (integer):",
                    default="42",
                    style=STYLE_CYAN
                ).ask()
                
                try:
                    seed_val = int(seed_input)
                except ValueError:
                    console.print("[yellow]Invalid seed. Defaulting to 42.[/yellow]")
                    seed_val = 42
                
                # Split rows
                num_rows = len(rows_to_write)
                num_test = int(round(num_rows * test_fraction))
                if num_rows >= 2:
                    num_test = max(1, min(num_test, num_rows - 1))
                else:
                    num_test = 0
                
                indices = list(range(num_rows))
                rng = random.Random(seed_val)
                rng.shuffle(indices)
                
                test_indices = set(indices[:num_test])
                
                # Filter rows keeping original order in split
                test_rows = [rows_to_write[i] for i in range(num_rows) if i in test_indices]
                train_rows = [rows_to_write[i] for i in range(num_rows) if i not in test_indices]
                
                test_filename = f"{name_part}_Test_ExCSV.csv"
                train_filename = f"{name_part}_Train_ExCSV.csv"
                test_filepath = os.path.join(dir_name, test_filename) if dir_name else test_filename
                train_filepath = os.path.join(dir_name, train_filename) if dir_name else train_filename
                
                try:
                    with open(test_filepath, 'w', encoding=encoding, newline='') as f:
                        writer = csv.writer(f, delimiter=delimiter)
                        writer.writerow(header_row)
                        writer.writerows(test_rows)
                        
                    with open(train_filepath, 'w', encoding=encoding, newline='') as f:
                        writer = csv.writer(f, delimiter=delimiter)
                        writer.writerow(header_row)
                        writer.writerows(train_rows)
                        
                    split_msg = (
                        f"[bold green]Split Successful![/bold green]\n\n"
                        f"[bold white]Parameters:[/bold white] Seed: {seed_val}  |  {test_pct}% Test / {100-test_pct}% Train\n\n"
                        f"  • [bold green]Train Set[/bold green] ({len(train_rows)} rows): [cyan]{train_filepath}[/cyan]\n"
                        f"  • [bold blue]Test Set[/bold blue]  ({len(test_rows)} rows): [cyan]{test_filepath}[/cyan]"
                    )
                    console.print(Align.center(Panel(
                        split_msg,
                        title="Split Export Complete",
                        border_style="green",
                        box=box.ROUNDED,
                        expand=False
                    )))
                except Exception as e:
                    console.print(f"[bold red]Error writing split files:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]Error writing to new file:[/bold red] {e}")

def main():
    while True:
        print_header()
        
        # Display files in current directory to help them see what's available
        csv_files = get_csv_files()
        if csv_files:
            console.print("[dim]CSV files in current directory:[/dim]")
            for f in csv_files:
                console.print(f"  [dim]• {f}[/dim]")
            console.print()
            
        console.print("[bold cyan]Drag & Drop a CSV file here, type its path, or press [bold white]Enter[/bold white] to open picker:[/bold cyan]")
        try:
            path_input = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Goodbye![/yellow]")
            break
            
        filepath = None
        if path_input:
            cleaned = clean_path(path_input)
            if os.path.isfile(cleaned):
                filepath = cleaned
            else:
                console.print(f"[bold red]Error:[/bold red] File not found at '{cleaned}'")
                questionary.press_any_key_to_continue().ask()
                continue
        else:
            filepath = prompt_file_selection()
            if not filepath:
                break
                
        stats = analyze_csv(filepath)
        display_results(stats)
        
        # Y-variable selection, cleaning, and train/test splitting
        select_and_clean_y_variable(filepath, stats)
        
        # Offer option to restart or quit
        again = questionary.confirm("Would you like to explore another CSV file?", style=STYLE_CYAN).ask()
        if not again:
            console.print("[yellow]Goodbye![/yellow]")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Program interrupted. Goodbye![/yellow]")
