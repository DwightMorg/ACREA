# flet_gui_design_v3.py

import flet as ft
import logging

# --- Color Palette (Same as before) ---
COLOR_BACKGROUND = "#1e1e1e"
COLOR_SURFACE = "#2d2d2d"
COLOR_PRIMARY = ft.colors.BLUE_400
COLOR_ON_PRIMARY = ft.colors.BLACK
COLOR_SECONDARY = ft.colors.TEAL_ACCENT_400
COLOR_ON_SURFACE = ft.colors.WHITE
COLOR_ON_SURFACE_VARIANT = ft.colors.with_opacity(0.7, ft.colors.WHITE)
COLOR_BORDER = ft.colors.with_opacity(0.2, ft.colors.WHITE)
COLOR_HOVER_BG = ft.colors.with_opacity(0.08, ft.colors.WHITE)

# --- Reusable Components (Enhanced for Wrapping & Copy) ---

def create_message_card_v3(role: str, text_content: str, timestamp: str = None, on_copy_click: callable = None): # Added on_copy_click
    """Creates a visually distinct card for each message with V3 styling, copy button, and better wrapping."""
    is_user = role.lower() == "you"

    # --- Content Control (Markdown/Text) ---
    content_control: ft.Control
    if not is_user:
        try:
            content_control = ft.Markdown(
                value=str(text_content), selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                code_theme="monokai",
                # Markdown should wrap automatically if parent container has width constraint
            )
        except Exception as md_error:
             logging.error(f"Markdown rendering failed: {md_error}. Falling back to Text.", exc_info=True)
             content_control = ft.Text(str(text_content), selectable=True, color=COLOR_ON_SURFACE)
    else:
        # User text should also wrap
        content_control = ft.Text(str(text_content), selectable=True, color=COLOR_ON_SURFACE)

    # --- Copy Button ---
    copy_button = ft.IconButton(
        icon=ft.icons.COPY_ALL_OUTLINED,
        icon_size=14,
        tooltip="Copy message text",
        icon_color=COLOR_ON_SURFACE_VARIANT,
        # The actual on_click handler will be attached in the runner
        # Store the text content here temporarily or pass it via data
        data=str(text_content), # Store text in data for the handler
        # Add hover effect if desired
        style=ft.ButtonStyle(
             shape=ft.CircleBorder(),
             padding=5,
             overlay_color=ft.colors.with_opacity(0.2, COLOR_ON_SURFACE_VARIANT)
        )
    )
    if on_copy_click: # Attach handler if provided
        copy_button.on_click = lambda e: on_copy_click(e.control.data)


    # --- Card Container ---
    message_container = ft.Container(
        content=ft.Column(
             [
                # Row for Role Icon, Name, and Copy Button
                ft.Row(
                    [
                        ft.Icon(ft.icons.PERSON_OUTLINE if is_user else ft.icons.COMPUTER_OUTLINED,
                                size=16, color=COLOR_ON_SURFACE_VARIANT),
                        ft.Text(role, weight=ft.FontWeight.BOLD, size=11, color=COLOR_ON_SURFACE),
                        ft.Container(expand=True), # Pushes copy button to the right
                        copy_button # Add copy button here
                    ],
                    spacing=5, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # Content Area - Wrap should happen here if container is constrained
                ft.Container(content=content_control, padding=ft.padding.only(top=5)),
            ],
            spacing=3, tight=True,
            # CRITICAL FOR WRAPPING: Ensure Column tries to fit content width-wise
            # Let the parent container handle the width constraint
            expand=True, # Allow column to expand vertically, but respect horizontal constraints
        ),
        bgcolor=COLOR_SURFACE,
        padding=ft.padding.symmetric(vertical=12, horizontal=16),
        border_radius=ft.border_radius.all(10),
        margin=ft.margin.only(bottom=10, left=10, right=60 if is_user else 10, top=5), # Adjust margins for alignment look
        shadow=ft.BoxShadow(
            spread_radius=1, blur_radius=3,
            color=ft.colors.with_opacity(0.15, ft.colors.BLACK),
            offset=ft.Offset(1, 2),
        ),
        # REMOVED ALIGNMENT FROM HERE - will be handled by parent Column/Row
        # Width is implicitly constrained by the parent Column (output_column)
        # which expands to fill the page width minus padding.
    )

    # Animated Container (same as before)
    animated_card = ft.Container(
        content=message_container,
        opacity=0,
        animate_opacity=ft.animation.Animation(600, ft.AnimationCurve.EASE_IN_OUT),
        # Let the parent Column handle alignment
        alignment=ft.alignment.center_right if is_user else ft.alignment.center_left # Align the animated container itself
    )

    return animated_card

# --- Main UI Class V3 ---
class AcreaFletUI_V3:
    """ V3 UI Class """
    def __init__(self):
        self.output_column = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
            spacing=0, # Let card margins handle spacing
            controls=[],
            auto_scroll=False,
            # Add horizontal alignment to ensure children don't stretch full width unless needed
            # Let the children's alignment handle left/right placement
            horizontal_alignment=ft.CrossAxisAlignment.START # Default alignment for children
        )

        # --- Input Area (mostly same) ---
        self.input_field = ft.TextField(
             # ... same properties ...
            hint_text="Ask Acrea...", multiline=True, shift_enter=True, min_lines=1, max_lines=5, expand=True,
            border=ft.InputBorder.OUTLINE, border_radius=ft.border_radius.all(20),
            border_color=COLOR_BORDER, focused_border_color=COLOR_PRIMARY,
            content_padding=ft.padding.symmetric(vertical=12, horizontal=15),
            text_size=13, bgcolor=ft.colors.with_opacity(0.03, ft.colors.WHITE),
            hint_style=ft.TextStyle(color=COLOR_ON_SURFACE_VARIANT)
        )
        self.send_button = ft.IconButton( # ... same properties ...
             icon=ft.icons.SEND_ROUNDED, tooltip="Send Message", icon_color=COLOR_PRIMARY,
             icon_size=22, animate_scale=ft.animation.Animation(150, ft.AnimationCurve.EASE_OUT_BACK),
             scale=ft.transform.Scale(1.0), data="send_button"
        )
        self.progress_indicator = ft.Container( # ... same properties ...
             content=ft.ProgressRing(width=20, height=20, stroke_width=2.5, color=COLOR_PRIMARY),
             visible=False, opacity=0, animate_opacity=ft.animation.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
             padding=ft.padding.only(right=8)
         )
        self.input_row = ft.Container( # ... same properties ...
             content=ft.Row(
                [ self.input_field, self.progress_indicator, self.send_button ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
            ),
            padding=ft.padding.all(10),
            border=ft.border.only(top=ft.border.BorderSide(1, COLOR_BORDER))
         )

        # --- Overall Layout (Mostly same) ---
        self.layout = ft.Container(
             content = ft.Column(
                [ self.output_column, self.input_row ],
                expand=True, spacing=0
            ),
            bgcolor=COLOR_BACKGROUND, border_radius=ft.border_radius.all(0),
            padding=0, expand=True,
        )

    def get_layout(self) -> ft.Container:
        return self.layout

    def add_message_animated(self, role: str, text: str, timestamp: str = None, on_copy_click: callable = None): # Added copy handler
        """Adds message card directly to column and triggers animation."""
        message_card_animated = create_message_card_v3(role, text, timestamp, on_copy_click) # Pass handler

        # Add the invisible animated container directly to the column
        self.output_column.controls.append(message_card_animated)
        self.output_column.update() # Ensure space is allocated

        # Trigger animation
        message_card_animated.opacity = 1
        message_card_animated.update()

        # Scroll to bottom
        self.output_column.scroll_to(offset=-1, duration=300, curve=ft.AnimationCurve.EASE_OUT)
        # self.output_column.update() # ScrollTo might trigger update implicitly

    # --- Other methods (set_thinking_status, clear_input, etc. same) ---
    def set_thinking_status(self, thinking: bool):
        self.progress_indicator.visible = thinking
        self.progress_indicator.opacity = 1 if thinking else 0
        self.send_button.disabled = thinking
        self.input_field.disabled = thinking
        self.input_row.update() # Update the row containing these elements

    def trigger_send_button_animation(self):
        self.send_button.scale = ft.transform.Scale(0.85)
        self.send_button.update()

    def reset_send_button_animation(self):
         self.send_button.scale = ft.transform.Scale(1.0)
         self.send_button.update()

    def clear_input(self):
        self.input_field.value = ""
        self.input_field.update()