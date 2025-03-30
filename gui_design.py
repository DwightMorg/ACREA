# gui_design.py

import tkinter as tk
from tkinter import scrolledtext, font

class AcreaGUI:
    """
    Defines the visual structure and widgets for the Acrea Tkinter GUI.
    Layout and basic styling are handled here.
    Interaction logic is delegated via callbacks.
    """
    def __init__(self, master: tk.Tk, send_callback: callable):
        """
        Initializes the GUI layout.

        Args:
            master: The root Tkinter window.
            send_callback: A function to call when the user clicks 'Send'.
                           This function should accept the user's input string
                           as its argument.
        """
        self.master = master
        self.send_callback = send_callback
        master.title("Acrea - AI Architecture Assistant")
        master.geometry("800x600") # Default size

        # Configure styles (optional, can be expanded)
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=11)
        text_font = font.Font(family="Consolas", size=10) # Monospaced for output maybe

        # --- Main Frame ---
        main_frame = tk.Frame(master, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Output Area ---
        output_label = tk.Label(main_frame, text="Conversation:", anchor="w")
        output_label.pack(fill=tk.X)

        self.output_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            state="disabled", # Start as read-only
            height=20,
            font=text_font,
            bg="#f0f0f0", # Lighter background
            relief=tk.SOLID,
            bd=1
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # --- Input Area ---
        input_label = tk.Label(main_frame, text="Your Message:", anchor="w")
        input_label.pack(fill=tk.X)

        self.input_text = tk.Text(
            main_frame,
            height=5,
            font=default_font,
            relief=tk.SOLID,
            bd=1
        )
        self.input_text.pack(fill=tk.X, pady=(0, 10))
        # Bind Enter key to send message as well
        self.input_text.bind("<Return>", self._on_send)
        self.input_text.bind("<Shift-Return>", self._insert_newline) # Allow Shift+Enter for newlines

        # --- Send Button ---
        self.send_button = tk.Button(
            main_frame,
            text="Send",
            command=self._on_send,
            width=10,
            relief=tk.RAISED,
            bd=2
        )
        self.send_button.pack(anchor="e")

        # Set focus to input box on start
        self.input_text.focus_set()


    def _on_send(self, event=None):
        """Internal handler for when the Send button or Enter key is pressed."""
        user_input = self.input_text.get("1.0", tk.END).strip()
        if user_input:
            # Call the callback function provided during initialization
            self.send_callback(user_input)
            # Don't clear input here, let the callback decide if needed after processing
        return "break" # Prevents default Enter key behavior (like adding a newline)

    def _insert_newline(self, event=None):
         """Allows Shift+Enter to insert a newline in the input."""
         self.input_text.insert(tk.INSERT, '\n')
         return "break" # Stop the event from propagating further


    def display_message(self, role: str, message: str):
        """
        Appends a message to the output text area.

        Args:
            role: Typically "You" or "Acrea".
            message: The text content to display.
        """
        self.output_text.config(state="normal") # Enable writing
        if self.output_text.index('end-1c') != "1.0": # Add newline if not empty
             self.output_text.insert(tk.END, "\n\n")
        self.output_text.insert(tk.END, f"{role}: {message}")
        self.output_text.see(tk.END) # Scroll to the end
        self.output_text.config(state="disabled") # Disable writing again

    def set_thinking_status(self, thinking: bool):
         """Provides visual feedback while Acrea is processing."""
         if thinking:
             self.display_message("Acrea", "...thinking...")
             self.send_button.config(state="disabled")
             self.input_text.config(state="disabled")
         else:
             # Remove "thinking..." (simple approach: clear and redisplay - better ways exist)
             # Or just rely on the actual response overwriting/appending
             self.send_button.config(state="normal")
             self.input_text.config(state="normal")
             self.input_text.focus_set() # Return focus

    def clear_input(self):
        """Clears the user input text area."""
        self.input_text.delete("1.0", tk.END)