# Windows Game Bar Widget Setup Guide

This guide will help you set up the Network Monitor as a Windows Game Bar widget for real-time in-game network monitoring.

## Prerequisites

1. **Windows 10/11** with Game Bar enabled
2. **Python 3.12+** installed
3. **Updated dependencies** (see Installation section)

## Installation

### 1. Install Dependencies

First, install the required Python package for WebSocket support:

```bash
uv sync
```

Or if using pip:

```bash
pip install aiohttp>=3.9.0
```

### 2. Start the Network Monitor

Run the network test script as usual. The WebSocket server will start automatically:

```bash
python network_test.py
```

You should see output like:
```
WebSocket server started on ws://localhost:8765/ws
Widget available at http://localhost:8765/
Gateway: 192.168.1.1
Comcast first hop: X.X.X.X
Google DNS: 8.8.8.8
```

The network monitor will:
- Continue logging to CSV as before (for ISP reports)
- Generate HTML reports as before
- Additionally broadcast live data to any connected widgets

### 3. Access the Widget

There are two ways to use the widget:

#### Option A: Direct Browser Access (Recommended for Testing)

1. Open your web browser
2. Navigate to: `http://localhost:8765/`
3. You should see the live network monitor updating in real-time

#### Option B: Windows Game Bar Widget (In-Game Overlay)

Windows Game Bar doesn't support custom widgets directly, but you can use it as a pinned browser window:

1. **Open the widget in Microsoft Edge:**
   - Open Microsoft Edge
   - Navigate to: `http://localhost:8765/`
   - Press `F11` for fullscreen mode OR
   - Use "App mode": `edge --app=http://localhost:8765`

2. **Make it Always on Top:**
   - Download a tool like "PowerToys" (free from Microsoft)
   - Enable "Always on Top" feature (Win + Ctrl + T)
   - Pin the Edge widget window on top of your game

3. **Adjust Transparency (Optional):**
   - The widget already has a semi-transparent dark background
   - For more transparency, you can use tools like:
     - **PowerToys FancyZones** - Window management
     - **TranslucentTB** - Transparency control
     - **WindowTop** - Per-window transparency control

#### Option C: OBS Browser Source (For Streamers)

If you use OBS for streaming/recording:

1. In OBS, add a new **Browser Source**
2. Set URL to: `http://localhost:8765/`
3. Set Width: 320, Height: 280
4. Enable "Shutdown source when not visible"
5. Position the source on your game scene

## Widget Features

### Real-Time Metrics Display

The widget shows three network targets:

1. **Gateway** (Blue) - Your local router
2. **First Hop** (Green) - Your ISP's first router
3. **Google DNS** (Orange) - Internet connectivity (8.8.8.8)

For each target, you see:
- **Latency**: Response time in milliseconds
  - Green: Good (<50ms)
  - Orange: Warning (50-100ms)
  - Red: Critical (>100ms)
- **Loss**: Packet loss percentage
  - Dot indicator: Green (0%), Orange (>0%), Red (>5%)
- **Jitter**: Latency variation
  - Green: Good (<10ms)
  - Orange: Warning (10-20ms)
  - Red: Critical (>20ms)

### Visual Alerts

- Cards pulse with red background when packet loss is detected
- Color-coded metrics for quick status assessment
- Real-time updates every 1 second (configurable)

## Customization

### Change Update Frequency

Edit `network_test.py`:

```python
SLEEP_BETWEEN_CYCLES = 0.5  # Update every 500ms instead of 1 second
```

### Change WebSocket Port

Edit `network_test.py`:

```python
WEBSOCKET_PORT = 9000  # Use a different port
```

Then update the widget URL to `http://localhost:9000/`

### Resize the Widget

The widget is responsive and can be resized. For different default sizes, edit `widget_manifest.json`:

```json
"widget": {
    "width": 400,    // Wider display
    "height": 350,   // Taller display
    "resizable": true
}
```

### Adjust Transparency

Edit `gamebar_widget.html`, line 18:

```css
background: rgba(0, 0, 0, 0.75);  /* 0.0 = fully transparent, 1.0 = opaque */
```

Lower values make it more transparent:
- `0.5` - More transparent
- `0.75` - Default (balanced)
- `0.9` - Less transparent

## Usage Tips

### For Gaming

1. **Start before launching game:**
   ```bash
   python network_test.py --duration 7200
   ```
   (Runs for 2 hours)

2. **Position widget in corner** of screen where it won't obstruct gameplay

3. **Watch for patterns:**
   - Red pulses indicate lag spikes
   - High jitter means unstable connection
   - Gateway issues = local network problem
   - First Hop/Google DNS issues = ISP problem

### For Troubleshooting with ISP

1. **Keep CSV logging running** - The widget doesn't replace CSV logs
2. **All existing functionality preserved:**
   - CSV files for historical analysis
   - HTML reports with graphs
   - Command-line output
3. **Share CSV data** with your ISP as proof of connection issues

## Troubleshooting

### Widget shows "Connecting..." forever

- Make sure `python network_test.py` is running
- Check firewall isn't blocking port 8765
- Try accessing `http://localhost:8765/` in a browser first

### Widget shows stale data

- Check console output of `network_test.py` for errors
- Verify WebSocket clients counter increases when opening widget
- Check browser console (F12) for JavaScript errors

### High CPU usage

- Reduce update frequency: increase `SLEEP_BETWEEN_CYCLES`
- Close unused widget instances
- Use lower ping count: `--count 1` instead of 3

### Widget not transparent

- Make sure you're using a modern browser (Edge, Chrome)
- Check if transparency is supported in your configuration
- Try adjusting the RGBA value in the CSS

## Command Line Options

Run the monitor with custom settings:

```bash
# Run for 4 hours with 500ms updates
python network_test.py --duration 14400 --interval 0.5

# High-resolution monitoring (200ms intervals, 1 ping per cycle)
python network_test.py --interval 0.2 --count 1 --timeout-ms 200

# Custom packet size testing
python network_test.py --packet-size 1400
```

All options work with the widget simultaneously!

## Advanced: Multiple Monitors

You can run multiple instances on different ports:

```python
# Instance 1: Edit network_test.py
WEBSOCKET_PORT = 8765

# Instance 2: Copy to network_test2.py and edit
WEBSOCKET_PORT = 8766
```

Then open multiple widgets at different URLs.

## Notes

- The widget auto-reconnects if the network monitor restarts
- All **existing CSV logging remains unchanged**
- HTML reports continue to be generated
- The widget is purely **additive** - no functionality removed
- Widget updates happen in addition to CSV writes (no performance impact)

## Support

If you encounter issues:
1. Check `network_test.py` console output for errors
2. Open browser console (F12) and check for JavaScript errors
3. Verify port 8765 is not in use: `netstat -ano | findstr 8765`
4. Ensure firewall allows Python network access
