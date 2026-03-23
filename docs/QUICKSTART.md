# Quick Start - Windows Game Bar Overlay

## Desktop Shortcut (Easiest Way!)

A desktop shortcut has been created for you! Just:
1. **Double-click "Network Monitor"** on your desktop
2. Wait for both windows to open (console + overlay)
3. Position the overlay where you want it
4. Install PowerToys and press **Win + Ctrl + T** to pin overlay on top
5. Launch your game!

See [DESKTOP_SHORTCUT.md](DESKTOP_SHORTCUT.md) for customization options.

---

## Manual Setup (If You Prefer)

### Step 1: Install Required Package

Open PowerShell or Command Prompt in this folder and run:

```powershell
uv sync
```

Or if you prefer pip:

```powershell
pip install aiohttp
```

## Step 2: Start the Network Monitor

```powershell
python network_test.py
```

You should see:
```
WebSocket server started on ws://localhost:8765/ws
Widget available at http://localhost:8765/
```

## Step 3: Open the Overlay

### Quick Test (Recommended First)

Open your web browser and go to:
```
http://localhost:8765/
```

You should see a dark, semi-transparent widget with a **live graph** showing the last 60 seconds of network latency! This lets you see patterns forming before lag spikes happen.

### For In-Game Use

1. **Using Microsoft Edge (Built into Windows):**

   Open PowerShell and run:
   ```powershell
   start msedge --app=http://localhost:8765/
   ```

   This opens the widget in a compact window mode without browser UI.

2. **Make it Always-On-Top:**

   - Download **PowerToys** from Microsoft Store (free)
   - After installing, press **Win + Ctrl + T** with the widget window focused
   - The widget will now stay on top of your game!

3. **Position it:**
   - Drag to a corner of your screen
   - Resize as needed (widget is responsive)

## Step 4: Launch Your Game

The widget will now overlay your game and show a **live scrolling graph** with:
- **Gateway latency** - Your router (Blue line)
- **First Hop latency** - Your ISP (Green line)
- **Google DNS latency** - Internet (Orange line)
- **Current values** - Bottom bar with color coding (Green=good, Orange=warning, Red=critical)
- **60-second history** - See patterns developing over the last minute

## Features

- **Live scrolling graph** - See the last 60 seconds of latency history
- **Pattern recognition** - Spot lag spikes before they happen by seeing trends
- Updates every 1 second
- **All CSV logging still works** (for ISP reports)
- **All HTML reports still work**
- Color-coded current values (Green = good, Orange = warning, Red = bad)
- Auto-reconnects if you restart the monitor
- Hover over graph for exact values at any point

## Adjusting Transparency

Edit [gamebar_widget.html](gamebar_widget.html) line 17:

```css
background: rgba(0, 0, 0, 0.75);
```

Change `0.75` to:
- `0.5` = More transparent (better for seeing through to game)
- `0.9` = Less transparent (easier to read)

Save and refresh the browser!

## Adjusting History Window

To show more or less history, edit [gamebar_widget.html](gamebar_widget.html) line 172:

```javascript
const MAX_DATA_POINTS = 60; // Show last 60 seconds
```

Change to:
- `120` = Show last 2 minutes (see longer patterns)
- `30` = Show last 30 seconds (faster scrolling, more recent focus)

## That's It!

You now have a live network monitoring overlay. Perfect for:
- Tracking lag spikes while gaming
- Identifying if issues are local (Gateway) or ISP (First Hop)
- Recording data for ISP complaints (CSV still saves everything)

See [GAMEBAR_SETUP.md](GAMEBAR_SETUP.md) for advanced options and troubleshooting.
