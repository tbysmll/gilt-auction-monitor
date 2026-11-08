"""
chart_style.py - the house style for every chart and the web dashboard, modelled on a sell-side research dashboard.

The charts are "card charts": each image is just the plot, saved as SVG (see FILE_TYPE). Its numbered title, subtitle, source and any note are
written by report.py into the dashboard card around it (and as text above and below it in the README), so the
images stay compact and crisp inside a grid.

Plot style: y-axis numbers on the right, a bottom baseline only, light horizontal gridlines, a small unboxed key
above the plot, each line's latest value in a coloured tag on the right-hand axis, and a gold dot on the latest point.
To change the look of every chart (and the web page's colours) at once, change it in this file only.
"""

import matplotlib.pyplot as plt                    # pyplot creates figures and chart areas
import matplotlib.dates as mdates                  # Formats dates along an axis
from matplotlib import font_manager                # Lets us check which fonts are installed

# ---------------------------------------------------------------------------
# Palette: these five colours (on a white background) are the only ones the charts use
# ---------------------------------------------------------------------------
NAVY = "#002B5C"         # Primary colour: Brent, and the main line on single-series charts
MID_BLUE = "#4F81BD"     # WTI
GOLD = "#C9A227"         # Highlights: today's value
DARK_GREY = "#595959"    # All text, and secondary series (e.g. "one month earlier")
LIGHT_GREY = "#D9D9D9"   # Gridlines and zero lines
WHITE = "#FFFFFF"        # Background

MARKET_COLOURS = {"Brent": NAVY, "WTI": MID_BLUE}  # Each market always gets the same colour, on every chart

# ---------------------------------------------------------------------------
# Size, font and date format
# ---------------------------------------------------------------------------
CARD_SIZE = (5.2, 3.6)   # A half-width dashboard card, in inches
WIDE_SIZE = (10.4, 3.6)  # A full-width card (twice as wide, same height)
FILE_TYPE = "svg"        # SVG stores the shapes themselves, not pixels, so charts stay sharp at any size or zoom
DATE_FORMAT = "%b-%y"    # Dates written like "Nov-26"
FONT_PREFERENCE = ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"]  # First one installed wins; Liberation Sans
                         # is a free Arial look-alike found on Linux (e.g. GitHub's servers); DejaVu Sans comes with matplotlib

# ---------------------------------------------------------------------------
# Layout of the plot inside each image, as fractions (0 = left/bottom edge, 1 = right/top edge)
# ---------------------------------------------------------------------------
PLOT_LEFT = 0.05         # A small left margin (the y-axis numbers are on the right), just wide enough for the first date label
PLOT_RIGHT = 0.87        # Room on the right for the y-axis numbers and the value tags
PLOT_TOP = 0.87          # Room above for the key
PLOT_BOTTOM = 0.13       # Room below for the dates


def pick_font():
    """Return the first font in FONT_PREFERENCE that's installed on this computer.

    Takes no inputs. Returns a font name such as "Arial".
    Exists so the same code gives Arial on Windows and the closest match elsewhere, without warnings.
    """
    installed = {font.name for font in font_manager.fontManager.ttflist}  # Names of every font matplotlib can find
    for name in FONT_PREFERENCE:                   # Try each preferred font in order...
        if name in installed:                      # ...and use the first one that's installed
            return name                            # e.g. "Arial"
    return "DejaVu Sans"                           # Always available: it ships with matplotlib


