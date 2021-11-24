"""Custom widget definitions and UI components assembly"""

from math import ceil
from operator import floordiv, sub
from shutil import get_terminal_size

import urwid

from .config import expand_key, _nav, nav
from ..image import TermImage


_command = urwid.Widget._command_map._command_defaults.copy()
for action, (key, _) in _nav.items():
    val = _command.pop(key)
    _command[nav[action][0]] = val
urwid.Widget._command_map._command = _command


class GridListBox(urwid.ListBox):
    def __init__(self, grid):
        self.__grid = grid
        self.__prev_ncell = 1

        return super().__init__(self.__grid_contents((grid.cell_width,)))

    def rows(self, size, focus=False):
        return self.__grid.rows(size[:1], focus)

    def render(self, size, focus=False):
        # 0, if size[0] < cell_width
        ncell = sum(
            map(
                floordiv,
                # No of whole (cell_width + h_sep), columns left after last sep
                divmod(size[0], self.__grid.cell_width + self.__grid.h_sep),
                # if one cell_width can fit into the remaining space
                (1, self.__grid.cell_width),
            )
        )

        if (
            not (ncell or self.__prev_ncell)  # Previously and currently < cell_width
            or ncell != self.__prev_ncell
        ):
            # When maxcol < cell_width, the grid contents are not `Columns` widgets.
            # Instead, they're what would normally be the contents of the `Columns`.
            if ncell and self.__prev_ncell:
                col_focus_position = self.focus.focus_position

            self.body[:] = self.__grid_contents(size[:1])

            if ncell and self.__prev_ncell:  # Same as above
                self.focus.focus_position = min(
                    len(self.focus.contents) - 1, col_focus_position
                )
            self.__prev_ncell = ncell

        return super().render(size, focus)

    def __grid_contents(self, size):
        contents = [
            content[0] if isinstance(content[0], urwid.Divider)
            # `.original_widget` gets rid of an unnecessary padding
            else content[0].original_widget
            for content in self.__grid.get_display_widget(size).contents
        ]
        for content in contents:
            if not isinstance(content, urwid.Divider):
                content._selectable = True

        return contents


class Image(urwid.Widget):
    _sizing = frozenset(["box"])
    _selectable = True

    def __init__(self, image: TermImage):
        self._image = image

    def keypress(self, size, key):
        return key

    def rows(self, size, focus=False):
        # Incompetent implementation due to the lack of maxrows
        size = self._image._valid_size(
            size[0],
            None,
            maxsize=get_terminal_size(),
            ignore_oversize=True,  # For the sake of vertically-oriented images
        )
        rows = ceil(size[1] / 2)
        return rows

    def render(self, size, focus=False):
        image = self._image
        if len(size) == 1:
            size = image._valid_size(
                None,
                None,
                maxsize=(size[0], get_terminal_size()[1]),
            )
            size = (size[0], ceil(size[1] / 2))
        image._size = image._valid_size(None, None, maxsize=size)
        return ImageCanvas(str(image).encode().split(b"\n"), size, image._size)


class ImageCanvas(urwid.Canvas):
    def __init__(self, lines, size, image_size):
        super().__init__()
        self.size = size
        self.lines = lines
        self.__image_size = image_size[0], ceil(image_size[1] / 2)

    def cols(self):
        return self.size[0]

    def rows(self):
        return self.size[1]

    def content(self, trim_left=0, trim_top=0, cols=None, rows=None, attr_map=None):
        diff_x, diff_y = map(sub, self.size, self.__image_size)
        pad_up = diff_y // 2
        pad_down = diff_y - pad_up
        pad_left = diff_x // 2
        pad_right = diff_x - pad_left

        cols = cols or self.cols()
        rows = rows or self.rows()

        fill = b" " * cols
        pad_left = b" " * pad_left
        pad_right = b" " * pad_right

        # Upper padding reduces when the top is trimmed
        for _ in range(pad_up - trim_top):
            yield [(None, "U", fill)]

        # If top is not trimmed (_trim_top_ == 0), render all lines
        # If top is trimmed (_trim_top_ > 0),
        # - and _rows_ > _pad_down_, render the last (_rows_ - _pad_down_) lines
        # - and _rows_ <= _pad_down_, do not render any line (i.e lines[len:])
        for line in self.lines[
            trim_top and (-max(0, rows - pad_down) or len(self.lines)) :
        ]:
            yield [(None, "U", pad_left + line + pad_right)]

        # render full lower padding if _rows_ >= _pad_down_,
        # otherwise only _rows_ rows of padding
        for _ in range(min(rows, pad_down)):
            yield [(None, "U", fill)]


