# GraphTheoristSketchpad

An interactive graph theory sketchpad built with Python and Tkinter.  
This application allows users to create, edit, visualize, and analyze graphs through a dynamic graphical interface.

---

## Features

### Graph Creation
- Add vertices by clicking grid squares
- Create edges by dragging between vertices
- Prevents duplicate edges
- Dynamic snapping to grid centers

### Selection & Editing
- Select vertices or edges
- Select the entire graph (`Ctrl + A`)
- Delete selected vertices or edges
- Connected edges are automatically removed when deleting a vertex
- Rename vertices and edges directly from the bottom label bar

### Labels
- Vertices default to `\bullet`
- Supports lightweight LaTeX-style labels:
  - Greek letters (`\alpha`, `\beta`, `\theta`, etc.)
  - Subscripts (`v_1`, `x_i`)
  - Colored labels (`\textcolor{blue}{a}`)
- Dynamic grid resizing to fit larger labels

### Navigation
- Zoom in/out
- Pan with mouse/trackpad
- Center view on:
  - Selected vertex
  - Selected edge
  - Entire graph
  - Origin
- Hide/show grid

### Undo / Redo
- Full undo support (`Ctrl + Z`)
- Full redo support (`Ctrl + Shift + Z`)
- Stores:
  - Vertices
  - Edges
  - Labels
  - Directed edge data

### Move Mode
- Press `B` to enter move mode
- Move selected vertices or the whole graph using arrow keys
- Collision-skipping movement for vertices
- Visual move-mode indicator

### Directed Edges
- Convert edges into directed edges
- Flip edge direction
- Convert directed edges back into undirected edges
- Side toolbar for edge controls

### Graph Analysis
- Degree / in-degree / out-degree display
- Adjacency list generation
- Adjacency matrix generation
- Graph property checking:
  - Connected
  - Tree
  - Cycle detection
  - Bipartite
  - Euler path existence

### Shortest Path Visualization
- BFS shortest path algorithm
- Path highlighting between two selected vertices
- Directed edges respected during pathfinding

---

## Technologies Used

- Python
- Tkinter
- Breadth-First Search (BFS)
- Depth-First Search (DFS)

---

## Controls

| Action | Shortcut |
|---|---|
| Undo | `Ctrl + Z` |
| Redo | `Ctrl + Shift + Z` |
| Select All | `Ctrl + A` |
| Delete Selection | `Backspace` / `Delete` |
| Move Mode | `B` |
| Center View | `G` |
| Hide Grid | `H` |
| Zoom In | `Ctrl + =` |
| Zoom Out | `Ctrl + -` |
| Cancel Path/Move Mode | `Esc` |

---

## How It Works

### Graph Representation
- Vertices are stored as coordinate tuples:
```python
(30, 30)
```

- Edges are stored as tuples of vertices:
```python
((30, 30), (90, 30))
```

- Labels and edge directions are stored using dictionaries:
```python
vertex_labels
edge_labels
edge_arrows
```

### Dynamic Grid
The application dynamically resizes grid columns to fit larger labels.  
Column widths are calculated using measured text width, and vertices/edges are drawn using adjusted positions.

### Shortest Path
The shortest-path tool uses Breadth-First Search (BFS).  
The algorithm explores vertices layer-by-layer using a queue (`collections.deque`) and reconstructs the shortest path using a previous-vertex dictionary.

---

## Running the Application

### Requirements
- Python 3.x

### Run
```bash
python Sketchpad.py
```

---

## Future Improvements

Potential future additions:
- Full LaTeX/TikZ export
- Graph saving/loading
- Additional graph algorithms
- Improved LaTeX rendering
- Multiple graph tabs
- Better styling/themes

---

## Author

Created by Allen Peregrino.
