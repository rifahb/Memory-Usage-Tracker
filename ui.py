
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os

def read_kernel_memory():
    try:
        with open("/proc/mem_tracker") as f:
            lines = f.readlines()
            used = int(lines[0].split(":")[1].strip())
            total = int(lines[1].split(":")[1].strip())
            percent = (used / total) * 100 if total > 0 else 0
            return used, total, percent
    except Exception:
        return 0, 1, 0

def get_process_memory_info():
    process_info = []
    for pid_str in os.listdir("/proc"):
        if pid_str.isdigit():
            pid = int(pid_str)
            try:
                with open(f"/proc/{pid}/status", 'r') as f:
                    lines = f.readlines()
                    name = ""
                    vmrss_kb = 0
                    for line in lines:
                        if line.startswith("Name:"):
                            name = line.split(":")[1].strip()
                        elif line.startswith("VmRSS:"):
                            vmrss_str = line.split(":")[1].strip()
                            vmrss_kb_str = vmrss_str.replace(" kB", "")
                            try:
                                vmrss_kb = int(vmrss_kb_str)
                            except ValueError:
                                vmrss_kb = 0
                            break
                    if name:
                        process_info.append({"pid": pid, "name": name, "memory_kb": vmrss_kb})
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"Error reading /proc/{pid}/status: {e}")

    process_info.sort(key=lambda x: x['memory_kb'], reverse=True)
    return process_info

class MemoryTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("🧠 System Memory Tracker")
        self.geometry("980x750")
        self.dark_mode = True

        # Fonts
        self.base_font = ("Segoe UI Variable", 14)
        self.title_font = ("Segoe UI Variable", 26, "semibold")
        self.label_font = ("Segoe UI Variable", 15)
        self.button_font = ("Segoe UI Variable", 13, "bold")
        self.process_font = ("Consolas", 11)

        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.configure_styles()

        # Notebook (Tabbed Interface)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=15, padx=15, fill='both', expand=True)

        # Kernel Memory Tab
        self.kernel_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.kernel_tab, text='Kernel Memory')
        self.create_kernel_memory_tab()

        # Process Memory Tab
        self.process_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.process_tab, text='Process Memory')
        self.create_process_memory_tab()

        # Buttons frame (moved to the main window)
        btn_frame = tk.Frame(self, bg=self._get_bg_color())
        btn_frame.pack(pady=(10, 20))

        # Pause/Resume button
        self.is_paused = False
        self.pause_button = ttk.Button(btn_frame, text="Pause Updates", command=self.toggle_pause)
        self.pause_button.grid(row=0, column=0, padx=10)

        # Save graph button
        self.save_button = ttk.Button(btn_frame, text="Save Graph", command=self.save_graph)
        self.save_button.grid(row=0, column=1, padx=10)

        # Toggle theme button
        self.theme_button = ttk.Button(btn_frame, text="Toggle Theme", command=self.toggle_theme)
        self.theme_button.grid(row=0, column=2, padx=10)

        # Data storage for kernel memory
        self.memory_log = []
        self.threshold = 80
        self.alert_shown = False

        self.update_ui()

    def create_kernel_memory_tab(self):
        # Header
        self.kernel_header = ttk.Label(self.kernel_tab, text="🧠 Kernel Memory Overview", style="Title.TLabel")
        self.kernel_header.pack(pady=(20, 15))

        # Kernel Memory Info label
        self.kernel_label_var = tk.StringVar()
        self.kernel_info_label = ttk.Label(self.kernel_tab, textvariable=self.kernel_label_var, style="TLabel")
        self.kernel_info_label.pack(pady=(0, 10))

        # Progress bar frame
        pb_frame = tk.Frame(self.kernel_tab, bg=self._get_axis_bg())
        pb_frame.pack(pady=(0, 20), padx=30, fill='x')
        self.progress = ttk.Progressbar(pb_frame, orient="horizontal",
                                         mode="determinate",
                                         length=650,
                                         style="TProgressbar")
        self.progress.pack(fill='x')

        # Matplotlib figure and canvas
        self.fig, self.ax = plt.subplots(figsize=(7, 3), dpi=100)
        self.fig.patch.set_facecolor(self._get_bg_color())
        self.ax.set_facecolor(self._get_axis_bg())
        self.ax.tick_params(axis='x', colors=self._get_fg_color())
        self.ax.tick_params(axis='y', colors=self._get_fg_color())
        self.ax.spines['bottom'].set_color(self._get_fg_color())
        self.ax.spines['left'].set_color(self._get_fg_color())
        self.ax.grid(color='#444444', linestyle='--', linewidth=0.5)
        self.ax.set_ylim(0, 100)
        self.ax.set_title("Kernel Memory Usage (Last 30 seconds)", color=self._get_teal_color(), fontsize=17, pad=15)
        self.line, = self.ax.plot([], [], color=self._get_coral_color(), linewidth=3, alpha=0.9)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.kernel_tab)
        self.canvas.get_tk_widget().pack(pady=(0, 15), padx=15, fill='x')
        self._configure_plot_colors()

    def create_process_memory_tab(self):
        self.process_tree = ttk.Treeview(self.process_tab, columns=('PID', 'Name', 'Memory'), show='headings')
        self.process_tree.heading('PID', text='PID')
        self.process_tree.heading('Name', text='Name')
        self.process_tree.heading('Memory', text='Memory (KB)')

        self.process_tree.column('PID', width=80, anchor='center')
        self.process_tree.column('Name', width=250, anchor='w')
        self.process_tree.column('Memory', width=120, anchor='e')

        self.process_tree.pack(padx=15, pady=15, fill='both', expand=True)

        # Scrollbar for the treeview
        scrollbar = ttk.Scrollbar(self.process_tab, orient=tk.VERTICAL, command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.process_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _get_bg_color(self):
        return "#121212" if self.dark_mode else "#f0f0f0"

    def _get_axis_bg(self):
        return "#1E1E1E" if self.dark_mode else "#ffffff"

    def _get_fg_color(self):
        return "#E0E0E0" if self.dark_mode else "#121212"

    def _get_teal_color(self):
        return "#00BFA6"

    def _get_coral_color(self):
        return "#FF6F61"

    def configure_styles(self):
        bg = self._get_bg_color()
        fg = self._get_fg_color()
        teal = self._get_teal_color()
        coral = self._get_coral_color()
        axis_bg = self._get_axis_bg()

        self.configure(bg=bg)

        self.style.configure("TNotebook", background=bg, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=axis_bg, foreground=fg, font=self.base_font, padding=(8, 4))
        self.style.map("TNotebook.Tab",
                       background=[("selected", teal)],
                       foreground=[("selected", bg)])

        self.style.configure("TLabel", background=bg, foreground=fg, font=self.base_font)
        self.style.configure("Title.TLabel", background=bg, foreground=teal, font=self.title_font)
        self.style.configure("TProgressbar", troughcolor=axis_bg, bordercolor=axis_bg, background=coral, thickness=28)
        self.style.configure("TButton", font=self.button_font, padding=10)
        self.style.map("TButton",
                       background=[('active', coral), ('!active', teal)],
                       foreground=[('active', bg), ('!active', "#F0F0F0")])
        self.style.configure("TLabelframe", background=bg, foreground=fg, font=self.label_font, borderwidth=2)
        self.style.configure("TLabelframe.Label", background=bg, foreground=fg, font=self.label_font)

        self.style.configure("Treeview", background=axis_bg, foreground=fg, font=self.process_font)
        self.style.configure("Treeview.Heading", background=axis_bg, foreground=fg, font=self.label_font)
        self.style.map("Treeview.Heading",
                       background=[('active', teal)],
                       foreground=[('active', bg)])

        self.style.configure("TScrollbar", background=bg, troughcolor=axis_bg)

    def _configure_plot_colors(self):
        coral = self._get_coral_color()
        teal = self._get_teal_color()
        bg = self._get_bg_color()
        axis_bg = self._get_axis_bg()
        fg = self._get_fg_color()

        self.fig.patch.set_facecolor(bg)
        self.ax.set_facecolor(axis_bg)
        self.ax.tick_params(axis='x', colors=fg)
        self.ax.tick_params(axis='y', colors=fg)
        self.ax.spines['bottom'].set_color(fg)
        self.ax.spines['left'].set_color(fg)
        self.ax.grid(color='#444444', linestyle='--', linewidth=0.5)
        self.ax.set_title("Kernel Memory Usage (Last 30 seconds)", color=teal, fontsize=17, pad=15)
        self.line.set_color(coral)
        self.canvas.draw_idle()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.pause_button.config(text="Resume Updates" if self.is_paused else "Pause Updates")

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.configure_styles()
        self._configure_plot_colors()

        # Configure Treeview style for background and foreground
        style = ttk.Style(self)
        style.configure("Treeview",
                        background=self._get_axis_bg(),
                        foreground=self._get_fg_color())
        style.configure("Treeview.Heading",
                        background=self._get_axis_bg(),
                        foreground=self._get_fg_color())
        style.map("Treeview.Heading",
                  background=[('active', self._get_teal_color())],
                  foreground=[('active', self._get_bg_color())])

    def save_graph(self):
        try:
            filename = filedialog.asksaveasfilename(defaultextension=".png",
                                                       filetypes=[("PNG files", "*.png"),
                                                                  ("All files", "*.*")])
            if filename:
                self.fig.savefig(filename)
                messagebox.showinfo("Saved", f"Graph saved to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save graph:\n{e}")

    def update_ui(self):
        if not self.is_paused:
            used, total, percent = read_kernel_memory()
            self.kernel_label_var.set(f"Used: {used:,} KB / Total: {total:,} KB ({percent:.2f}%)")
            self.progress['value'] = percent

            self.memory_log.append(percent)
            if len(self.memory_log) > 30:
                self.memory_log.pop(0)

            self.line.set_data(range(len(self.memory_log)), self.memory_log)
            self.ax.set_xlim(0, 30)
            self.canvas.draw_idle()

            if percent >= self.threshold and not self.alert_shown:
                self.alert_shown = True
                messagebox.showwarning("Threshold Alert",
                                       f"Kernel memory usage crossed {self.threshold}%!\nCurrent: {percent:.2f}%")
            elif percent < self.threshold:
                self.alert_shown = False

            process_memory = get_process_memory_info()
            # Clear previous items in the treeview
            for item in self.process_tree.get_children():
                self.process_tree.delete(item)
            # Insert new process memory info
            for proc in process_memory[:20]:  # Show top 20 processes
                self.process_tree.insert('', tk.END, values=(proc['pid'], proc['name'], f"{proc['memory_kb']:,}"))

        self.after(1000, self.update_ui)

if __name__ == "__main__":
    app = MemoryTrackerApp()
    app.mainloop()