class LineSquare(urwid.LineBox):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        # Prevents `Image.rows()` from being called,
        # in order to get the correct no of rows for a `<LinesSquare <Image>>` widget
        original_middle = self._wrapped_widget.contents[1]
        new_middle = LineSquareMiddleColumns(
            [x[0] for x in original_middle[0].contents],
            box_columns=(0, 2),
            focus_column=original_middle[0].focus_position,
        )
        new_middle.contents[0] = (new_middle.contents[0][0], ("given", 1, True))
        new_middle.contents[2] = (new_middle.contents[2][0], ("given", 1, True))
        self._wrapped_widget.contents[1] = (new_middle, original_middle[1])

    def rows(self, size, focus=False):
        return ceil(size[0] / 2)

    def render(self, size, focus=False):
        return super().render((size[0], ceil(size[0] / 2)), focus)


# To prevent `Image.rows()` from being called,
# in order to get the correct no of rows for a `<LinesSquare <Image>>` widget
class LineSquareMiddleColumns(urwid.Columns):
    def rows(self, size, focus=False):
        return ceil(size[0] / 2) - 2


class MenuEntry(urwid.Text):
    _selectable = True

    def keypress(self, size, key):
        return key


class MenuListBox(urwid.ListBox):
    def keypress(self, size, key):
        ret = super().keypress(size, key)
        return key if any(key == v[0] for v in nav.values()) else ret


class NoSwitchColumns(urwid.Columns):
    _command_map = urwid.ListBox._command_map.copy()
    for key in (nav["Left"][0], nav["Right"][0]):
        _command_map._command.pop(key)


_placeholder = urwid.SolidFill(" ")
_placeholder._selectable = True  # Prevents _image_box_ from being un-selectable
menu = MenuListBox(urwid.SimpleFocusListWalker([]))
image_grid = urwid.GridFlow(
    [_placeholder],
    30,
    2,
    1,
    "left",
)
image_box = urwid.LineBox(_placeholder, "Image", "left")
image_grid_box = urwid.LineBox(urwid.Padding(GridListBox(image_grid)), "Image", "left")
view = urwid.AttrMap(
    image_box,
    "unfocused box",
    "focused box",
)
viewer = NoSwitchColumns(
    [
        (
            20,
            urwid.AttrMap(
                urwid.LineBox(menu, "List", "left"), "unfocused box", "focused box"
            ),
        ),
        view,
    ]
)
banner = urwid.LineBox(
    urwid.AttrMap(
        urwid.Filler(urwid.Text(("red on green", "Term-Img"), "center")),
        "red on green",
    ),
)
pile = urwid.Pile([(4, banner), viewer], 1)

info_bar = urwid.Filler(urwid.Text(""))
key_bar = urwid.Filler(urwid.Text([[("mine", "cool"), " "]] * 19 + [("mine", "cool")]))
expand = urwid.Filler(urwid.Text(f"\u25B2 [{expand_key[0]}]", align="right"), "middle")
bottom_bar = urwid.Columns([key_bar, (5, expand)], 2)

main = urwid.Pile([pile, (1, info_bar), (1, bottom_bar)], 0)