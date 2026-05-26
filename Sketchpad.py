# Tkinter is used for the GUI window, toolbar buttons, canvas drawing, and pop-up windows.
import tkinter as tk

# deque is used for BFS-style graph traversals, such as shortest path and connectivity checks.
from collections import deque

# Main application window.
root = tk.Tk()
root.title("Graph Sketcher")

# Default canvas/window sizing and drawing constants.
WIDTH = 800
HEIGHT = 600

# Base grid size. Vertex positions are stored as centers of these grid squares.
GRID_SIZE = 60

# Radius used when drawing default bullet-style vertices.
RADIUS = 10

# Top toolbar that holds shortcut buttons for common actions.
toolbar = tk.Frame(root, bg="#1a1a1a", height=72)
toolbar.pack(side="top", fill="x")

toolbar_inner = tk.Frame(toolbar, bg="#1a1a1a")
toolbar_inner.pack(anchor="center")


# Creates one button in the top toolbar.
# Each button shows a title, icon-like symbol, and shortcut text.
def make_toolbar_button(parent, title, icon, shortcut, command):
    button = tk.Button(parent, text=f"{title}\n{icon}\n{shortcut}", command=command, bg="#1a1a1a", fg="white", activebackground="#333333", activeforeground="white", relief="flat", bd=0, width=10, height=3, font=("Arial", 8), cursor="hand2")
    button.pack(side="left", padx=2, pady=6)
    return button


make_toolbar_button(toolbar_inner, "Undo", "↶", "ctrl+Z", lambda: undo())
make_toolbar_button(toolbar_inner, "Redo", "↷", "shift+ctrl+Z", lambda: redo())
make_toolbar_button(toolbar_inner, "Select all", "●●", "ctrl+A", lambda: select_everything())
make_toolbar_button(toolbar_inner, "Delete", "✕", "del", lambda: delete_selected())
make_toolbar_button(toolbar_inner, "Move", "▣", "B", lambda: toggle_move_mode())
make_toolbar_button(toolbar_inner, "Center view", "◎", "G", lambda: center_grid())
make_toolbar_button(toolbar_inner, "Zoom out", "⊖", "ctrl+-", lambda: zoom(0.9))
make_toolbar_button(toolbar_inner, "Zoom in", "⊕", "ctrl+=", lambda: zoom(1.1))
make_toolbar_button(toolbar_inner, "Hide grid", "▦", "H", lambda: hide_grid())
make_toolbar_button(toolbar_inner, "Adj List", "≡", "", lambda: show_adjacency_list())
make_toolbar_button(toolbar_inner, "Adj Matrix", "▦", "", lambda: show_adjacency_matrix())
make_toolbar_button(toolbar_inner, "Properties", "✓", "", lambda: show_graph_properties())
make_toolbar_button(toolbar_inner, "Path", "↝", "", lambda: toggle_path_mode())

# Main workspace: canvas on the left, edge toolbar on the right when needed.
workspace = tk.Frame(root)
workspace.pack(fill="both", expand=True)

canvas = tk.Canvas(workspace, width=WIDTH, height=HEIGHT, bg="white")
canvas.pack(side="left", fill="both", expand=True)

# Side toolbar for edge-related actions. It starts hidden and appears when an edge or the whole graph is selected.
edge_toolbar = tk.Frame(workspace, bg="#1a1a1a", width=220)
edge_toolbar.pack(side="right", fill="y")
edge_toolbar.pack_forget()

edge_toolbar_title = tk.Label(edge_toolbar, text="Edge Tools", bg="#1a1a1a", fg="white", font=("Arial", 13, "bold"))
edge_toolbar_title.pack(pady=(15, 10))

make_directed_button = tk.Button(edge_toolbar, text="Make Directed →", bg="#0ea5e9", fg="black", activebackground="#38bdf8", relief="flat", font=("Arial", 11), command=lambda: make_selected_edges_directed())
make_directed_button.pack(fill="x", padx=15, pady=8)

flip_arrow_button = tk.Button(edge_toolbar, text="Flip Arrow", bg="#0ea5e9", fg="black", activebackground="#38bdf8", relief="flat", font=("Arial", 11), command=lambda: flip_selected_edges())
flip_arrow_button.pack(fill="x", padx=15, pady=8)

make_undirected_button = tk.Button(edge_toolbar, text="Make Undirected", bg="#0ea5e9", fg="black", activebackground="#38bdf8", relief="flat", font=("Arial", 11), command=lambda: make_selected_edges_undirected())
make_undirected_button.pack(fill="x", padx=15, pady=8)

# Bottom name bar. When a vertex or edge is selected, this lets the user edit its label.
name_bar = tk.Frame(root, bg="#0ea5e9", height=36)
name_bar.pack(fill="x", side="bottom")

name_entry = tk.Entry(name_bar, justify="center", font=("Arial", 14), bg="#0ea5e9", fg="black", relief="flat", insertbackground="black")
name_entry.pack(fill="x", padx=30, pady=4)

# Core graph data.
# vertices stores vertex positions as (x, y) grid-center tuples.
# edges stores pairs of vertices: ((x1, y1), (x2, y2)).
vertices = []
edges = []

# Label and arrow metadata attached to vertices/edges.
# edge_arrows values are None, "forward", or "reverse".
vertex_labels = {}
edge_labels = {}
edge_arrows = {}

# History stacks used for undo and redo.
undo_stack = []
redo_stack = []

# Selection state. Only one vertex or one edge can be individually selected,
# or select_all can represent the whole graph being selected.
selected_square = None
selected_vertex = None
selected_edge = None
select_all = False
rename_mode = False
move_mode = False
path_mode = False
path_start_vertex = None
highlighted_path_edges = set()
drag_start = None
drag_started_on_existing_vertex = False
preview_pos = None

# View transform: scale controls zoom, offsets control panning.
scale = 1.0
offset_x = 0
offset_y = 0

# Grid visibility and pan tracking state.
show_grid = True
pan_last_x = None
pan_last_y = None



# Converts graph/world coordinates into canvas screen coordinates using current zoom and pan.
def world_to_screen(x, y):
    return x * scale + offset_x, y * scale + offset_y



