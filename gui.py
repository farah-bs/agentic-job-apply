import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
import asyncio
import threading
from pipeline import run_pipeline


class JobApplicationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Agentic Job Application Pipeline")
        self.root.geometry("800x700")
        self.root.configure(bg="#f0f0f0")
        
        # Title
        title_label = tk.Label(
            root, 
            text="Job Application Pipeline", 
            font=("Arial", 16, "bold"),
            bg="#f0f0f0"
        )
        title_label.pack(pady=10)
        
        # Main frame
        main_frame = tk.Frame(root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Job URL/File input
        tk.Label(main_frame, text="Job Posting URL or File:", font=("Arial", 10), bg="#f0f0f0").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.job_url_var = tk.StringVar()
        job_frame = tk.Frame(main_frame, bg="#f0f0f0")
        job_frame.grid(row=0, column=1, sticky="ew", pady=5)
        tk.Entry(job_frame, textvariable=self.job_url_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(job_frame, text="Browse", command=self.browse_job_file).pack(side=tk.LEFT, padx=5)
        
        # Resume file input
        tk.Label(main_frame, text="Resume File (.tex):", font=("Arial", 10), bg="#f0f0f0").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.resume_var = tk.StringVar(value="media/sample_resume.tex")
        resume_frame = tk.Frame(main_frame, bg="#f0f0f0")
        resume_frame.grid(row=1, column=1, sticky="ew", pady=5)
        tk.Entry(resume_frame, textvariable=self.resume_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(resume_frame, text="Browse", command=self.browse_resume_file).pack(side=tk.LEFT, padx=5)
        
        # Output directory input
        tk.Label(main_frame, text="Output Directory:", font=("Arial", 10), bg="#f0f0f0").grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.output_dir_var = tk.StringVar(value="media/output")
        output_frame = tk.Frame(main_frame, bg="#f0f0f0")
        output_frame.grid(row=2, column=1, sticky="ew", pady=5)
        tk.Entry(output_frame, textvariable=self.output_dir_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(output_frame, text="Browse", command=self.browse_output_dir).pack(side=tk.LEFT, padx=5)
        
        # Checkboxes
        checkbox_frame = tk.Frame(main_frame, bg="#f0f0f0")
        checkbox_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=10)
        
        self.cover_letter_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            checkbox_frame, 
            text="Generate Cover Letter", 
            variable=self.cover_letter_var,
            bg="#f0f0f0",
            font=("Arial", 10)
        ).pack(anchor="w")
        
        self.verbose_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            checkbox_frame, 
            text="Verbose Output", 
            variable=self.verbose_var,
            bg="#f0f0f0",
            font=("Arial", 10)
        ).pack(anchor="w")
        
        # Buttons frame
        button_frame = tk.Frame(main_frame, bg="#f0f0f0")
        button_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=15)
        
        self.run_button = tk.Button(
            button_frame, 
            text="Run Pipeline", 
            command=self.run_pipeline,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=10,
            cursor="hand2"
        )
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame, 
            text="Clear Log", 
            command=self.clear_log,
            bg="#2196F3",
            fg="white",
            font=("Arial", 11),
            padx=20,
            pady=10,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)
        
        # Output log
        tk.Label(main_frame, text="Output Log:", font=("Arial", 10, "bold"), bg="#f0f0f0").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(15, 5)
        )
        
        self.log_text = scrolledtext.ScrolledText(
            main_frame, 
            height=15, 
            width=80,
            bg="white",
            fg="#333",
            font=("Courier", 9)
        )
        self.log_text.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=5)
        
        # Configure grid weight for resizing
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            root, 
            textvariable=self.status_var, 
            bd=1, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            bg="#e0e0e0",
            font=("Arial", 9)
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def browse_job_file(self):
        file = filedialog.askopenfilename(
            title="Select Job Posting File",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if file:
            self.job_url_var.set(file)
    
    def browse_resume_file(self):
        file = filedialog.askopenfilename(
            title="Select Resume File",
            filetypes=[("LaTeX files", "*.tex"), ("All files", "*.*")]
        )
        if file:
            self.resume_var.set(file)
    
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_var.set(directory)
    
    def clear_log(self):
        self.log_text.delete("1.0", tk.END)
        self.log("Log cleared.\n")
    
    def log(self, message):
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.root.update()
    
    def run_pipeline(self):
        # Validate inputs
        job_url = self.job_url_var.get().strip()
        resume = self.resume_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        
        if not job_url:
            messagebox.showerror("Error", "Please enter a job posting URL or file path")
            return
        
        if not resume:
            messagebox.showerror("Error", "Please select a resume file")
            return
        
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory")
            return
        
        # Check if files exist
        if not Path(resume).exists():
            messagebox.showerror("Error", f"Resume file not found: {resume}")
            return
        
        # Disable run button during execution
        self.run_button.config(state=tk.DISABLED)
        self.status_var.set("Running pipeline...")
        
        # Clear log
        self.log_text.delete("1.0", tk.END)
        
        # Run pipeline in a separate thread
        thread = threading.Thread(
            target=self._run_pipeline_thread,
            args=(job_url, resume, output_dir),
            daemon=True
        )
        thread.start()
    
    def _run_pipeline_thread(self, job_url, resume, output_dir):
        try:
            self.log("=" * 60 + "\n")
            self.log(f"Starting Job Application Pipeline\n")
            self.log(f"Job URL    : {job_url}\n")
            self.log(f"Resume     : {resume}\n")
            self.log(f"Output Dir : {output_dir}\n")
            self.log(f"Cover Letter: {'Yes' if self.cover_letter_var.get() else 'No'}\n")
            self.log("=" * 60 + "\n\n")
            
            # Capture print statements
            import io
            import sys
            
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            
            try:
                # Run the pipeline
                asyncio.run(run_pipeline(
                    job_url=job_url,
                    resume_path=resume,
                    output_dir=output_dir,
                    generate_cover_letter=self.cover_letter_var.get(),
                    verbose=self.verbose_var.get(),
                ))
                
                output = sys.stdout.getvalue()
                self.log(output)
                
            finally:
                sys.stdout = old_stdout
            
            self.log("\n" + "=" * 60 + "\n")
            self.log("Pipeline completed successfully!\n")
            self.status_var.set("Pipeline completed successfully")
            messagebox.showinfo("Success", "Pipeline completed successfully!")
            
        except SystemExit as e:
            if e.code != 0:
                self.log(f"\nPipeline failed with exit code {e.code}\n")
                self.status_var.set("Pipeline failed")
            else:
                self.log("\nPipeline completed!\n")
                self.status_var.set("Pipeline completed")
        except Exception as e:
            self.log(f"\nError: {str(e)}\n")
            self.status_var.set("Pipeline failed with error")
            messagebox.showerror("Error", f"Pipeline failed:\n{str(e)}")
        
        finally:
            self.run_button.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    gui = JobApplicationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
