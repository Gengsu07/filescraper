import csv
import os
import queue
import sys
import tkinter as tk
from threading import Thread
from tkinter import PhotoImage, filedialog, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator
from ttkbootstrap import Style

from excluded_files import excluded_files
from included_files import included_ext

data_queue = queue.Queue()

INCLUDED_EXTENSIONS = included_ext
EXCLUDED_EXTENSIONS = excluded_files
EXCLUDED_STARTSWITH = {
    ".dll",
    ".cip",
    ".wim",
    ".sys",
    ".nlp",
    ".ppg",
    ".fon",
    ".ctypes",
    ".LOG",
    ".APACHE",
}
current_canvas = None


def list_files_thread(directory):
    # Start the progress bar
    file_progress.start(10)
    data_queue.put("start_listing")
    list_files(directory)
    data_queue.put("end_listing")
    # Stop the progress bar
    file_progress.stop()
    data_queue.put("done")


def show_charts_thread():
    # Start the progress bar
    global current_canvas
    chart_progress.start(10)
    data_queue.put("start_listing")

    data = aggregate_data()
    data_queue.put(data)
    data_queue.put("end_listing")
    # Stop the progress bar
    chart_progress.stop()
    data_queue.put("done")


def select_directory():
    directory = filedialog.askdirectory()
    if directory:
        Thread(target=list_files_thread, args=(directory,)).start()


def list_files(directory):
    for i in table.get_children():
        table.delete(i)
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Exclude Windows files
            _, extension = os.path.splitext(file)
            # if (
            #     not extension
            #     or any(extension.startswith(ext) for ext in EXCLUDED_STARTSWITH)
            #     or extension in EXCLUDED_EXTENSIONS
            # ):
            #     continue  # Skip this file

            if (
                extension in INCLUDED_EXTENSIONS
                and extension not in EXCLUDED_EXTENSIONS
                and "RECYCLE.BIN" not in os.path.join(root, file)
            ):
                filepath = os.path.join(root, file)
                size = os.path.getsize(filepath)
                formatted_size = format_size(size)
                name, extension = os.path.splitext(file)
                table.insert(
                    "", tk.END, values=(name, extension, formatted_size, size, filepath)
                )


def format_size(size):
    # 1024 bytes = 1 Kilobyte (KB)
    if size < 1024:
        return f"{size} bytes"
    # 1024 Kilobytes = 1 Megabyte (MB)
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    # 1024 Megabytes = 1 Gigabyte (GB)
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    # For sizes in Gigabytes
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"


def export_to_csv():
    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv", filetypes=[("CSV files", "*.csv")]
    )
    if not file_path:  # If no file is selected, return
        return

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Name", "Extension", "Formated Size", "Size", "Full Path"])
        for child in table.get_children():
            writer.writerow(table.item(child)["values"])


def size_to_bytes(size_str):
    size, unit = size_str.split()
    size = float(size)

    unit_factors = {"bytes": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}

    return int(size * unit_factors[unit])


def aggregate_data():
    # Dictionary to store total size and count for each extension
    data = {}
    for child in table.get_children():
        _, ext, _, size, _ = table.item(child)["values"]
        # size = size_to_bytes(size_str)  # Convert size back to bytes
        if ext in data:
            data[ext]["size"] += size
            data[ext]["count"] += 1
        else:
            data[ext] = {"size": size, "count": 1}
    return data