# Converts canvas screen coordinates back into graph/world coordinates.
def screen_to_world(x, y):
    return (x - offset_x) / scale, (y - offset_y) / scale



# Converts a mouse click position into the nearest logical grid-square center.
# This version accounts for dynamic column widths caused by long vertex labels.
def snap_to_square_center(screen_x, screen_y):
    world_x, world_y = screen_to_world(screen_x, screen_y)

    col_widths = get_column_widths()

    row = int(world_y // GRID_SIZE)

    min_col, max_col = get_visible_col_range()
    chosen_col = min_col

    for col in range(min_col, max_col + 1):
        left = get_column_left(col, col_widths)
        right = left + col_widths.get(col, GRID_SIZE)

        if left <= world_x < right:
            chosen_col = col
            break

    return grid_to_vertex(chosen_col, row)



# Original fixed-grid square bounds helper. Kept for reference/compatibility, but dynamic bounds are used for drawing.
def get_square_bounds(center_x, center_y):
    left = center_x - GRID_SIZE // 2
    top = center_y - GRID_SIZE // 2
    right = center_x + GRID_SIZE // 2
    bottom = center_y + GRID_SIZE // 2
    return left, top, right, bottom


# Converts a stored vertex coordinate into a logical grid column and row.
def vertex_to_grid(vertex):
    x, y = vertex
    col = int(x // GRID_SIZE)
    row = int(y // GRID_SIZE)
    return col, row



# Converts a logical grid column and row into the stored vertex center coordinate.
def grid_to_vertex(col, row):
    return col * GRID_SIZE + GRID_SIZE // 2, row * GRID_SIZE + GRID_SIZE // 2



# Estimates which grid columns are visible, plus some buffer columns.
def get_visible_col_range():
    left_world, _ = screen_to_world(0, 0)
    right_world, _ = screen_to_world(canvas.winfo_width(), 0)

    min_col = int(left_world // GRID_SIZE) - 3
    max_col = int(right_world // GRID_SIZE) + 3

    return min_col, max_col



# Measures how wide a label is in world units so grid columns can expand to fit it.
def measure_text_width_world(label, font):
    temp = canvas.create_text(0, 0, text=label, font=font, anchor="nw")
    bbox = canvas.bbox(temp)
    canvas.delete(temp)

    if not bbox:
        return 0

    screen_width = bbox[2] - bbox[0]
    return screen_width / scale



# Calculates the width of each visible grid column.
# Columns expand when labels are wider than a normal grid square.
def get_column_widths():
    min_col, max_col = get_visible_col_range()

    col_widths = {}
    for col in range(min_col, max_col + 1):
        col_widths[col] = GRID_SIZE

    font = ("Arial", max(12, int(20 * scale)), "italic")

    for vertex in vertices:
        col, row = vertex_to_grid(vertex)

        if col not in col_widths:
            col_widths[col] = GRID_SIZE

        raw_label = vertex_labels.get(vertex, r"\bullet")
        label, label_color = parse_label_style(raw_label)

        if label != "•":
            needed_width = measure_text_width_world(label, font) + 30
            col_widths[col] = max(col_widths[col], needed_width)

    return col_widths



# Returns the world x-coordinate of the left boundary of a dynamic column.
def get_column_left(col, col_widths):
    x = 0
    if col >= 0:
        for c in range(0, col):
            x += col_widths.get(c, GRID_SIZE)
    else:
        for c in range(-1, col - 1, -1):
            x -= col_widths.get(c, GRID_SIZE)
    return x



# Returns the world x-coordinate of the center of a dynamic column.
def get_column_center(col, col_widths):
    left = get_column_left(col, col_widths)
    width = col_widths.get(col, GRID_SIZE)
    return left + width / 2



# Returns the actual drawn position of a vertex after dynamic column resizing.
def get_dynamic_vertex_position(vertex, col_widths):
    col, row = vertex_to_grid(vertex)
    x = get_column_center(col, col_widths)
    y = row * GRID_SIZE + GRID_SIZE // 2
    return x, y



# Returns the actual dynamic square bounds for a vertex/grid cell.
def get_dynamic_square_bounds(vertex, col_widths):
    col, row = vertex_to_grid(vertex)

    left = get_column_left(col, col_widths)
    right = left + col_widths.get(col, GRID_SIZE)

    top = row * GRID_SIZE
    bottom = top + GRID_SIZE

    return left, top, right, bottom


# Converts a small subset of LaTeX-like labels into displayable Unicode text.
def display_label(label):
    replacements = {
        r"\bullet": "•",
        r"\alpha": "α",
        r"\beta": "β",
        r"\gamma": "γ",
        r"\delta": "δ",
        r"\epsilon": "ε",
        r"\zeta": "ζ",
        r"\eta": "η",
        r"\theta": "θ",
        r"\iota": "ι",
        r"\kappa": "κ",
        r"\lambda": "λ",
        r"\mu": "μ",
        r"\nu": "ν",
        r"\xi": "ξ",
        r"\pi": "π",
        r"\rho": "ρ",
        r"\sigma": "σ",
        r"\tau": "τ",
        r"\upsilon": "υ",
        r"\phi": "φ",
        r"\chi": "χ",
        r"\psi": "ψ",
        r"\omega": "ω",
        r"\Gamma": "Γ",
        r"\Delta": "Δ",
        r"\Theta": "Θ",
        r"\Lambda": "Λ",
        r"\Pi": "Π",
        r"\Sigma": "Σ",
        r"\Phi": "Φ",
        r"\Psi": "Ψ",
        r"\Omega": "Ω",
    }

    label = replacements.get(label, label)

    subscript_map = {
        "0": "₀",
        "1": "₁",
        "2": "₂",
        "3": "₃",
        "4": "₄",
        "5": "₅",
        "6": "₆",
        "7": "₇",
        "8": "₈",
        "9": "₉",
        "i": "ᵢ",
        "j": "ⱼ",
        "k": "ₖ",
        "n": "ₙ",
    }

    # Simple subscript support:
    # v_1 -> v₁
    # x_i -> xᵢ
    # a_12 -> a₁₂
    result = ""
    i = 0

    while i < len(label):
        if label[i] == "_" and i + 1 < len(label):
            i += 1

            if label[i] == "{" and "}" in label[i:]:
                end = label.find("}", i)
                subscript_text = label[i + 1:end]
                result += "".join(subscript_map.get(ch, ch) for ch in subscript_text)
                i = end + 1
            else:
                result += subscript_map.get(label[i], label[i])
                i += 1
        else:
            result += label[i]
            i += 1

    return result


# Parses simple label styling, especially \textcolor{color}{label}.
# Returns the display text and the Tkinter color string.
def parse_label_style(raw_label):
    color = "black"
    label = raw_label

    prefix = r"\textcolor{"

    if label.startswith(prefix):
        color_start = len(prefix)
        color_end = label.find("}", color_start)

        if color_end != -1:
            possible_color = label[color_start:color_end]

            text_start = color_end + 1

            if text_start < len(label) and label[text_start] == "{":
                text_end = label.rfind("}")

                if text_end != -1 and text_end > text_start:
                    color = possible_color
                    label = label[text_start + 1:text_end]

    return display_label(label), color


# Draws a blue instruction box while move mode is active.
def draw_move_mode_indicator():
    if not move_mode:
        return

    width = canvas.winfo_width()

    box_width = 430
    box_height = 78

    x1 = width / 2 - box_width / 2
    y1 = 20
    x2 = width / 2 + box_width / 2
    y2 = y1 + box_height

    canvas.create_rectangle(x1, y1, x2, y2, fill="#0ea5e9", outline="#0ea5e9")

    canvas.create_text(width / 2, y1 + 25, text="Move the selected objects with the arrow keys.", fill="black", font=("Arial", 13))

    canvas.create_text(width / 2, y1 + 55, text="Press B or Esc to finish moving.", fill="black", font=("Arial", 13))


# Draws graph-related information overlays, such as degree info and path-mode instructions.
def draw_graph_info_indicator():
    if selected_vertex:
        degree, in_degree, out_degree = get_vertex_degrees(selected_vertex)

        x1 = 20
        y1 = 20
        x2 = 190
        y2 = 100

        canvas.create_rectangle(x1, y1, x2, y2, fill="#0ea5e9", outline="#0ea5e9")

        canvas.create_text(x1 + 10, y1 + 18, anchor="w", text=f"Degree: {degree}", fill="black", font=("Arial", 12))

        canvas.create_text(x1 + 10, y1 + 42, anchor="w", text=f"In-degree: {in_degree}", fill="black", font=("Arial", 12))

        canvas.create_text(x1 + 10, y1 + 66, anchor="w", text=f"Out-degree: {out_degree}", fill="black", font=("Arial", 12))

    if path_mode:
        width = canvas.winfo_width()

        box_width = 430
        box_height = 54

        x1 = width / 2 - box_width / 2
        y1 = 110
        x2 = width / 2 + box_width / 2
        y2 = y1 + box_height

        canvas.create_rectangle(x1, y1, x2, y2, fill="#0ea5e9", outline="#0ea5e9")

        if path_start_vertex:
            message = "Click the ending vertex for the shortest path."
        else:
            message = "Click the starting vertex for the shortest path."

        canvas.create_text(width / 2, y1 + 27, text=message, fill="black", font=("Arial", 13))



# Fully redraws the canvas: grid, selected square, edges, labels, vertices, and overlays.
def redraw():
    canvas.delete("all")

    width = canvas.winfo_width()
    height = canvas.winfo_height()

    col_widths = get_column_widths()

    left_world, top_world = screen_to_world(0, 0)
    right_world, bottom_world = screen_to_world(width, height)

    min_col, max_col = get_visible_col_range()

    start_row = int(top_world // GRID_SIZE) - 1
    end_row = int(bottom_world // GRID_SIZE) + 1

    # draw grid ONLY if enabled
    if show_grid:
        # horizontal dashed lines
        for row in range(start_row, end_row + 2):
            y = row * GRID_SIZE
            _, sy = world_to_screen(0, y)
            canvas.create_line(0, sy, width, sy, fill="lightgray", dash=(3, 3))

        # vertical dashed lines using dynamic column widths
        for col in range(min_col, max_col + 2):
            x = get_column_left(col, col_widths)
            sx, _ = world_to_screen(x, 0)
            canvas.create_line(sx, 0, sx, height, fill="lightgray", dash=(3, 3))

    # draw selected square
    if selected_square:
        cx, cy = selected_square
        col_widths = get_column_widths()
        left, top, right, bottom = get_dynamic_square_bounds((cx, cy), col_widths)

        sx1, sy1 = world_to_screen(left, top)
        sx2, sy2 = world_to_screen(right, bottom)

        canvas.create_rectangle(sx1, sy1, sx2, sy2, fill="lightgray", outline="gray", stipple="gray25")

        dyn_x, dyn_y = get_dynamic_vertex_position((cx, cy), col_widths)
        text_x, text_y = world_to_screen(dyn_x, dyn_y)
        canvas.create_text(text_x, text_y, text="Add Vertex", fill="gray", font=("Arial", max(6, int(8 * scale))))

    # draw edges
    for edge in edges:
        (x1, y1), (x2, y2) = edge

        wx1, wy1 = get_dynamic_vertex_position((x1, y1), col_widths)
        wx2, wy2 = get_dynamic_vertex_position((x2, y2), col_widths)

        sx1, sy1 = world_to_screen(wx1, wy1)
        sx2, sy2 = world_to_screen(wx2, wy2)

        if edge in highlighted_path_edges:
            canvas.create_line(sx1, sy1, sx2, sy2, width=max(6, int(10 * scale)), fill="#f59e0b")

        if selected_edge == edge or select_all:
            canvas.create_line(sx1, sy1, sx2, sy2, width=max(6, int(10 * scale)), fill="lightgray")

        arrow_direction = edge_arrows.get(edge, None)

        arrow_style = None
        if arrow_direction == "forward":
            arrow_style = tk.LAST
        elif arrow_direction == "reverse":
            arrow_style = tk.FIRST

        canvas.create_line(sx1, sy1, sx2, sy2, width=max(1, int(2 * scale)), fill="black", arrow=arrow_style, arrowshape=(12 * scale, 15 * scale, 5 * scale))

        raw_label = edge_labels.get(edge, "")

        if raw_label:
            label, label_color = parse_label_style(raw_label)

            mid_x = (wx1 + wx2) / 2
            mid_y = (wy1 + wy2) / 2
            
            smx, smy = world_to_screen(mid_x, mid_y)

            canvas.create_text(smx, smy - 18 * scale, text=label, fill=label_color, font=("Arial", max(10, int(16 * scale))))
        

    # draw preview line while dragging
    if drag_start and preview_pos:
        wx1, wy1 = get_dynamic_vertex_position(drag_start, col_widths)
        sx1, sy1 = world_to_screen(wx1, wy1)
        canvas.create_line(sx1, sy1, preview_pos[0], preview_pos[1], width=max(1, int(2 * scale)))

    # draw vertices
    for x, y in vertices:
        wx, wy = get_dynamic_vertex_position((x, y), col_widths)
        sx, sy = world_to_screen(wx, wy)
        r = RADIUS * scale

        raw_label = vertex_labels.get((x, y), r"\bullet")
        label, label_color = parse_label_style(raw_label)

        is_selected = selected_vertex == (x, y) or select_all

        if label == "•":
            if is_selected:
                highlight_r = (RADIUS + 18) * scale
                canvas.create_oval(sx - highlight_r, sy - highlight_r, sx + highlight_r, sy + highlight_r, fill="lightgray", outline="")

            canvas.create_oval(sx - r, sy - r, sx + r, sy + r, fill="black", outline="black")

        else:
            font_size = max(12, int(20 * scale))
            font = ("Arial", font_size, "italic")

            # invisible text used to measure the label size
            temp_id = canvas.create_text(sx, sy, text=label, font=font)
            bbox = canvas.bbox(temp_id)
            canvas.delete(temp_id)

            if bbox:
                x1, y1, x2, y2 = bbox
                padding_x = 14 * scale
                padding_y = 10 * scale

                if is_selected:
                    canvas.create_rectangle(x1 - padding_x, y1 - padding_y, x2 + padding_x, y2 + padding_y, fill="lightgray", outline="", width=0)

            canvas.create_text(sx,sy,text=label,fill=label_color,font=font)

    draw_move_mode_indicator()
    draw_graph_info_indicator()
    update_edge_toolbar()


# Saves the current graph state before a graph-changing action for undo support.
def save_state():
    undo_stack.append((vertices.copy(), edges.copy(), vertex_labels.copy(), edge_labels.copy(), edge_arrows.copy()))
    redo_stack.clear()



# Restores the previous saved graph state and pushes the current state to redo history.
def undo():
    global vertices, edges, vertex_labels, edge_labels, edge_arrows
    global selected_square, selected_vertex, selected_edge, select_all

    if not undo_stack:
        return

    redo_stack.append((vertices.copy(), edges.copy(), vertex_labels.copy(), edge_labels.copy(), edge_arrows.copy()))

    restored_state = undo_stack.pop()

    if len(restored_state) == 5:
        vertices, edges, vertex_labels, edge_labels, edge_arrows = restored_state
    else:
        vertices, edges, vertex_labels, edge_labels = restored_state
        edge_arrows = {}

    selected_square = None
    selected_vertex = None
    selected_edge = None
    select_all = False

    update_name_bar()
    redraw()



# Restores the most recently undone state and pushes the current state back to undo history.
def redo():
    global vertices, edges, vertex_labels, edge_labels, edge_arrows
    global selected_square, selected_vertex, selected_edge, select_all

    if not redo_stack:
        return

    undo_stack.append((vertices.copy(), edges.copy(), vertex_labels.copy(), edge_labels.copy(), edge_arrows.copy()))

    restored_state = redo_stack.pop()

    if len(restored_state) == 5:
        vertices, edges, vertex_labels, edge_labels, edge_arrows = restored_state
    else:
        vertices, edges, vertex_labels, edge_labels = restored_state
        edge_arrows = {}

    selected_square = None
    selected_vertex = None
    selected_edge = None
    select_all = False

    update_name_bar()
    redraw()


# Adds a vertex if it does not already exist and gives it the default bullet label.
def add_vertex(vertex):
    if vertex not in vertices:
        vertices.append(vertex)
        vertex_labels[vertex] = r"\bullet"



# Adds an undirected edge between two vertices if it is not already present.
def add_edge(v1, v2):
    if v1 == v2:
        return

    edge = (v1, v2)
    reverse_edge = (v2, v1)

    if edge not in edges and reverse_edge not in edges:
        edges.append(edge)
        edge_labels[edge] = ""
        edge_arrows[edge] = None


# Clears a pending selected square if the mouse moves off it before adding a vertex.
def on_mouse_move(event):
    global selected_square

    if selected_square:
        current_square = snap_to_square_center(event.x, event.y)

        if current_square != selected_square:
            selected_square = None
            redraw()



# Zooms in or out while keeping the same world point under the zoom center.
def zoom(factor, screen_x=None, screen_y=None):
    global scale, offset_x, offset_y

    if screen_x is None:
        screen_x = canvas.winfo_width() / 2
    if screen_y is None:
        screen_y = canvas.winfo_height() / 2

    world_x, world_y = screen_to_world(screen_x, screen_y)

    scale *= factor

    offset_x = screen_x - world_x * scale
    offset_y = screen_y - world_y * scale

    redraw()


# Pans the view so the given world coordinate appears at the center of the canvas.
def center_view_on(world_x, world_y):
    global offset_x, offset_y

    canvas_center_x = canvas.winfo_width() / 2
    canvas_center_y = canvas.winfo_height() / 2

    offset_x = canvas_center_x - world_x * scale
    offset_y = canvas_center_y - world_y * scale

    redraw()


# Deletes the current selection.
# If a vertex is deleted, all incident edges and related metadata are also deleted.
def delete_selected():
    global selected_vertex, selected_edge, selected_square, select_all
    global vertices, edges, vertex_labels, edge_labels, edge_arrows

    if select_all:
        save_state()

        vertices.clear()
        edges.clear()
        vertex_labels.clear()
        edge_labels.clear()
        edge_arrows.clear()

        selected_vertex = None
        selected_edge = None
        selected_square = None
        select_all = False

        update_name_bar()
        redraw()
        return

    if selected_vertex:
        save_state()

        vertex_to_delete = selected_vertex

        if vertex_to_delete in vertices:
            vertices.remove(vertex_to_delete)
        
        vertex_labels.pop(vertex_to_delete, None)

        edges = [
            edge for edge in edges
            if vertex_to_delete not in edge
        ]

        edge_labels = {
        edge: label
        for edge, label in edge_labels.items()
        if edge in edges
        }

        edge_arrows = {
            edge: direction
            for edge, direction in edge_arrows.items()
            if edge in edges
        }

        selected_vertex = None
        selected_edge = None
        selected_square = None

        update_name_bar()
        redraw()

    elif selected_edge:
        save_state()

        edge_to_delete = selected_edge
        reverse_edge = (edge_to_delete[1], edge_to_delete[0])

        if edge_to_delete in edges:
            edges.remove(edge_to_delete)
        elif reverse_edge in edges:
            edges.remove(reverse_edge)

        edge_labels.pop(edge_to_delete, None)
        edge_labels.pop(reverse_edge, None)

        edge_arrows.pop(edge_to_delete, None)
        edge_arrows.pop(reverse_edge, None)

        selected_edge = None
        selected_vertex = None
        selected_square = None

        update_name_bar()
        redraw()


# Toggles the dashed grid on or off.
def hide_grid():
    global show_grid
    show_grid = not show_grid
    redraw()


# Centers the view on the selected vertex, selected edge, whole graph, or origin.
def center_grid():
    col_widths = get_column_widths()

    if select_all and vertices:
        total_x = 0
        total_y = 0

        for vertex in vertices:
            x, y = get_dynamic_vertex_position(vertex, col_widths)
            total_x += x
            total_y += y

        center_x = total_x / len(vertices)
        center_y = total_y / len(vertices)

        center_view_on(center_x, center_y)

    elif selected_vertex:
        x, y = get_dynamic_vertex_position(selected_vertex, col_widths)
        center_view_on(x, y)

    elif selected_edge:
        v1, v2 = selected_edge

        x1, y1 = get_dynamic_vertex_position(v1, col_widths)
        x2, y2 = get_dynamic_vertex_position(v2, col_widths)

        edge_center_x = (x1 + x2) / 2
        edge_center_y = (y1 + y2) / 2

        center_view_on(edge_center_x, edge_center_y)

    else:
        center_view_on(0, 0)


# Updates the bottom label-entry bar to match the currently selected vertex or edge.
def update_name_bar():
    name_entry.delete(0, tk.END)

    if select_all:
        return

    if selected_vertex:
        name_entry.insert(0, vertex_labels.get(selected_vertex, r"\bullet"))

    elif selected_edge:
        name_entry.insert(0, edge_labels.get(selected_edge, ""))



# Applies the bottom name-bar text to the selected vertex or edge label.
def apply_name_change(event=None):
    global selected_vertex, selected_edge, rename_mode

    if select_all:
        return

    new_name = name_entry.get()

    if selected_vertex:
        old_name = vertex_labels.get(selected_vertex, r"\bullet")

        if new_name.strip() == "":
            new_name = r"\bullet"

        if new_name != old_name:
            save_state()
            vertex_labels[selected_vertex] = new_name

    elif selected_edge:
        old_name = edge_labels.get(selected_edge, "")

        if new_name != old_name:
            save_state()
            edge_labels[selected_edge] = new_name

    rename_mode = False
    root.focus_set()
    redraw()


# Finds where a moved vertex should land.
# If another vertex is in the way, it skips over occupied grid positions.
def get_next_open_position(vertex, dx, dy, moving_vertices):
    occupied_vertices = set(vertices) - set(moving_vertices)

    x, y = vertex
    next_position = (x + dx, y + dy)

    # If another vertex is in the way, keep jumping over vertices
    # until we find an empty square.
    while next_position in occupied_vertices:
        next_position = (next_position[0] + dx, next_position[1] + dy)

    return next_position



# Moves the selected vertex or all vertices by one grid step in the given direction.
def move_selected(dx, dy):
    global vertices, edges, vertex_labels, edge_labels, edge_arrows
    global selected_vertex, selected_edge, selected_square, select_all

    if not move_mode:
        return

    if not selected_vertex and not select_all:
        return

    save_state()

    if select_all:
        moving_vertices = vertices.copy()
        position_map = {
            vertex: (vertex[0] + dx, vertex[1] + dy)
            for vertex in moving_vertices
        }

    else:
        moving_vertices = [selected_vertex]
        new_position = get_next_open_position(selected_vertex, dx, dy, moving_vertices)
        position_map = {
            selected_vertex: new_position
        }

    # update vertices
    vertices = [
        position_map.get(vertex, vertex)
        for vertex in vertices
    ]

    # update vertex labels
    vertex_labels = {
        position_map.get(vertex, vertex): label
        for vertex, label in vertex_labels.items()
    }

    # update edges
    new_edges = []
    new_edge_labels = {}
    new_edge_arrows = {}

    for edge in edges:
        v1, v2 = edge

        new_v1 = position_map.get(v1, v1)
        new_v2 = position_map.get(v2, v2)

        new_edge = (new_v1, new_v2)
        new_edges.append(new_edge)

        if edge in edge_labels:
            new_edge_labels[new_edge] = edge_labels[edge]

        if edge in edge_arrows:
            new_edge_arrows[new_edge] = edge_arrows[edge]

    edges = new_edges
    edge_labels = new_edge_labels
    edge_arrows = new_edge_arrows

    # update selected vertex after moving
    if selected_vertex in position_map:
        selected_vertex = position_map[selected_vertex]

    selected_square = None
    selected_edge = None

    update_name_bar()
    redraw()


# Returns a readable name for a vertex for adjacency lists/matrices and reports.
def get_vertex_name(vertex):
    index = vertices.index(vertex) if vertex in vertices else 0
    raw_label = vertex_labels.get(vertex, r"\bullet")
    label, color = parse_label_style(raw_label)

    if label == "•":
        return f"v{index}"

    return label



# Builds an adjacency list that respects edge arrow direction.
def get_directed_neighbors():
    adjacency = {vertex: [] for vertex in vertices}

    for edge in edges:
        v1, v2 = edge
        direction = edge_arrows.get(edge, None)

        if direction == "forward":
            adjacency[v1].append(v2)

        elif direction == "reverse":
            adjacency[v2].append(v1)

        else:
            adjacency[v1].append(v2)
            adjacency[v2].append(v1)

    return adjacency



# Builds an adjacency list that ignores edge arrow direction.
def get_undirected_neighbors():
    adjacency = {vertex: [] for vertex in vertices}

    for edge in edges:
        v1, v2 = edge
        adjacency[v1].append(v2)
        adjacency[v2].append(v1)

    return adjacency



# Computes total degree, in-degree, and out-degree for a vertex.
def get_vertex_degrees(vertex):
    degree = 0
    in_degree = 0
    out_degree = 0

    for edge in edges:
        v1, v2 = edge
        direction = edge_arrows.get(edge, None)

        if direction is None:
            if vertex == v1 or vertex == v2:
                degree += 1

        elif direction == "forward":
            if vertex == v1:
                out_degree += 1
            elif vertex == v2:
                in_degree += 1

        elif direction == "reverse":
            if vertex == v2:
                out_degree += 1
            elif vertex == v1:
                in_degree += 1

    total_degree = degree + in_degree + out_degree
    return total_degree, in_degree, out_degree



# Opens a popup window containing read-only text output.
def show_text_window(title, content):
    window = tk.Toplevel(root)
    window.title(title)
    window.geometry("650x500")

    text_box = tk.Text(window, wrap="none", font=("Consolas", 11))
    text_box.pack(fill="both", expand=True)

    text_box.insert("1.0", content)
    text_box.config(state="disabled")


# Shows the graph as an adjacency list in a popup.
def show_adjacency_list():
    adjacency = get_directed_neighbors()

    lines = []
    lines.append("Adjacency List")
    lines.append("")
    lines.append("Directed edges are respected.")
    lines.append("Undirected edges appear in both directions.")
    lines.append("")

    for vertex in vertices:
        vertex_name = get_vertex_name(vertex)
        neighbors = adjacency.get(vertex, [])

        neighbor_names = [
            get_vertex_name(neighbor)
            for neighbor in neighbors
        ]

        if neighbor_names:
            lines.append(f"{vertex_name}: {', '.join(neighbor_names)}")
        else:
            lines.append(f"{vertex_name}: ")

    show_text_window("Adjacency List", "\n".join(lines))



# Shows the graph as an adjacency matrix in a popup.
def show_adjacency_matrix():
    adjacency = get_directed_neighbors()

    names = [
        get_vertex_name(vertex)
        for vertex in vertices
    ]

    if not vertices:
        show_text_window("Adjacency Matrix", "The graph is empty.")
        return

    max_name_length = max(len(name) for name in names)
    cell_width = max(max_name_length + 2, 5)

    lines = []
    lines.append("Adjacency Matrix")
    lines.append("")

    header = " " * cell_width
    for name in names:
        header += name.center(cell_width)
    lines.append(header)

    for row_vertex, row_name in zip(vertices, names):
        row = row_name.center(cell_width)

        for col_vertex in vertices:
            value = 1 if col_vertex in adjacency.get(row_vertex, []) else 0
            row += str(value).center(cell_width)

        lines.append(row)

    show_text_window("Adjacency Matrix", "\n".join(lines))


# Checks whether the underlying undirected graph is connected.
def is_connected():
    if not vertices:
        return True

    adjacency = get_undirected_neighbors()

    visited = set()
    queue = deque([vertices[0]])
    visited.add(vertices[0])

    while queue:
        current = queue.popleft()

        for neighbor in adjacency[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return len(visited) == len(vertices)



# Checks whether the underlying undirected graph contains a cycle.
def has_cycle():
    adjacency = get_undirected_neighbors()
    visited = set()

    def dfs(vertex, parent):
        visited.add(vertex)

        for neighbor in adjacency[vertex]:
            if neighbor not in visited:
                if dfs(neighbor, vertex):
                    return True
            elif neighbor != parent:
                return True

        return False

    for vertex in vertices:
        if vertex not in visited:
            if dfs(vertex, None):
                return True

    return False



# Checks whether the underlying undirected graph is bipartite using BFS coloring.
def is_bipartite():
    adjacency = get_undirected_neighbors()
    colors = {}

    for start in vertices:
        if start not in colors:
            colors[start] = 0
            queue = deque([start])

            while queue:
                current = queue.popleft()

                for neighbor in adjacency[current]:
                    if neighbor not in colors:
                        colors[neighbor] = 1 - colors[current]
                        queue.append(neighbor)
                    elif colors[neighbor] == colors[current]:
                        return False

    return True



# Checks whether the underlying undirected graph has an Euler path.
def has_euler_path():
    adjacency = get_undirected_neighbors()

    non_isolated_vertices = [
        vertex for vertex in vertices
        if len(adjacency[vertex]) > 0
    ]

    if not non_isolated_vertices:
        return True

    visited = set()
    queue = deque([non_isolated_vertices[0]])
    visited.add(non_isolated_vertices[0])

    while queue:
        current = queue.popleft()

        for neighbor in adjacency[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    for vertex in non_isolated_vertices:
        if vertex not in visited:
            return False

    odd_count = 0

    for vertex in vertices:
        if len(adjacency[vertex]) % 2 == 1:
            odd_count += 1

    return odd_count == 0 or odd_count == 2



# Shows a popup summary of graph properties and counts.
def show_graph_properties():
    directed_edge_count = sum(1 for edge in edges if edge_arrows.get(edge, None) is not None)

    connected = is_connected()
    cycle_exists = has_cycle()
    bipartite = is_bipartite()
    euler_path = has_euler_path()

    is_tree = (len(vertices) > 0 and connected and not cycle_exists and len(edges) == len(vertices) - 1)

    lines = []
    lines.append("Graph Properties")
    lines.append("")
    lines.append(f"Vertices: {len(vertices)}")
    lines.append(f"Edges: {len(edges)}")
    lines.append(f"Directed edges: {directed_edge_count}")
    lines.append("")
    lines.append(f"Connected: {'Yes' if connected else 'No'}")
    lines.append(f"Tree: {'Yes' if is_tree else 'No'}")
    lines.append(f"Cycle exists: {'Yes' if cycle_exists else 'No'}")
    lines.append(f"Bipartite: {'Yes' if bipartite else 'No'}")
    lines.append(f"Euler path exists: {'Yes' if euler_path else 'No'}")
    lines.append("")
    lines.append("Note:")
    lines.append("connectivity/tree/cycle/bipartite/euler checks ignore arrow direction.")

    show_text_window("Graph Properties", "\n".join(lines))


# Finds the stored edge connecting two vertices, ignoring direction.
def find_edge_between(v1, v2):
    for edge in edges:
        a, b = edge

        if (a == v1 and b == v2) or (a == v2 and b == v1):
            return edge

    return None



# Finds a shortest directed path from start to end using BFS.
def find_shortest_path(start, end):
    adjacency = get_directed_neighbors()

    queue = deque([start])
    previous = {start: None}

    while queue:
        current = queue.popleft()

        if current == end:
            break

        for neighbor in adjacency[current]:
            if neighbor not in previous:
                previous[neighbor] = current
                queue.append(neighbor)

    if end not in previous:
        return None

    path = []
    current = end

    while current is not None:
        path.append(current)
        current = previous[current]

    path.reverse()
    return path



# Converts a vertex path into edges that should be highlighted on the canvas.
def set_highlighted_path(path):
    global highlighted_path_edges

    highlighted_path_edges = set()

    if not path:
        return

    for i in range(len(path) - 1):
        edge = find_edge_between(path[i], path[i + 1])

        if edge:
            highlighted_path_edges.add(edge)



# Turns shortest-path picking mode on or off.
def toggle_path_mode():
    global path_mode, path_start_vertex, highlighted_path_edges
    global move_mode, rename_mode

    path_mode = not path_mode
    path_start_vertex = None
    highlighted_path_edges = set()

    move_mode = False
    rename_mode = False

    root.focus_set()
    redraw()



# Handles vertex clicks while path mode is active. First click sets start; second click sets end.
def handle_path_vertex_click(vertex):
    global path_mode, path_start_vertex

    if not path_mode:
        return False

    if path_start_vertex is None:
        path_start_vertex = vertex
        redraw()
        return True

    path = find_shortest_path(path_start_vertex, vertex)
    set_highlighted_path(path)

    path_mode = False
    path_start_vertex = None

    redraw()
    return True


# Selects the entire graph.
def select_everything():
    global selected_square, selected_vertex, selected_edge, select_all, move_mode, rename_mode

    selected_square = None
    selected_vertex = None
    selected_edge = None
    select_all = True
    move_mode = False
    rename_mode = False

    root.focus_set()
    update_name_bar()
    redraw()



# Toggles move mode when a vertex or the whole graph is selected.
def toggle_move_mode():
    global move_mode, selected_square

    if selected_vertex or select_all:
        move_mode = not move_mode
        selected_square = None
        root.focus_set()
        redraw()


# Shows or hides the side edge toolbar depending on the current selection.
def update_edge_toolbar():
    if selected_edge or select_all:
        if not edge_toolbar.winfo_ismapped():
            edge_toolbar.pack(side="right", fill="y")
    else:
        if edge_toolbar.winfo_ismapped():
            edge_toolbar.pack_forget()



# Returns the edge or edges affected by side-toolbar edge actions.
def get_selected_edges():
    if select_all:
        return edges.copy()

    if selected_edge:
        return [selected_edge]

    return []



# Makes selected edge(s) directed in their stored forward direction.
def make_selected_edges_directed():
    global edge_arrows

    selected_edges = get_selected_edges()

    if not selected_edges:
        return

    save_state()

    for edge in selected_edges:
        edge_arrows[edge] = "forward"

    redraw()



# Flips selected edge arrow directions.
def flip_selected_edges():
    global edge_arrows

    selected_edges = get_selected_edges()

    if not selected_edges:
        return

    save_state()

    for edge in selected_edges:
        current_direction = edge_arrows.get(edge, None)

        if current_direction == "forward":
            edge_arrows[edge] = "reverse"
        elif current_direction == "reverse":
            edge_arrows[edge] = "forward"
        else:
            edge_arrows[edge] = "reverse"

    redraw()


# Removes arrow direction from selected edge(s).
def make_selected_edges_undirected():
    global edge_arrows

    selected_edges = get_selected_edges()

    if not selected_edges:
        return

    save_state()

    for edge in selected_edges:
        edge_arrows[edge] = None

    redraw()


# Clears path mode and removes highlighted shortest-path edges.
def global_path_mode_clear():
    global path_mode, path_start_vertex, highlighted_path_edges

    path_mode = False
    path_start_vertex = None
    highlighted_path_edges = set()


# Handles all keyboard shortcuts.
def on_key(event):
    global show_grid, select_all, selected_square, selected_vertex, selected_edge, rename_mode, move_mode

    if root.focus_get() == name_entry:
        return

    if event.state & 0x4:  # Shortcuts using Control key
        if event.keysym.lower() == "a":
            select_everything()

        elif event.keysym.lower() == "z":
            if event.state & 0x1:
                redo()
            else:
                undo()

        elif event.keysym in ["equal", "plus"]:
            zoom(1.1)
        elif event.keysym == "minus":
            zoom(0.9)

    elif event.keysym == "h":
        hide_grid()

    elif event.keysym == "g":
        center_grid()
    
    elif event.keysym in ["BackSpace", "Delete"]:
        delete_selected()

    elif event.keysym == "b":
        toggle_move_mode()

    elif event.keysym == "Escape":
        move_mode = False
        global_path_mode_clear()
        root.focus_set()
        redraw()

    elif event.keysym == "Left":
        move_selected(-GRID_SIZE, 0)

    elif event.keysym == "Right":
        move_selected(GRID_SIZE, 0)

    elif event.keysym == "Up":
        move_selected(0, -GRID_SIZE)

    elif event.keysym == "Down":
        move_selected(0, GRID_SIZE)


# Finds the vertex under/near a mouse position.
def find_vertex(screen_x, screen_y):
    wx, wy = screen_to_world(screen_x, screen_y)
    col_widths = get_column_widths()

    for vertex in vertices:
        vx, vy = get_dynamic_vertex_position(vertex, col_widths)
        if (wx - vx) ** 2 + (wy - vy) ** 2 <= RADIUS ** 2:
            return vertex

    return None


# Finds an edge near a mouse position by projecting onto each edge segment.
def find_edge(screen_x, screen_y):
    wx, wy = screen_to_world(screen_x, screen_y)
    tolerance = 8 / scale
    col_widths = get_column_widths()

    for edge in edges:
        v1, v2 = edge

        x1, y1 = get_dynamic_vertex_position(v1, col_widths)
        x2, y2 = get_dynamic_vertex_position(v2, col_widths)

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            continue

        t = ((wx - x1) * dx + (wy - y1) * dy) / (dx * dx + dy * dy)

        if 0 <= t <= 1:
            closest_x = x1 + t * dx
            closest_y = y1 + t * dy

            distance_squared = (wx - closest_x) ** 2 + (wy - closest_y) ** 2

            if distance_squared <= tolerance ** 2:
                return edge

    return None


# Handles mouse press: starts a drag from an existing vertex or a grid square.
def on_press(event):
    global drag_start, preview_pos, drag_started_on_existing_vertex

    clicked_vertex = find_vertex(event.x, event.y)

    if clicked_vertex:
        drag_start = clicked_vertex
        drag_started_on_existing_vertex = True
    else:
        drag_start = snap_to_square_center(event.x, event.y)
        drag_started_on_existing_vertex = False

    preview_pos = None



# Handles mouse drag: updates the preview edge line.
def on_drag(event):
    global preview_pos

    if drag_start:
        preview_pos = (event.x, event.y)
        redraw()


# Focuses the bottom name bar so the selected object can be renamed.
def enter_rename_mode():
    global rename_mode

    rename_mode = True
    update_name_bar()
    name_entry.focus_set()
    name_entry.select_range(0, tk.END)
    name_entry.icursor(tk.END)


# Handles mouse release: selects objects, creates vertices/edges, or handles path clicks.
def on_release(event):
    global selected_square, selected_vertex, selected_edge, select_all, rename_mode, move_mode
    global drag_start, preview_pos, drag_started_on_existing_vertex

    select_all = False
    move_mode = False

    end_square = snap_to_square_center(event.x, event.y)
    end_was_existing_vertex = end_square in vertices

    if drag_start and preview_pos:
        before_vertices = vertices.copy()
        before_edges = edges.copy()
        before_vertex_labels = vertex_labels.copy()
        before_edge_labels = edge_labels.copy()
        before_edge_arrows = edge_arrows.copy()

        add_vertex(drag_start)
        add_vertex(end_square)
        add_edge(drag_start, end_square)

        if vertices != before_vertices or edges != before_edges or vertex_labels != before_vertex_labels or edge_labels != before_edge_labels or edge_arrows != before_edge_arrows:
            undo_stack.append((before_vertices, before_edges, before_vertex_labels, before_edge_labels, before_edge_arrows))
            redo_stack.clear()

        selected_square = None

        if drag_started_on_existing_vertex or end_was_existing_vertex:
            selected_vertex = None
            selected_edge = (drag_start, end_square)
        else:
            selected_vertex = drag_start
            selected_edge = None

    else:
        clicked_square = end_square
        clicked_edge = find_edge(event.x, event.y)

        if path_mode and clicked_square in vertices:
            handle_path_vertex_click(clicked_square)

        elif clicked_square in vertices:
            selected_square = None
            selected_edge = None

            if selected_vertex == clicked_square and not rename_mode:
                enter_rename_mode()
            elif selected_vertex == clicked_square and rename_mode:
                rename_mode = False
                root.focus_set()
            else:
                rename_mode = False
                selected_vertex = clicked_square

        elif clicked_edge:
            selected_square = None
            selected_vertex = None

            if selected_edge == clicked_edge and not rename_mode:
                enter_rename_mode()
            elif selected_edge == clicked_edge and rename_mode:
                rename_mode = False
                root.focus_set()
            else:
                rename_mode = False
                selected_edge = clicked_edge

        elif selected_square == clicked_square:
            save_state()
            add_vertex(clicked_square)
            selected_square = None
            selected_vertex = clicked_square
            selected_edge = None

        else:
            selected_square = clicked_square
            selected_vertex = None
            selected_edge = None

        

    drag_start = None
    preview_pos = None
    drag_started_on_existing_vertex = False

    update_name_bar()
    redraw()


# Starts right-click dragging for panning.
def on_pan_start(event):
    global pan_last_x, pan_last_y

    pan_last_x = event.x
    pan_last_y = event.y



# Updates pan offset while right-click dragging.
def on_pan_drag(event):
    global pan_last_x, pan_last_y, offset_x, offset_y

    if pan_last_x is None or pan_last_y is None:
        return

    dx = event.x - pan_last_x
    dy = event.y - pan_last_y

    offset_x += dx
    offset_y += dy

    pan_last_x = event.x
    pan_last_y = event.y

    redraw()



# Ends right-click panning.
def on_pan_end(event):
    global pan_last_x, pan_last_y

    pan_last_x = None
    pan_last_y = None



# Handles two-finger/scroll-wheel panning; Shift scroll moves horizontally.
def on_trackpad_scroll(event):
    global offset_x, offset_y

    # Shift + two-finger scroll usually means horizontal scrolling.
    if event.state & 0x1:
        offset_x += event.delta
    else:
        offset_y += event.delta

    redraw()

# Mouse and keyboard event bindings.
canvas.bind("<Motion>", on_mouse_move)
canvas.bind("<ButtonPress-1>", on_press)
canvas.bind("<B1-Motion>", on_drag)
canvas.bind("<ButtonRelease-1>", on_release)
canvas.bind("<Configure>", lambda event: redraw())
# right-click drag to pan around the graph
canvas.bind("<ButtonPress-3>", on_pan_start)
canvas.bind("<B3-Motion>", on_pan_drag)
canvas.bind("<ButtonRelease-3>", on_pan_end)

# laptop trackpad / mouse wheel scrolling
canvas.bind("<MouseWheel>", on_trackpad_scroll)

root.bind("<Key>", on_key)
name_entry.bind("<Return>", apply_name_change)

redraw()
root.mainloop()