def rc_params():
    """The matplotlib settings that give every chart the house look.

    Takes no inputs. Returns a dictionary of matplotlib settings ("rcParams").
    Used with plt.rc_context(rc_params()), which applies them only while one chart is being drawn.
    """
    return {                                       # Each setting below changes one default of matplotlib
        "font.family": pick_font(),                # Arial (or the nearest installed match)
        "font.size": 10,                           # Text sized to stay readable when a card is shown ~370 px wide
        "text.parse_math": False,                  # Treat $ as a plain dollar sign: otherwise text between two $ signs
                                                   # (e.g. "$/bbl ... $/bbl") is read as a maths formula and garbled
        "text.color": DARK_GREY,                   # Default text colour
        "axes.labelcolor": DARK_GREY,              # Axis label colour
        "axes.edgecolor": DARK_GREY,               # Colour of the bottom baseline
        "axes.linewidth": 0.8,                     # Thin baseline
        "axes.spines.top": False,                  # No border along the top...
        "axes.spines.right": False,                # ...down the right...
        "axes.spines.left": False,                 # ...or down the left: just a bottom baseline
        "axes.grid": True,                         # Gridlines on...
        "axes.grid.axis": "y",                     # ...horizontal only (no vertical gridlines)
        "axes.axisbelow": True,                    # Gridlines drawn behind the data
        "axes.xmargin": 0.01,                      # Lines run almost to the edges of the plot
        "grid.color": LIGHT_GREY,                  # Light grey gridlines
        "grid.linewidth": 0.6,                     # Hairline gridlines
        "xtick.color": DARK_GREY,                  # Tick marks and dates along the bottom
        "xtick.major.size": 3,                     # Short tick marks on the dates
        "xtick.labelsize": 9,                      # Date labels
        "ytick.color": DARK_GREY,                  # The y-axis numbers
        "ytick.left": False,                       # No y-axis ticks on the left...
        "ytick.labelleft": False,                  # ...or numbers on the left...
        "ytick.right": True,                       # ...they go on the right instead,
        "ytick.labelright": True,                  # ...where a reader's eye ends up at the latest data
        "ytick.major.size": 0,                     # No tick marks (the gridlines do that job)
        "ytick.labelsize": 9,                      # Axis numbers
        "lines.linewidth": 1.6,                    # Fairly thin lines
        "legend.frameon": False,                   # The key never has a box around it
        "legend.fontsize": 9,                      # Key text
        "figure.facecolor": WHITE,                 # White figure background
        "axes.facecolor": WHITE,                   # White chart-area background
        "savefig.facecolor": WHITE,                # Saved files have a white background, never transparent
        "svg.fonttype": "path",                    # Save lettering as drawn shapes, so charts look identical on every
                                                   # computer, even one without Arial
        "svg.hashsalt": "oil-curve-tracker",       # Fixed internal IDs (instead of random ones), so an unchanged chart
                                                   # produces an identical file and Git sees no change
    }


def new_figure(nrows=1, ncols=1, size=CARD_SIZE, **kwargs):
    """Create a blank figure at a card size, with the plot placed in the house margins.

    nrows, ncols -- how many chart areas, in rows and columns (most charts have one)
    size         -- CARD_SIZE for a half-width card, WIDE_SIZE for a full-width one
    **kwargs     -- any extra plt.subplots options, e.g. sharey=True
    Returns (fig, axes): the figure and its chart area(s).
    """
    fig, axes = plt.subplots(nrows, ncols, figsize=size, **kwargs)  # The figure and its chart area(s)
    fig.subplots_adjust(left=PLOT_LEFT, right=PLOT_RIGHT, top=PLOT_TOP, bottom=PLOT_BOTTOM,  # Fixed margins...
                        wspace=0.12, hspace=0.30)  # ...and spacing between panels
    return fig, axes                               # Hand them back


def format_dates(ax):
    """Write the dates along the bottom of a time-series chart like "Nov-26".

    ax -- the chart area
    Returns nothing.
    """
    ax.xaxis.set_major_formatter(mdates.DateFormatter(DATE_FORMAT))  # e.g. "Nov-26"


def add_key(ax):
    """Show a small key (no box) just above the top-left of the plot, one item per labelled line, side by side.

    ax -- the chart area; its lines must have been drawn with label="..."
    Returns nothing.
    """
    handles, labels = ax.get_legend_handles_labels()  # The lines that were given a label
    ax.legend(handles, labels, loc="lower left", bbox_to_anchor=(0, 1.0),  # Anchored at the plot's top-left corner, sitting above it
              ncol=len(labels), handlelength=1.6, columnspacing=1.4, borderaxespad=0.2)  # All on one row, compact


def mark_latest(ax, x, y, text, dx=6, dy=6, ha="left"):
    """A small gold dot on a point with its number beside it (used on the curve chart for today's M1 price).

    ax       -- the chart area
    x, y     -- the point
    text     -- the number to show, e.g. "104.77"
    dx, dy   -- where to put the number relative to the dot, in points
    ha       -- "left" puts the number to the right of that spot, "right" to the left
    Returns nothing.
    """
    ax.scatter([x], [y], s=22, color=GOLD, zorder=5)  # The gold dot, drawn on top of the line (zorder)
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points",  # The number, nudged off the dot
                va="center", ha=ha, fontsize=9, fontweight="bold", color=DARK_GREY)  # Bold grey text


def mark_last(ax, x, y):
    """A small gold dot on a line's latest point.

    ax   -- the chart area
    x, y -- the latest point (last date, last value)
    Returns nothing.
    """
    ax.scatter([x], [y], s=18, color=GOLD, zorder=5)  # Gold dot, drawn on top of the line


