# Desktop Shortcut Guide

## What Just Happened

A desktop shortcut called **"Network Monitor"** has been created on your desktop at:
```
C:\Users\fyodorwolf\Desktop\Network Monitor.lnk
```

## How to Use

1. **Double-click the "Network Monitor" shortcut** on your desktop
2. Two windows will open:
   - **Console window** - Shows real-time network data and saves CSV logs
   - **Overlay window** - Live graph widget for gaming

3. **Position the overlay** where you want it on your screen (usually a corner)

4. **Use PowerToys to pin it on top:**
   - Focus the overlay window
   - Press **Win + Ctrl + T**
   - The overlay will now stay on top of your games

5. **Launch your game** and monitor your network!

## What the Shortcut Does

The [launch_monitor.bat](launch_monitor.bat) script:
1. Starts `uv run network_test.py` in a new console window
2. Waits 3 seconds for the WebSocket server to start
3. Opens the widget in Edge app mode at http://localhost:8765/
4. Sets initial window size (400x500) and position (top-left corner)

## Customizing the Overlay Position

Edit [launch_monitor.bat](launch_monitor.bat) line 15 to change where the overlay opens:

```batch
start msedge --app=http://localhost:8765/ --window-size=400,500 --window-position=10,100
```

Change the values:
- `--window-size=WIDTH,HEIGHT` - Adjust overlay size
  - Example: `--window-size=500,600` for larger window
- `--window-position=X,Y` - Screen coordinates (pixels from left, pixels from top)
  - Example: `--window-position=1500,100` for top-right on a 1920px wide screen

## Stopping the Monitor

To stop everything:
1. Close the console window, OR
2. Press **Ctrl+C** in the console window

The overlay will automatically close when the WebSocket server stops.

## Recreating the Shortcut

If you delete the shortcut or want to recreate it:

```powershell
cd C:\Users\fyodorwolf\Code\NetworkTester
powershell -ExecutionPolicy Bypass -File create_shortcut.ps1
```

## Troubleshooting

### Shortcut doesn't work
- Right-click the shortcut → Properties
- Make sure "Start in" is: `C:\Users\fyodorwolf\Code\NetworkTester`
- Make sure "Target" is: `C:\Users\fyodorwolf\Code\NetworkTester\launch_monitor.bat`

### Overlay doesn't open
- Wait 5 seconds after double-clicking (server needs time to start)
- Check if the console window shows "WebSocket server started"
- Manually open http://localhost:8765/ in a browser

### Overlay won't stay on top of game
- Install PowerToys: `winget install Microsoft.PowerToys`
- Enable "Always on Top" feature in PowerToys settings
- Press **Win + Ctrl + T** with overlay focused

## Tips

- **Run before gaming**: Start the monitor a minute before launching your game to collect baseline data
- **Resize as needed**: The overlay is fully responsive - make it as small or large as you want
- **CSV logs preserved**: All data is still being logged to `network_test.csv` for ISP reports
- **Multiple monitors**: Position the overlay on a secondary monitor if you have one
