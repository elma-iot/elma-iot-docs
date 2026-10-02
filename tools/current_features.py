"""Reviewed articles for the current Windows/device telemetry workspace."""

BASE = "/elma-iot-docs"


def link(locale, topic, label):
    return f'<a href="{BASE}/{locale}/{topic.replace(".", "/")}/">{label}</a>'


def figure(name, alt, caption):
    return (f'<figure class="feature-figure"><img src="{BASE}/assets/illustrations/{name}.svg" '
            f'alt="{alt}" loading="lazy"><figcaption>{caption}</figcaption></figure>')


def body(topic, locale):
    if topic == "workspace":
        return (
            '<h2>Arrange the main pages</h2><p>The Windows menu bar holds Configuration, Logics, Wi-Fi, MQTT, '
            'Compile and flash, Serial Monitor, and Plotter. Drag a page tab along the bar to reorder it. '
            'Drag it away from the main window to open that page in a separate window. The detached window has '
            'its own tab handle at the top and the page content below it.</p>'
            + figure('workspace', 'Diagram of a tab moving from the main menu bar into a separate window and back',
                     'A tab moves between the main window and a separate page window. The highlighted insertion point shows where it will dock.')
            + '<h2>Dock and position a page</h2><ol><li>Hold the tab handle in the floating window and drag it over '
            'the main tab bar.</li><li>Watch the highlighted placement preview, then release at the desired '
            'position.</li><li>To return a page without dragging, select Dock in its floating window or use '
            'View → Workspace tabs → Dock all tabs.</li></ol><p>The short transition indicates where the page '
            'moved. The saved tab order and floating window positions and sizes return after application restart.</p>'
            + '<h2>Recover a layout</h2><p>Use View → Workspace tabs to focus any page, including a floating '
            'one. View → Reset tab layout returns every page to the main window in its default order. Plotter '
            'has separate movable toolbars; use View → Plotter toolbars to restore a hidden toolbar and '
            'View → Reset Plotter view to restore their arrangement. The page layout and Plotter toolbar '
            'layout are saved separately.</p>'
            + '<h2>When a page seems missing</h2><p>First check whether it is on another monitor or behind '
            'the main window. Choose the page under View → Workspace tabs to bring it forward. If a display '
            'was removed or a window is off-screen, reset the tab layout. A floating page should always show '
            'its tab handle above the actual page controls.</p>'
        )
    if topic == "plotter":
        return (
            '<h2>Connect and request samples</h2><p>Choose USB serial and its port and baud rate, or Wi-Fi / IP '
            'and the device address, then Connect. The connection control changes state when connected. The '
            'device collects values from Transfer to Plotter nodes while Logics is playing, keeps a bounded '
            'RAM buffer, and answers Plotter requests. It does not continuously stream chart traffic. '
            'Serial Monitor and Plotter share the serial connection; flashing releases it.</p>'
            + figure('plotter', 'Diagram of two colored measurement curves on one Plotter time axis',
                     'Matching plot names place named series on one time axis; each series can have its own color and Y scale.')
            + '<h2>Read and customize the graph</h2><p>Use Overlay all to put every series on one graph, or '
            'By plot name to separate plots. Each series has a distinct color; temperature starts red. Hover '
            'for a crosshair, intersection circles, and color-matched readings at the selected time. Right-click '
            'a curve or legend for display style, color, thickness, and opacity. Right-click an axis for unit, '
            'range, color, and divisions. These appearance choices survive restart.</p><p>The Display menu includes '
            'solid, dashed, dotted, markers, filled area, gradient area, and steps. Smooth curves are redrawn '
            'for the visible range; smoothing does not create artificial peaks. Markers and grid can be toggled.</p>'
            + '<h2>Explore time and keep history</h2><p>Drag the graph left or right to pan. Use the mouse wheel '
            'over the plot to zoom around the cursor. Drag the range bar to move through recorded session history; '
            'drag its ends to change the visible window. Online returns to the newest samples. The selectable '
            'window spans 30 seconds to 30 minutes in 30-second steps. Zoom-out stops when available data '
            'would occupy less than about 80% of the plot width. Old points are retained during the session '
            'instead of disappearing when the live view advances.</p>'
            + '<h2>Save a PC recording</h2><p>Select the record icon to start an ASCII JSON Lines recording '
            'of newly received samples; its status changes to Recording. Select it again to stop. The adjacent '
            'folder icon opens the destination. The default is beside the application; Tools → Plotter '
            'recording folder changes it. Export CSV writes retained session data separately. The temporary '
            'session history file is removed on normal close; the explicit PC recording remains.</p>'
            + '<h2>If a curve is absent</h2><p>Check that the automation is playing, every Transfer to Plotter '
            'node has a connected numeric or Boolean Value, and the device runs firmware with the request '
            'protocol. For multiple curves, use separate Transfer to Plotter nodes with the same Plot name and '
            'different Series names. If Wi-Fi stops updating, check device reachability and reconnect; if serial '
            'is blank, verify the port and that Serial Monitor or flashing is not holding it. '
            + link(locale, 'logics.telemetry', 'Set up the Logics sampling graph') + '.</p>'
        )
    if topic == "logics.telemetry":
        return (
            '<h2>Build a measurement path</h2><ol><li>Add a numeric or Boolean source such as chip '
            'temperature or Wi-Fi signal strength.</li><li>Connect its output directly to Transfer to Plotter.Value '
            'for five-second sampling, or insert Sampling Interval.Value to choose a cadence from 1 ms to '
            '365 days.</li><li>Add a second Transfer to Plotter node for another value. Give both nodes the '
            'same Plot name and distinct Series names to draw two curves together.</li><li>Start the automation '
            'and connect the Plotter; sampling begins on the device, but transport happens only in response '
            'to a Plotter request.</li></ol>'
            + figure('telemetry', 'Diagram of two sensor sources through sampling intervals into separate plot nodes and external storage',
                     'A Sampling Interval controls collection. Separate destinations can use their own intervals and labels.')
            + '<h2>Names, units, and copied nodes</h2><p>Connecting a recognized measurement suggests a short '
            'Plot name, Series name, and Unit, including through Sampling Interval. Those fields remain '
            'editable. A manually edited field keeps its chosen value when wiring changes. When nodes are '
            'copied without their original source, inherited plot labels are reset until a new source is '
            'connected. Verify names and units after copying or rewiring. Do not combine unrelated units '
            'on one physical Y scale.</p>'
            + '<h2>Store samples on the ESP</h2><p>Add Save Data and connect a value, optionally through its '
            'own Sampling Interval. Save Data writes standard ASCII JSON Lines to mounted external SD or '
            'SDMMC storage, not internal flash. Choose an absolute directory; missing directories are created. '
            'Each line includes the series, numeric value, UTC time, and uptime. Non-ASCII labels are escaped '
            'as JSON Unicode sequences. The device clock must be synchronized; storage or queue errors are '
            'reported by the Plots view. Plotter transfer and external recording are separate destinations.</p>'
            + '<h2>Timing and startup</h2><p>The optional Sample now or Save sample Flow input enables '
            'triggered collection while respecting the configured cadence. Pausing an automation pauses its '
            'sampling; stopping resets its interval. A large stall does not generate a catch-up burst. '
            'Millisecond sampling is best effort and depends on the source, device loop, and storage. After '
            'an abnormal startup restart, saved Logics can retry up to three times before stopping with '
            'a notice. Review any red node validation marker and storage error before restarting the group.</p>'
            + '<h2>Check the result</h2><p>Confirm that the device Plots view appears when Transfer to Plotter '
            'is configured, the Windows Plotter discovers every named series, and the external JSONL files '
            'receive data only when Save Data is present. '
            + link(locale, 'plotter', 'Learn the Plotter controls') + '.</p>'
        )
    return None