def value_tag(ax, y, text, colour, dy=0):
    """A coloured tag on the right-hand axis showing a line's latest value, like a market terminal or bank chart.

    ax     -- the chart area
    y      -- the value, which sets the tag's height on the axis
    text   -- what the tag says, e.g. "+11.71"
    colour -- the line's colour (the tag is filled with it, with white text)
    dy     -- optional nudge up (+) or down (-) in points, from label_offsets(), to stop tags overlapping
    Returns nothing.
    """
    ax.annotate(text, xy=(1, y), xycoords=("axes fraction", "data"),  # At the right-hand edge, at the value's height
                xytext=(3, dy), textcoords="offset points",  # Just outside the plot, over the axis numbers
                va="center", ha="left", fontsize=8.5, fontweight="bold", color=WHITE,  # Bold white text...
                bbox={"boxstyle": "square,pad=0.25", "facecolor": colour, "edgecolor": "none"},  # ...on a box in the line's colour
                annotation_clip=False)             # Allow it to sit outside the plot area


def label_offsets(ax, ys, min_gap=11):
    """Work out how far to nudge value tags so that none sit closer than `min_gap` points apart.

    ax      -- the chart area (its scale is needed to turn $/bbl into distance on the page)
    ys      -- the heights of the tags in data units, e.g. [11.71, 8.75]
    min_gap -- the smallest allowed vertical gap between tags, in points
    Returns a list of nudges in points, one per tag, in the same order as ys (0 = no nudge needed).
    """
    to_points = 72 / ax.figure.dpi                 # 72 points per inch; dpi is pixels per inch, so this turns pixels into points
    heights = [ax.transData.transform((0, y))[1] * to_points for y in ys]  # Each tag's height on the page, in points
    order = sorted(range(len(ys)), key=lambda i: heights[i])  # Tag numbers from lowest to highest on the page
    placed = list(heights)                         # Where each tag will end up; starts where it would naturally sit
    for previous, current in zip(order, order[1:]):  # Walk up the tags, each one with the one just below it
        if placed[current] - placed[previous] < min_gap:  # Too close to the one below...
            placed[current] = placed[previous] + min_gap  # ...so push it up to exactly min_gap above
    return [placed[i] - heights[i] for i in range(len(ys))]  # Nudge = where it ends up minus where it started


def hide_numbers_under_tags(ax, ys, nudges=None, gap=10):
    """Hide any right-hand axis number that a value tag would sit on top of, so tags never cover half a number.

    ax     -- the chart area (call this after its lines are drawn)
    ys     -- the tags' values in data units, e.g. [105.95, 97.92]
    nudges -- the same nudges (in points) given to value_tag(), if any; None means no nudges
    gap    -- how close, in points, an axis number can be to a tag before it's hidden
    Returns nothing.
    """
    nudges = nudges or [0] * len(ys)               # No nudges given: treat every nudge as 0
    ax.set_ylim(ax.get_ylim())                     # Freeze the scale, so the axis numbers can't move after this check
    to_points = 72 / ax.figure.dpi                 # Turns pixels into points (72 points per inch)
    tags = [ax.transData.transform((0, y))[1] * to_points + dy for y, dy in zip(ys, nudges)]  # Each tag's height on the page
    for tick, value in zip(ax.yaxis.get_major_ticks(), ax.get_yticks()):  # Each axis number and the value it shows
        height = ax.transData.transform((0, value))[1] * to_points  # That number's height on the page
        if any(abs(height - tag) < gap for tag in tags):  # A tag sits on (or very near) it...
            tick.label2.set_visible(False)         # ...so hide it (label2 is the right-hand number)


def save(fig, path):
    """Save the figure in the house file type (SVG), with a white background, then close it.

    fig  -- the finished figure
    path -- where to save it, without a file ending, e.g. docs/charts/curves (".svg" is added here)
    Returns the full path, e.g. docs/charts/curves.svg.
    No "tight" trimming, so every card chart comes out at exactly the same size.
    """
    path = path.with_suffix(f".{FILE_TYPE}")     # Add the file ending, e.g. curves -> curves.svg
    fig.savefig(path, format=FILE_TYPE, facecolor=WHITE,  # Write the file...
                metadata={"Date": None})           # ...without a date stamp inside, so unchanged charts stay identical
    plt.close(fig)                                 # Free the memory
    return path                                    # Tell the caller where it went
