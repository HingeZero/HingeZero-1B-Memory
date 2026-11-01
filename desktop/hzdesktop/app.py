"""User-facing offline desktop interface. Only explicitly selected files are accessed."""
from __future__ import annotations

import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from hzdesktop import __version__
from hzdesktop.vault import Vault
from hzdesktop.retrieval import search, RetainedMemorySession
from hzdesktop.importers import extract, chunks, SUPPORTED
from hzdesktop import ollama
from hzdesktop.api import LocalAPI

VAULT_PATH = Path.home() / "HingeZeroMemory" / "vault.sqlite3"


class Consent(tk.Toplevel):
    def __init__(self, root):
        super().__init__(root)
        self.title("Create encrypted HingeZero Memory vault")
        self.resizable(False, False)
        self.result = None
        self.transient(root)
        self.grab_set()
        panel = ttk.Frame(self, padding=20)
        panel.pack(fill="both")
        ttk.Label(panel, text="Your memory, under your control", font=("Arial", 15, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(panel, text=("• Files are imported ONLY when you select them.\n"
                      "• All saved notes are encrypted with your passphrase.\n"
                      "• No cloud service or telemetry is used.\n"
                      "• Optional Ollama and API access start DISABLED.\n"
                      "• Losing your password means losing access to the vault.\n"
                      "• Free for permitted noncommercial use; commercial use requires a paid licence.\n"
                      "• Licence terms: polyformproject.org/licenses/noncommercial/1.0.0\n"
                      "• This is not a medical or safety system."),
                  justify="left").pack(anchor="w")
        self.ok = tk.BooleanVar(value=False)
        ttk.Checkbutton(panel, text="I agree to the licence and consent to these storage permissions",
                        variable=self.ok).pack(anchor="w", pady=(12, 6))
        ttk.Label(panel, text="Passphrase (at least 12 characters)").pack(anchor="w")
        self.password = ttk.Entry(panel, show="*", width=47)
        self.password.pack(anchor="w")
        ttk.Label(panel, text="Confirm passphrase").pack(anchor="w", pady=(8, 0))
        self.confirm = ttk.Entry(panel, show="*", width=47)
        self.confirm.pack(anchor="w")
        ttk.Button(panel, text="Create encrypted vault", command=self.save).pack(anchor="e", pady=(15, 0))
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.password.focus_set()
        self.wait_window()

    def save(self):
        if not self.ok.get():
            messagebox.showwarning("Consent required", "Confirm storage permissions first", parent=self)
        elif self.password.get() != self.confirm.get():
            messagebox.showerror("Mismatch", "Passphrases do not match", parent=self)
        elif len(self.password.get()) < 12:
            messagebox.showerror("Too short", "Use at least 12 characters", parent=self)
        else:
            self.result = self.password.get()
            self.destroy()


class MemoryApp:
    def __init__(self, root: tk.Tk, vault: Vault):
        self.root, self.vault = root, vault
        self.api = None
        self.events = queue.Queue()
        self.selected = []
        self.retained_session = RetainedMemorySession()
        self.use_ollama = tk.BooleanVar(value=False)
        self.embed_model = tk.StringVar(value="embeddinggemma")
        self.chat_model = tk.StringVar(value="llama3.2:3b")
        self.status = tk.StringVar(value="Offline vault unlocked · no AI connection enabled")
        self.query = tk.StringVar()
        self.root.title(f"HingeZero Memory · v{__version__}")
        self.root.geometry("920x690")
        self.root.minsize(720, 520)
        self.build()
        self.refresh()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.process_events)

    def build(self):
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="HingeZero Memory", font=("Arial", 18, "bold")).pack(side="left")
        ttk.Label(header, text="Encrypted • Offline-first", foreground="#376d57").pack(side="right")
        tabs = ttk.Notebook(self.root)
        tabs.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        memory_tab = ttk.Frame(tabs, padding=8)
        chat_tab = ttk.Frame(tabs, padding=8)
        settings_tab = ttk.Frame(tabs, padding=8)
        tabs.add(memory_tab, text="Memories & Search")
        tabs.add(chat_tab, text="Ask local AI")
        tabs.add(settings_tab, text="Permissions & Integration")
        toolbar = ttk.Frame(memory_tab)
        toolbar.pack(fill="x", pady=3)
        ttk.Button(toolbar, text="Add memory", command=self.add_note).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Import selected file", command=self.import_file).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Delete selected", command=self.delete).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Encrypted backup", command=self.backup).pack(side="right", padx=3)
        qs = ttk.Frame(memory_tab)
        qs.pack(fill="x", pady=(9, 4))
        ttk.Label(qs, text="Recall:").pack(side="left")
        entry = ttk.Entry(qs, textvariable=self.query)
        entry.pack(side="left", fill="x", expand=True, padx=6)
        entry.bind("<Return>", lambda *_: self.run_search())
        ttk.Button(qs, text="Search", command=self.run_search).pack(side="left")
        ttk.Button(qs, text="Show all", command=self.refresh).pack(side="left", padx=4)
        list_frame = ttk.Frame(memory_tab)
        list_frame.pack(fill="both", expand=True)
        self.results = tk.Listbox(list_frame, height=11, exportselection=False)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.results.yview)
        self.results.configure(yscrollcommand=scrollbar.set)
        self.results.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.results.bind("<<ListboxSelect>>", self.show_selected)
        ttk.Label(memory_tab, text="Stored evidence (read-only)").pack(anchor="w", pady=(6, 2))
        self.preview = tk.Text(memory_tab, height=10, wrap="word", state="disabled")
        self.preview.pack(fill="both", expand=True)
        ttk.Label(chat_tab, text="Ask an optional, locally running Ollama model using evidence from your vault.").pack(anchor="w")
        self.chat_input = tk.Text(chat_tab, height=4, wrap="word")
        self.chat_input.pack(fill="x", pady=(9, 5))
        ttk.Button(chat_tab, text="Ask using memory", command=self.ask).pack(anchor="e")
        self.chat_output = tk.Text(chat_tab, wrap="word", state="disabled")
        self.chat_output.pack(fill="both", expand=True, pady=(8, 0))
        ttk.Label(settings_tab, text="Permissions", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(settings_tab, text="File access: only files chosen through the import dialog. No administrator access requested.", wraplength=660).pack(anchor="w")
        ttk.Checkbutton(settings_tab,
                        text="Allow sharing selected memories and questions with Ollama on THIS device (127.0.0.1 only)",
                        variable=self.use_ollama).pack(anchor="w", pady=14)
        models = ttk.Frame(settings_tab)
        models.pack(anchor="w", fill="x")
        ttk.Label(models, text="Local embedding model:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(models, textvariable=self.embed_model, width=27).grid(row=0, column=1)
        ttk.Label(models, text="Local chat model:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(models, textvariable=self.chat_model, width=27).grid(row=1, column=1)
        ttk.Label(settings_tab, text=("Embeddings improve meaning-based search. Existing notes aren't automatically re-embedded "
                 "after switching models. Ollama must already be installed and models downloaded. "
                 "No cloud AI or internet endpoints are supported."), wraplength=680).pack(anchor="w", pady=12)
        ttk.Separator(settings_tab).pack(fill="x", pady=14)
        ttk.Label(settings_tab, text="Local app integration API", font=("Arial", 14, "bold")).pack(anchor="w")
        ttk.Label(settings_tab, text=("Optional token-protected HTTP API bound to 127.0.0.1. Enabling it allows "
                    "other processes on your computer to read or add vault memories if they know its token. "
                    "Never share the token. Stop it when not needed."), wraplength=680).pack(anchor="w", pady=6)
        self.api_btn = ttk.Button(settings_tab, text="Start local API (consent required)", command=self.toggle_api)
        self.api_btn.pack(anchor="w", pady=8)
        self.api_info = tk.Text(settings_tab, height=5, wrap="word", state="disabled")
        self.api_info.pack(fill="x")
        ttk.Label(self.root, textvariable=self.status, relief="sunken", anchor="w", padding=5).pack(fill="x", padx=10, pady=(0, 6))

    def set_text(self, widget, content):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def refresh(self):
        self.selected = self.vault.list()
        self.results.delete(0, "end")
        for rec in self.selected:
            self.results.insert("end", f"{rec['title']}   · {rec['source']}")
        self.status.set(f"{len(self.selected)} encrypted memory chunks · offline")
        self.set_text(self.preview, "Select a memory to view its stored evidence.")

    def show_selected(self, *_):
        if self.results.curselection():
            record = self.selected[self.results.curselection()[0]]
            self.set_text(self.preview, f"SOURCE: {record['source']}\nTITLE: {record['title']}\n\n{record['content']}")

    def run_search(self):
        question = self.query.get().strip()
        if not question:
            self.refresh()
            return
        if self.use_ollama.get():
            try:
                model = ollama.valid_model(self.embed_model.get())
                self.status.set("Computing local query embedding…")
                self.work(lambda: ollama.embed(model, question),
                          lambda vec: self.display_results(search(self.vault.list(), question,
                                          query_embedding=vec, embedding_model=model,
                                          session=self.retained_session)))
                return
            except Exception as e:
                messagebox.showerror("Model name", str(e))
                return
        self.display_results(search(self.vault.list(), question, session=self.retained_session))

    def display_results(self, found):
        self.selected = [item["record"] for item in found]
        self.results.delete(0, "end")
        for item in found:
            r = item["record"]
            self.results.insert("end", f"{item['score']:.3f}  {r['title']}   · {r['source']}")
        self.status.set(f"{len(found)} matching memories · results are evidence, not verified truth")
        if found:
            self.results.selection_set(0)
            self.show_selected()
        else:
            self.set_text(self.preview, "No matching memories found. Try different wording or enable a local embedding model.")

    def add_note(self):
        title = simpledialog.askstring("New memory", "Title:", parent=self.root)
        if title is None:
            return
        content = simpledialog.askstring("New memory", "Memory content (up to 10,000 characters):", parent=self.root)
        if not content:
            return
        self.save_document(title, [content], "manual")

    def import_file(self):
        path = filedialog.askopenfilename(parent=self.root, title="Choose a file to import",
                  filetypes=[("Supported", "*.txt *.md *.csv *.json *.pdf *.docx"), ("All files", "*.*")])
        if not path:
            return
        try:
            text = extract(path)
            segments = chunks(text)
            if self.vault.count() + len(segments) > 20_000:
                raise ValueError("Insufficient vault record capacity")
            if not messagebox.askyesno("Confirm file import",
                     f"Import {len(segments)} encrypted memory chunks from:\n{Path(path).name}?\n\n"
                     "This reads only the selected file.", parent=self.root):
                return
            self.save_document(Path(path).name, segments, Path(path).name)
        except Exception as e:
            messagebox.showerror("Import refused", str(e)[:700], parent=self.root)

    def save_document(self, title, segments, source):
        self.retained_session.reset()
        if self.use_ollama.get():
            try:
                model = ollama.valid_model(self.embed_model.get())
            except Exception as e:
                messagebox.showerror("Invalid model", str(e))
                return
            if not messagebox.askyesno("Local Ollama sharing",
                f"Allow sending {len(segments)} selected memory chunks to the LOCAL Ollama embedding process?",
                parent=self.root):
                return
            def prepare():
                return [(segment, ollama.embed(model, segment)) for segment in segments]
            def commit(prepared):
                try:
                    for i, (segment, vector) in enumerate(prepared):
                        self.vault.add(f"{title} · part {i + 1}" if len(prepared) > 1 else title,
                                       segment, source, vector, model)
                    self.refresh()
                except Exception as e:
                    messagebox.showerror("Save failed", str(e)[:700])
            self.work(prepare, commit)
        else:
            try:
                for i, segment in enumerate(segments):
                    self.vault.add(f"{title} · part {i + 1}" if len(segments) > 1 else title,
                                   segment, source)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Save failed", str(e)[:700])

    def delete(self):
        if not self.results.curselection():
            return
        note = self.selected[self.results.curselection()[0]]
        if messagebox.askyesno("Delete permanently", f"Delete memory '{note['title']}'?", parent=self.root):
            with self.api.lock if self.api else _NoopLock():
                self.vault.delete(note["id"])
            self.retained_session.reset()
            self.refresh()

    def backup(self):
        target = filedialog.asksaveasfilename(parent=self.root, title="Save encrypted vault backup",
                      initialfile="hingezero-vault-backup.sqlite3", defaultextension=".sqlite3")
        if target:
            try:
                with self.api.lock if self.api else _NoopLock():
                    self.vault.backup_encrypted(target)
                messagebox.showinfo("Backup saved", "Backup is encrypted. Keep your passphrase safe.")
            except Exception as e:
                messagebox.showerror("Backup failed", str(e))

    def ask(self):
        question = self.chat_input.get("1.0", "end").strip()
        if not question:
            return
        if not self.use_ollama.get():
            messagebox.showwarning("Opt-in required", "Enable local Ollama in Permissions & Integration first.")
            return
        try:
            chat_model = ollama.valid_model(self.chat_model.get())
            embed_model = ollama.valid_model(self.embed_model.get())
        except Exception as e:
            messagebox.showerror("Invalid local model", str(e))
            return
        if not messagebox.askyesno("Local AI consent", "Share this question and up to five retrieved notes with LOCAL Ollama?", parent=self.root):
            return
        def prepare():
            try:
                vec = ollama.embed(embed_model, question)
                relevant = search(self.vault.list(), question, query_embedding=vec, embedding_model=embed_model)
            except Exception:
                relevant = search(self.vault.list(), question)
            response = ollama.answer(chat_model, question, relevant)
            return response, relevant
        def done(result):
            reply, sources = result
            self.set_text(self.chat_output, reply + "\n\n--- Retrieved local evidence ---\n" +
                          "\n".join(f"[{i}] {v['record']['title']} ({v['record']['source']})" for i, v in enumerate(sources, 1)) +
                          "\n\nAI may still make mistakes. Check source notes for important facts.")
        self.work(prepare, done)

    def toggle_api(self):
        if self.api:
            self.api.stop()
            self.api = None
            self.api_btn.configure(text="Start local API (consent required)")
            self.set_text(self.api_info, "Stopped. Access token revoked.")
            return
        if not messagebox.askyesno("Enable local memory API",
              "Other programs on this computer can retrieve or add vault memories IF they know the session token. "
              "Use only with programs you trust. Start the API?", parent=self.root):
            return
        self.api = LocalAPI(self.vault)
        self.api_btn.configure(text="Stop local API")
        self.set_text(self.api_info, f"API: http://127.0.0.1:{self.api.port}\n"
              f"Session token (keep private): {self.api.token}\nPOST /v1/search or POST /v1/remember. Bearer token required.\n"
              "Close the app to revoke access.")

    def work(self, operation, finish):
        self.status.set("Working locally…")
        def worker():
            try:
                output = operation()
                self.events.put((True, output, finish))
            except Exception as e:
                self.events.put((False, e, finish))
        threading.Thread(target=worker, daemon=True).start()

    def process_events(self):
        try:
            while True:
                success, value, callback = self.events.get_nowait()
                if success:
                    callback(value)
                else:
                    self.status.set("Local action failed")
                    messagebox.showerror("Local operation failed", str(value)[:700], parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self.process_events)

    def close(self):
        if self.api:
            self.api.stop()
        self.vault.close()
        self.root.destroy()


class _NoopLock:
    def __enter__(self): pass
    def __exit__(self, *_): pass


def main():
    root = tk.Tk()
    root.withdraw()
    try:
        if VAULT_PATH.exists():
            password = simpledialog.askstring("Unlock HingeZero Memory",
                     "Enter your vault passphrase:", show="*", parent=root)
            if password is None:
                root.destroy()
                return
            vault = Vault(VAULT_PATH, password)
        else:
            screen = Consent(root)
            if screen.result is None:
                root.destroy()
                return
            vault = Vault(VAULT_PATH, screen.result, create=True)
    except Exception as e:
        messagebox.showerror("Vault unavailable", str(e)[:700], parent=root)
        root.destroy()
        return
    root.deiconify()
    MemoryApp(root, vault)
    root.mainloop()