def update_charts(data):
    data = data

    # Sort data by size and then by count
    sorted_by_size = sorted(data.items(), key=lambda x: x[1]["size"], reverse=False)
    sorted_by_count = sorted(data.items(), key=lambda x: x[1]["count"], reverse=False)

    # Separate the data into lists for plotting
    extensions_by_size = [ext for ext, _ in sorted_by_size]
    sizes = [data[ext]["size"] for ext in extensions_by_size]
    extensions_by_count = [ext for ext, _ in sorted_by_count]
    counts = [data[ext]["count"] for ext in extensions_by_count]

    # Create the figure and axes for the plots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # Plot the total size chart
    ax1.barh(extensions_by_size, sizes, color="skyblue")
    ax1.set_xlabel("Total ukuran file")
    ax1.set_ylabel("File Ekstensi")
    ax1.set_title("Total Ukuran file per Ekstensi")
    ax1.xaxis.set_major_locator(MaxNLocator(integer=True))

    # Plot the file count chart
    ax2.barh(extensions_by_count, counts, color="lightgreen")
    ax2.set_xlabel("Jumlah File")
    ax2.set_ylabel("File Ekstensi")
    ax2.set_title("Jumlah File per Ektensi")
    ax2.xaxis.set_major_locator(MaxNLocator(integer=True))

    fig.tight_layout()
    # Display the plots
    canvas = FigureCanvasTkAgg(fig, master=chart_frame)  # Embedding the plot in Tkinter
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)


def check_queue():
    try:
        message = data_queue.get_nowait()
        if isinstance(message, dict):
            # If the message is a dictionary, assume it's the chart data
            update_charts(message)
        elif message == "start_chart":
            # Prepare to display chart (if needed)
            pass
        elif message == "done":
            # Finalize any pending tasks (if needed)
            pass
    except queue.Empty:
        # No new messages in the queue
        pass
    finally:
        # Schedule the next check
        root.after(100, check_queue)


# Initialize Tkinter and ttkbootstrap
style = Style(theme="litera")
root = style.master
root.title("FileScraper by Gengsu07")
root.geometry("1024x800")

if getattr(sys, "frozen", False):
    # The application is frozen
    datadir = sys._MEIPASS
else:
    # The application is not frozen
    datadir = os.path.dirname(__file__)

# Now use datadir to construct the full path to your file
image_path = os.path.join(datadir, "palestine.png")
icon = PhotoImage(file=image_path)  # or .gif
root.iconphoto(True, icon)

# Tab Control
tab_control = ttk.Notebook(root)
tab1 = ttk.Frame(tab_control)
tab2 = ttk.Frame(tab_control)
tab_control.add(tab1, text="Files")
tab_control.add(tab2, text="Charts")
tab_control.pack(expand=1, fill="both")

# Contents for Tab 1
select_button = tk.Button(tab1, text="Select Directory", command=select_directory)
select_button.pack(pady=5, side="top", anchor="center")
export_button = tk.Button(tab1, text="Export to CSV", command=export_to_csv)
export_button.pack(pady=5, side="top", anchor="center")
columns = ("Name", "Extension", "Formated Size", "Size", "Full Path")

# Progress bar for file listing
file_progress = ttk.Progressbar(tab1, orient="horizontal", mode="indeterminate")
file_progress.pack(fill="x", padx=10, pady=5)

table = ttk.Treeview(tab1, columns=columns, show="headings")

# Configure table headers
for col in columns:
    table.heading(col, text=col)
    table.column(col, anchor="center")

# Set header background color
table.pack(expand=True, fill="both", padx=10, pady=10)
style = ttk.Style()
style.configure("Treeview.Heading", background="#f0f0f0")


# Add vertical scrollbar
scrollbar = ttk.Scrollbar(tab1, orient="vertical", command=table.yview)
scrollbar.place(relx=1, rely=0, relheight=1, anchor="ne")
# scrollbar.pack(side="right", fill="y")
table.configure(yscrollcommand=scrollbar.set)


# Contents for Tab 2
chart_frame = ttk.Frame(tab2)
chart_frame.pack(fill="both", expand=True)
show_charts_button = tk.Button(
    chart_frame,
    text="Show Charts",
    command=lambda: Thread(target=show_charts_thread).start(),
)
show_charts_button.pack(pady=10)


# Progress bar for chart creation
chart_progress = ttk.Progressbar(tab2, orient="horizontal", mode="indeterminate")
chart_progress.pack(fill="x", padx=10, pady=5)
# Start the GUI


# Schedule the first check
root.after(100, check_queue)

root.mainloop()
