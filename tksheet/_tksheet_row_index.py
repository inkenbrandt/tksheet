from ._tksheet_vars import *
from ._tksheet_other_classes import *

from collections import defaultdict, deque
from itertools import islice, repeat, accumulate, chain
from math import floor, ceil
from tkinter import ttk
import bisect
import csv as csv_module
import io
import pickle
import re
import tkinter as tk
import zlib
# for mac bindings
from platform import system as get_os


class RowIndex(tk.Canvas):
    def __init__(self,
                 parentframe = None,
                 main_canvas = None,
                 header_canvas = None,
                 max_rh = None,
                 max_row_width = None,
                 row_index_align = None,
                 row_index_width = None,
                 row_index_background = None,
                 row_index_border_color = None,
                 row_index_grid_color = None,
                 row_index_foreground = None,
                 row_index_select_background = None,
                 row_index_select_foreground = None,
                 row_index_select_row_bg = "#5f6368",
                 row_index_select_row_fg = "white",
                 drag_and_drop_color = None,
                 resizing_line_color = None,
                 row_drag_and_drop_perform = True,
                 measure_subset_index = True,
                 auto_resize_width = True):
        tk.Canvas.__init__(self,
                           parentframe,
                           height = None,
                           background = row_index_background,
                           highlightthickness = 0)
        self.parentframe = parentframe
        self.row_drag_and_drop_perform = row_drag_and_drop_perform
        self.beingDrawnSelRect = None
        self.beingDrawnSelBorder = None
        self.extra_motion_func = None
        self.extra_b1_press_func = None
        self.extra_b1_motion_func = None
        self.extra_b1_release_func = None
        self.extra_rc_func = None
        self.selection_binding_func = None
        self.shift_selection_binding_func = None
        self.drag_selection_binding_func = None
        self.ri_extra_drag_drop_func = None
        self.extra_double_b1_func = None
        self.new_row_width = 0
        if row_index_width is None:
            self.set_width(100)
            self.default_width = 100
        else:
            self.set_width(row_index_width)
            self.default_width = row_index_width
        self.max_rh = float(max_rh)
        self.max_row_width = float(max_row_width)
        self.MT = main_canvas         # is set from within MainTable() __init__
        self.CH = header_canvas      # is set from within MainTable() __init__
        self.TL = None                # is set from within TopLeftRectangle() __init__
        self.text_color = row_index_foreground
        self.grid_color = row_index_grid_color
        self.row_index_border_color = row_index_border_color
        self.selected_cells_background = row_index_select_background
        self.selected_cells_foreground = row_index_select_foreground
        self.selected_rows_bg = row_index_select_row_bg
        self.selected_rows_fg = row_index_select_row_fg
        self.row_index_background = row_index_background
        self.drag_and_drop_color = drag_and_drop_color
        self.resizing_line_color = resizing_line_color
        self.align = row_index_align
        self.highlighted_cells = {}
        self.drag_and_drop_enabled = False
        self.dragged_row = None
        self.width_resizing_enabled = False
        self.height_resizing_enabled = False
        self.double_click_resizing_enabled = False
        self.row_selection_enabled = False
        self.rc_insert_row_enabled = False
        self.rc_delete_row_enabled = False
        self.visible_row_dividers = []
        self.row_width_resize_bbox = tuple()
        self.rsz_w = None
        self.rsz_h = None
        self.currently_resizing_width = False
        self.currently_resizing_height = False
        self.measure_subset_index = measure_subset_index
        self.auto_resize_width = auto_resize_width
        self.bind("<Motion>", self.mouse_motion)
        self.bind("<ButtonPress-1>", self.b1_press)
        self.bind("<Shift-ButtonPress-1>",self.shift_b1_press)
        self.bind("<B1-Motion>", self.b1_motion)
        self.bind("<ButtonRelease-1>", self.b1_release)
        self.bind("<Double-Button-1>", self.double_b1)
        self.bind("<MouseWheel>", self.mousewheel)

    def basic_bindings(self, enable = True):
        if enable:
            self.bind("<Motion>", self.mouse_motion)
            self.bind("<ButtonPress-1>", self.b1_press)
            self.bind("<B1-Motion>", self.b1_motion)
            self.bind("<ButtonRelease-1>", self.b1_release)
            self.bind("<Double-Button-1>", self.double_b1)
            self.bind("<MouseWheel>", self.mousewheel)
            self.bind(get_rc_binding(), self.rc)
        else:
            self.unbind("<Motion>")
            self.unbind("<ButtonPress-1>")
            self.unbind("<B1-Motion>")
            self.unbind("<ButtonRelease-1>")
            self.unbind("<Double-Button-1>")
            self.unbind("<MouseWheel>")
            self.unbind(get_rc_binding())

    def mousewheel(self, event = None):
        if event.num == 5 or event.delta == -120:
            self.yview_scroll(1, "units")
            self.MT.yview_scroll(1, "units")
        if event.num == 4 or event.delta == 120:
            if self.canvasy(0) <= 0:
                return
            self.yview_scroll( - 1, "units")
            self.MT.yview_scroll( - 1, "units")
        self.MT.main_table_redraw_grid_and_text(redraw_row_index = True)

    def set_width(self, new_width, set_TL = False):
        self.current_width = new_width
        self.config(width = new_width)
        if set_TL:
            self.TL.set_dimensions(new_w = new_width)
        try:
            self.MT.recreate_all_selection_boxes()
        except:
            pass

    def enable_bindings(self, binding):
        if binding == "row_width_resize":
            self.width_resizing_enabled = True
        elif binding == "row_height_resize":
            self.height_resizing_enabled = True
        elif binding == "double_click_row_resize":
            self.double_click_resizing_enabled = True
        elif binding == "row_select":
            self.row_selection_enabled = True
        elif binding == "drag_and_drop":
            self.drag_and_drop_enabled = True
        elif binding == "rc_delete_row":
            self.rc_delete_row_enabled = True
            self.ri_rc_popup_menu.entryconfig("Delete Rows", state = "normal")
        elif binding == "rc_insert_row":
            self.rc_insert_row_enabled = True
            self.ri_rc_popup_menu.entryconfig("Insert Row", state = "normal")
        
    def disable_bindings(self, binding):
        if binding == "row_width_resize":
            self.width_resizing_enabled = False
        elif binding == "row_height_resize":
            self.height_resizing_enabled = False
        elif binding == "double_click_row_resize":
            self.double_click_resizing_enabled = False
        elif binding == "row_select":
            self.row_selection_enabled = False
        elif binding == "drag_and_drop":
            self.drag_and_drop_enabled = False
        elif binding == "rc_delete_row":
            self.rc_delete_row_enabled = False
            self.ri_rc_popup_menu.entryconfig("Delete Rows", state = "disabled")
        elif binding == "rc_insert_row":
            self.rc_delete_row_enabled = False
            self.ri_rc_popup_menu.entryconfig("Insert Row", state = "disabled")

    def check_mouse_position_height_resizers(self, x, y):
        ov = None
        for x1, y1, x2, y2 in self.visible_row_dividers:
            if x >= x1 and y >= y1 and x <= x2 and y <= y2:
                ov = self.find_overlapping(x1, y1, x2, y2)
                break
        return ov

    def rc(self, event):
        self.focus_set()
        if self.MT.identify_row(y = event.y, allow_end = False) is None:
            self.MT.deselect("all")
            if self.MT.rc_popup_menus_enabled:
                self.ri_rc_popup_menu.tk_popup(event.x_root, event.y_root)
        elif self.row_selection_enabled and all(v is None for v in (self.CH.rsz_h, self.CH.rsz_w, self.rsz_h, self.rsz_w)):
            r = self.MT.identify_row(y = event.y)
            if r < len(self.MT.row_positions) - 1:
                if self.MT.is_row_selected(r) and self.MT.rc_popup_menus_enabled:
                    self.ri_rc_popup_menu.tk_popup(event.x_root, event.y_root)
                else:
                    if self.MT.single_selection_enabled and self.MT.rc_select_enabled:
                        self.select_row(r, redraw = True)
                    elif self.MT.toggle_selection_enabled and self.MT.rc_select_enabled:
                        self.toggle_select_row(r, redraw = True)
                    if self.MT.rc_popup_menus_enabled:
                        self.ri_rc_popup_menu.tk_popup(event.x_root, event.y_root)
        if self.extra_rc_func is not None:
            self.extra_rc_func(event)

    def shift_b1_press(self, event):
        y = event.y
        r = self.MT.identify_row(y = y)
        if self.drag_and_drop_enabled or self.row_selection_enabled and self.rsz_h is None and self.rsz_w is None:
            if r < len(self.MT.row_positions) - 1:
                r_selected = self.MT.is_row_selected(r)
                if not r_selected and self.row_selection_enabled:
                    r = int(r)
                    currently_selected = self.MT.currently_selected()
                    if currently_selected and currently_selected[0] == "row":
                        min_r = int(currently_selected[1])
                        self.MT.delete_selection_rects(delete_current = False)
                        if r > min_r:
                            self.MT.create_selected(min_r, 0, r + 1, len(self.MT.col_positions) - 1, "rows")
                        elif r < min_r:
                            self.MT.create_selected(r, 0, min_r + 1, len(self.MT.col_positions) - 1, "rows")
                    else:
                        self.select_row(r)
                    self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
                    if self.shift_selection_binding_func is not None:
                        self.shift_selection_binding_func(("shift_select_rows", tuple(sorted(self.MT.get_selected_rows()))))
                elif r_selected:
                    self.dragged_row = r

    def mouse_motion(self, event):
        if not self.currently_resizing_height and not self.currently_resizing_width:
            x = self.canvasx(event.x)
            y = self.canvasy(event.y)
            mouse_over_resize = False
            if self.height_resizing_enabled and not mouse_over_resize:
                ov = self.check_mouse_position_height_resizers(x, y)
                if ov is not None:
                    #tgs = next(itm for itm in ov if "h" == self.gettags(itm))
                    for itm in ov:
                        tgs = self.gettags(itm)
                        if "h" == tgs[0]:
                            break
                    r = int(tgs[1])
                    self.config(cursor = "sb_v_double_arrow")
                    self.rsz_h = r
                    mouse_over_resize = True
                else:
                    self.rsz_h = None
            if self.width_resizing_enabled and not mouse_over_resize:
                try:
                    x1, y1, x2, y2 = self.row_width_resize_bbox[0], self.row_width_resize_bbox[1], self.row_width_resize_bbox[2], self.row_width_resize_bbox[3]
                    if x >= x1 and y >= y1 and x <= x2 and y <= y2:
                        self.config(cursor = "sb_h_double_arrow")
                        self.rsz_w = True
                        mouse_over_resize = True
                    else:
                        self.rsz_w = None
                except:
                    self.rsz_w = None
            if not mouse_over_resize:
                self.MT.reset_mouse_motion_creations()
        if self.extra_motion_func is not None:
            self.extra_motion_func(event)
        
    def b1_press(self, event = None):
        self.focus_set()
        self.MT.unbind("<MouseWheel>")
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        if self.check_mouse_position_height_resizers(x, y) is None:
            self.rsz_h = None
        if not x >= self.row_width_resize_bbox[0] and y >= self.row_width_resize_bbox[1] and x <= self.row_width_resize_bbox[2] and y <= self.row_width_resize_bbox[3]:
            self.rsz_w = None
        if self.height_resizing_enabled and self.rsz_h is not None:
            self.currently_resizing_height = True
            y = self.MT.row_positions[self.rsz_h]
            line2y = self.MT.row_positions[self.rsz_h - 1]
            x1, y1, x2, y2 = self.MT.get_canvas_visible_area()
            self.create_line(0, y, self.current_width, y, width = 1, fill = self.resizing_line_color, tags = "rhl")
            self.MT.create_line(x1, y, x2, y, width = 1, fill = self.resizing_line_color, tags = "rhl")
            self.create_line(0, line2y, self.current_width, line2y, width = 1, fill = self.resizing_line_color, tags = "rhl2")
            self.MT.create_line(x1, line2y, x2, line2y, width = 1, fill = self.resizing_line_color, tags = "rhl2")
        elif self.width_resizing_enabled and self.rsz_h is None and self.rsz_w == True:
            self.currently_resizing_width = True
            x1, y1, x2, y2 = self.MT.get_canvas_visible_area()
            x = int(event.x)
            if x < self.MT.min_cw:
                x = int(self.MT.min_cw)
            self.new_row_width = x
            self.create_line(x, y1, x, y2, width = 1, fill = self.resizing_line_color, tags = "rwl")
        elif self.MT.identify_row(y = event.y, allow_end = False) is None:
            self.MT.deselect("all")
        elif self.row_selection_enabled and self.rsz_h is None and self.rsz_w is None:
            r = self.MT.identify_row(y = event.y)
            if r < len(self.MT.row_positions) - 1:
                if self.MT.single_selection_enabled:
                    self.select_row(r, redraw = True)
                elif self.MT.toggle_selection_enabled:
                    self.toggle_select_row(r, redraw = True)
        if self.extra_b1_press_func is not None:
            self.extra_b1_press_func(event)
    
    def b1_motion(self, event):
        x1,y1,x2,y2 = self.MT.get_canvas_visible_area()
        if self.height_resizing_enabled and self.rsz_h is not None and self.currently_resizing_height:
            y = self.canvasy(event.y)
            size = y - self.MT.row_positions[self.rsz_h - 1]
            if not size <= self.MT.min_rh and size < self.max_rh:
                self.delete("rhl")
                self.MT.delete("rhl")
                self.create_line(0, y, self.current_width, y, width = 1, fill = self.resizing_line_color, tags = "rhl")
                self.MT.create_line(x1, y, x2, y, width = 1, fill = self.resizing_line_color, tags = "rhl")
        elif self.width_resizing_enabled and self.rsz_w is not None and self.currently_resizing_width:
            evx = event.x
            self.delete("rwl")
            self.MT.delete("rwl")
            if evx > self.current_width:
                x = self.MT.canvasx(evx - self.current_width)
                if evx > self.max_row_width:
                    evx = int(self.max_row_width)
                    x = self.MT.canvasx(evx - self.current_width)
                self.new_row_width = evx
                self.MT.create_line(x, y1, x, y2, width = 1, fill = self.resizing_line_color, tags = "rwl")
            else:
                x = evx
                if x < self.MT.min_cw:
                    x = int(self.MT.min_cw)
                self.new_row_width = x
                self.create_line(x, y1, x, y2, width = 1, fill = self.resizing_line_color, tags = "rwl")
        if self.drag_and_drop_enabled and self.row_selection_enabled and self.rsz_h is None and self.rsz_w is None and self.dragged_row is not None and self.MT.anything_selected(exclude_cells = True, exclude_columns = True):
            y = self.canvasy(event.y)
            if y > 0 and y < self.MT.row_positions[-1]:
                y = event.y
                hend = self.winfo_height()
                if y >= hend - 0:
                    end_row = bisect.bisect_right(self.MT.row_positions, self.canvasy(hend))
                    end_row -= 1
                    if not end_row == len(self.MT.row_positions) - 1:
                        try:
                            self.MT.see(r = end_row, c = 0, keep_yscroll = False, keep_xscroll = True, bottom_right_corner = False, check_cell_visibility = True)
                        except:
                            pass
                elif y <= 0:
                    start_row = bisect.bisect_left(self.MT.row_positions, self.canvasy(0))
                    if y <= -40:
                        start_row -= 3
                    else:
                        start_row -= 2
                    if start_row <= 0:
                        start_row = 0
                    try:
                        self.MT.see(r = start_row, c = 0, keep_yscroll = False, keep_xscroll = True, bottom_right_corner = False, check_cell_visibility = True)
                    except:
                        pass
                selected_rows = sorted(self.MT.get_selected_rows())
                rectw = self.MT.row_positions[selected_rows[-1] + 1] - self.MT.row_positions[selected_rows[0]]
                start = self.canvasy(event.y - int(rectw / 2))
                end = self.canvasy(event.y + int(rectw / 2))
                self.delete("dd")
                self.create_rectangle(0, start, self.current_width - 1, end, fill = self.drag_and_drop_color, outline = self.grid_color, tags = "dd")
                self.tag_raise("dd")
                self.tag_raise("t")
                self.tag_raise("h")
        elif self.MT.drag_selection_enabled and self.row_selection_enabled and self.rsz_h is None and self.rsz_w is None:
            end_row = self.MT.identify_row(y = event.y)
            currently_selected = self.MT.currently_selected()
            if end_row < len(self.MT.row_positions) - 1 and currently_selected:
                if currently_selected[0] == "row":
                    start_row = currently_selected[1]
                    self.MT.delete_selection_rects(delete_current = False)
                    if end_row >= start_row:
                        self.MT.create_selected(start_row, 0, end_row + 1, len(self.MT.col_positions) - 1, "rows")
                        func_event = tuple(range(start_row, end_row + 1))
                    elif end_row < start_row:
                        func_event = tuple(range(end_row, start_row + 1))
                        self.MT.create_selected(end_row, 0, start_row + 1, len(self.MT.col_positions) - 1, "rows")
                    if self.drag_selection_binding_func is not None:
                        self.drag_selection_binding_func(("drag_select_rows", func_event))
            if event.y > self.winfo_height():
                try:
                    self.MT.yview_scroll(1, "units")
                    self.yview_scroll(1, "units")
                except:
                    pass
            elif event.y < 0 and self.canvasy(self.winfo_height()) > 0:
                try:
                    self.yview_scroll(-1, "units")
                    self.MT.yview_scroll(-1, "units")
                except:
                    pass
            self.MT.main_table_redraw_grid_and_text(redraw_header = False, redraw_row_index = True)
        if self.extra_b1_motion_func is not None:
            self.extra_b1_motion_func(event)
            
    def b1_release(self, event = None):
        self.MT.bind("<MouseWheel>", self.MT.mousewheel)
        if self.height_resizing_enabled and self.rsz_h is not None and self.currently_resizing_height:
            self.currently_resizing_height = False
            new_row_pos = self.coords("rhl")[1]
            self.delete("rhl", "rhl2")
            self.MT.delete("rhl", "rhl2")
            size = new_row_pos - self.MT.row_positions[self.rsz_h - 1]
            if size < self.MT.min_rh:
                new_row_pos = ceil(self.MT.row_positions[self.rsz_h - 1] + self.MT.min_rh)
            elif size > self.max_rh:
                new_row_pos = floor(self.MT.row_positions[self.rsz_h - 1] + self.max_rh)
            increment = new_row_pos - self.MT.row_positions[self.rsz_h]
            self.MT.row_positions[self.rsz_h + 1:] = [e + increment for e in islice(self.MT.row_positions, self.rsz_h + 1, len(self.MT.row_positions))]
            self.MT.row_positions[self.rsz_h] = new_row_pos
            self.MT.recreate_all_selection_boxes()
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        elif self.width_resizing_enabled and self.rsz_w is not None and self.currently_resizing_width:
            self.currently_resizing_width = False
            self.delete("rwl")
            self.MT.delete("rwl")
            self.set_width(self.new_row_width, set_TL = True)
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        if self.drag_and_drop_enabled and self.MT.anything_selected(exclude_cells = True, exclude_columns = True) and self.row_selection_enabled and self.rsz_h is None and self.rsz_w is None and self.dragged_row is not None:
            self.delete("dd")
            y = event.y
            r = self.MT.identify_row(y = y)
            orig_selected_rows = self.MT.get_selected_rows()
            if r != self.dragged_row and r is not None and r not in orig_selected_rows and len(orig_selected_rows) != (len(self.MT.row_positions) - 1):
                orig_selected_rows = sorted(orig_selected_rows)
                if len(orig_selected_rows) > 1:
                    orig_min = orig_selected_rows[0]
                    orig_max = orig_selected_rows[1]
                    start_idx = bisect.bisect_left(orig_selected_rows, self.dragged_row)
                    forward_gap = get_index_of_gap_in_sorted_integer_seq_forward(orig_selected_rows, start_idx)
                    reverse_gap = get_index_of_gap_in_sorted_integer_seq_reverse(orig_selected_rows, start_idx)
                    if forward_gap is not None:
                        orig_selected_rows[:] = orig_selected_rows[:forward_gap]
                    if reverse_gap is not None:
                        orig_selected_rows[:] = orig_selected_rows[reverse_gap:]
                rowsiter = orig_selected_rows.copy()
                rm1start = rowsiter[0]
                rm1end = rowsiter[-1] + 1
                rm2start = rm1start + (rm1end - rm1start)
                rm2end = rm1end + (rm1end - rm1start)
                totalrows = len(rowsiter)
                if self.dragged_row < r and r >= len(self.MT.row_positions) - 1:
                    r -= 1
                if self.ri_extra_drag_drop_func is not None:
                    self.ri_extra_drag_drop_func(tuple(orig_selected_rows), int(r))
                r_ = int(r)
                if self.row_drag_and_drop_perform:
                    if rm1end < r:
                        r += 1
                    if rm1start > r:
                        self.MT.data_ref[r:r] = self.MT.data_ref[rm1start:rm1end]
                        self.MT.data_ref[rm2start:rm2end] = []
                        if not isinstance(self.MT.my_row_index, int) and self.MT.my_row_index:
                            try:
                                self.MT.my_row_index[r:r] = self.MT.my_row_index[rm1start:rm1end]
                                self.MT.my_row_index[rm2start:rm2end] = []
                            except:
                                pass
                    else:
                        self.MT.data_ref[r:r] = self.MT.data_ref[rm1start:rm1end]
                        self.MT.data_ref[rm1start:rm1end] = []
                        if not isinstance(self.MT.my_row_index, int) and self.MT.my_row_index:
                            try:
                                self.MT.my_row_index[r:r] = self.MT.my_row_index[rm1start:rm1end]
                                self.MT.my_row_index[rm1start:rm1end] = []
                            except:
                                pass
                rhs = [int(b - a) for a, b in zip(self.MT.row_positions, islice(self.MT.row_positions, 1, len(self.MT.row_positions)))]
                if rm1start > r:
                    rhs[r:r] = rhs[rm1start:rm1end]
                    rhs[rm2start:rm2end] = []
                else:
                    rhs[r:r] = rhs[rm1start:rm1end]
                    rhs[rm1start:rm1end] = []
                self.MT.row_positions = list(accumulate(chain([0], (height for height in rhs))))
                self.MT.deselect("all")
                if (r_ - 1) + totalrows > len(self.MT.row_positions) - 1:
                    new_selected = tuple(range(len(self.MT.row_positions) - 1 - totalrows, len(self.MT.row_positions) - 1))
                    self.MT.create_selected(len(self.MT.row_positions) - 1 - totalrows, 0, len(self.MT.row_positions) - 1, len(self.MT.col_positions) - 1, "rows")
                else:
                    if rm1start > r:
                        new_selected = tuple(range(r_, r_ + totalrows))
                        self.MT.create_selected(r_, 0, r_ + totalrows, len(self.MT.col_positions) - 1, "rows")
                    else:
                        new_selected = tuple(range(r_ + 1 - totalrows, r_ + 1))
                        self.MT.create_selected(r_ + 1 - totalrows, 0, r_ + 1, len(self.MT.col_positions) - 1, "rows")
                self.MT.create_current(int(new_selected[0]), 0, type_ = "row", inside = True)
                if self.MT.undo_enabled:
                    self.MT.undo_storage.append(zlib.compress(pickle.dumps(("move_rows", min(orig_selected_rows), (new_selected[0], new_selected[-1])))))
                self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        self.dragged_row = None
        self.currently_resizing_width = False
        self.currently_resizing_height = False
        self.rsz_w = None
        self.rsz_h = None
        self.mouse_motion(event)
        if self.extra_b1_release_func is not None:
            self.extra_b1_release_func(event)

    def double_b1(self, event = None):
        self.focus_set()
        if self.double_click_resizing_enabled and self.height_resizing_enabled and self.rsz_h is not None and not self.currently_resizing_height:
            row = self.rsz_h - 1
            self.set_row_height(row)
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        elif self.row_selection_enabled and self.rsz_h is None and self.rsz_w is None:
            r = self.MT.identify_row(y = event.y)
            if r < len(self.MT.row_positions) - 1:
                if self.MT.single_selection_enabled:
                    self.select_row(r, redraw = True)
                elif self.MT.toggle_selection_enabled:
                    self.toggle_select_row(r, redraw = True)
        self.mouse_motion(event)
        self.rsz_h = None
        if self.extra_double_b1_func is not None:
            self.extra_double_b1_func(event)

    def highlight_cells(self, r = 0, cells = tuple(), bg = None, fg = None, redraw = False):
        if bg is None and fg is None:
            return
        if cells:
            self.highlighted_cells = {r_: (bg, fg)  for r_ in cells}
        else:
            self.highlighted_cells[r] = (bg, fg)
        if redraw:
            self.MT.main_table_redraw_grid_and_text(False, True)

    def select_row(self, r, redraw = False, keep_other_selections = False):
        r = int(r)
        ignore_keep = False
        if keep_other_selections:
            if self.MT.is_row_selected(r):
                self.MT.create_current(r, 0, type_ = "row", inside = True)
            else:
                ignore_keep = True
        if ignore_keep or not keep_other_selections:
            self.MT.delete_selection_rects()
            self.MT.create_current(r, 0, type_ = "row", inside = True)
            self.MT.create_selected(r, 0, r + 1, len(self.MT.col_positions) - 1, "rows")
        if redraw:
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        if self.selection_binding_func is not None:
            self.selection_binding_func(("select_row", int(r)))

    def toggle_select_row(self, row, add_selection = True, redraw = True, run_binding_func = True, set_as_current = True):
        if add_selection:
            if self.MT.is_row_selected(row):
                self.MT.deselect(r = row, redraw = redraw)
            else:
                self.add_selection(r = row, redraw = redraw, run_binding_func = run_binding_func, set_as_current = set_as_current)
        else:
            if self.MT.is_row_selected(row):
                self.MT.deselect(r = row, redraw = redraw)
            else:
                self.select_row(row, redraw = redraw)

    def add_selection(self, r, redraw = False, run_binding_func = True, set_as_current = True):
        r = int(r)
        if set_as_current:
            create_new_sel = False
            current = self.MT.get_tags_of_current()
            if current:
                if current[0] == "Current_Outside":
                    create_new_sel = True
            self.MT.create_current(r, 0, type_ = "row", inside = True)
            if create_new_sel:
                r1, c1, r2, c2 = tuple(int(e) for e in current[1].split("_") if e)
                self.MT.create_selected(r1, c1, r2, c2, current[2] + "s")
        self.MT.create_selected(r, 0, r + 1, len(self.MT.col_positions) - 1, "rows")
        if redraw:
            self.MT.main_table_redraw_grid_and_text(redraw_header = True, redraw_row_index = True)
        if self.selection_binding_func is not None and run_binding_func:
            self.selection_binding_func(("select_row", int(r)))

    def set_row_height(self, row, height = None, only_set_if_too_small = False, recreate = True, return_new_height = False):
        r_norm = row + 1
        r_extra = row + 2
        min_rh = self.MT.min_rh
        if height is None:
            x = self.MT.txt_measure_canvas.create_text(0, 0, text = "", font = self.MT.my_font)
            itmcon = self.MT.txt_measure_canvas.itemconfig
            itmbbx = self.MT.txt_measure_canvas.bbox
            if self.MT.all_columns_displayed:
                iterable = range(len(self.MT.data_ref[row]))
            else:
                iterable = self.MT.displayed_columns
            new_height = int(min_rh)
            try:
                if isinstance(self.MT.my_row_index[row], str):
                    txt = self.MT.my_row_index[row]
                else:
                    txt = f"{self.MT.my_row_index[row]}"
            except:
                txt = ""
            if txt:
                itmcon(x, text = txt)
                b = itmbbx(x)
                h = b[3] - b[1] + 5
            else:
                h = min_rh
            if h < min_rh:
                h = int(min_rh)
            elif h > self.max_rh:
                h = int(self.max_rh)
            if h > new_height:
                new_height = h
            for cn in iterable:
                try:
                    if isinstance(self.MT.data_ref[row][cn], str):
                        txt = self.MT.data_ref[row][cn]
                    else:
                        txt = f"{self.MT.data_ref[row][cn]}"
                except:
                    txt = ""
                if txt:
                    itmcon(x, text = txt)
                    b = itmbbx(x)
                    h = b[3] - b[1] + 5
                else:
                    h = min_rh
                if h < min_rh:
                    h = int(min_rh)
                elif h > self.max_rh:
                    h = int(self.max_rh)
                if h > new_height:
                    new_height = h
            self.MT.txt_measure_canvas.delete(x)
        else:
            new_height = int(height)
        if new_height < min_rh:
            new_height = int(min_rh)
        elif new_height > self.max_rh:
            new_height = int(self.max_rh)
        if only_set_if_too_small:
            if new_height <= self.MT.row_positions[row + 1] - self.MT.row_positions[row]:
                return self.MT.row_positions[row + 1] - self.MT.row_positions[row]
        if return_new_height:
            return new_height
        else:
            new_row_pos = self.MT.row_positions[row] + new_height
            increment = new_row_pos - self.MT.row_positions[r_norm]
            self.MT.row_positions[r_extra:] = [e + increment for e in islice(self.MT.row_positions, r_extra, len(self.MT.row_positions))]
            self.MT.row_positions[r_norm] = new_row_pos
            if recreate:
                self.MT.recreate_all_selection_boxes()

    def set_height_of_all_rows(self, height = None, only_set_if_too_small = False, recreate = True):
        if height is None:
            self.MT.row_positions = list(accumulate(chain([0], (self.set_row_height(rn, only_set_if_too_small = only_set_if_too_small, recreate = False, return_new_height = True) for rn in range(len(self.MT.data_ref))))))
        else:
            self.MT.row_positions = list(accumulate(chain([0], (height for r in range(len(self.MT.data_ref))))))
        if recreate:
            self.MT.recreate_all_selection_boxes()
        
    def GetNumLines(self, cell):
        if isinstance(cell, str):
            return len(cell.split("\n"))
        else:
            return 1

    def GetLinesHeight(self, cell):
        numlines = self.GetNumLines(cell)
        if numlines > 1:
            return int(self.MT.fl_ins) + (self.MT.xtra_lines_increment * numlines) - 2
        else:
            return int(self.MT.min_rh)

    def redraw_grid_and_text(self, last_row_line_pos, y1, y_stop, start_row, end_row, y2, x1, x_stop, selected_rows, selected_cols, actual_selected_rows):
        try:
            self.configure(scrollregion = (0, 0, self.current_width, last_row_line_pos + 100))
            self.delete("fh", "h", "v", "t", "s") #first horizontal, horizontal, vertical, text, highlights
            self.visible_row_dividers = []
            y = self.MT.row_positions[start_row]
            self.create_line(0, y, self.current_width, y, fill = self.grid_color, width = 1, tags = "fh")
            xend = self.current_width - 6
            self.row_width_resize_bbox = (self.current_width - 5, y1, self.current_width, y2)
            if self.height_resizing_enabled:
                for r in range(start_row + 1, end_row):
                    y = self.MT.row_positions[r]
                    self.visible_row_dividers.append((1, y - 4, xend, y + 4))
                    self.create_line(0, y, self.current_width, y, fill = self.grid_color, width = 1, tags = ("h", f"{r}"))
            else:
                for r in range(start_row + 1, end_row):
                    y = self.MT.row_positions[r]
                    self.create_line(0, y, self.current_width, y, fill = self.grid_color, width = 1, tags = ("h", f"{r}"))
            sb = y2 + 2
            c_2 = self.selected_cells_background if self.selected_cells_background.startswith("#") else Color_Map_[self.selected_cells_background]
            c_3 = self.selected_rows_bg if self.selected_rows_bg.startswith("#") else Color_Map_[self.selected_rows_bg]
            if not self.MT.my_row_index and not isinstance(self.MT.my_row_index, int) and self.auto_resize_width:
                new_w = self.MT.GetTextWidth(f"{end_row}") + 11
                if self.current_width != new_w:
                    self.set_width(new_w, set_TL = True)
            if self.align == "center":
                mw = self.current_width - 5
                x = floor(self.current_width / 2)
                for r in range(start_row, end_row - 1):
                    fr = self.MT.row_positions[r]
                    sr = self.MT.row_positions[r + 1]
                    if sr > sb:
                        sr = sb
                    if r in self.highlighted_cells and r in actual_selected_rows:
                        c_1 = self.highlighted_cells[r][0] if self.highlighted_cells[r][0].startswith("#") else Color_Map_[self.highlighted_cells[r][0]]
                        self.create_rectangle(0,
                                              fr + 1,
                                              self.current_width - 1,
                                              sr,
                                              fill = (f"#{int((int(c_1[1:3], 16) + int(c_3[1:3], 16)) / 2):02X}" +
                                                      f"{int((int(c_1[3:5], 16) + int(c_3[3:5], 16)) / 2):02X}" +
                                                      f"{int((int(c_1[5:], 16) + int(c_3[5:], 16)) / 2):02X}"),
                                              outline = "",
                                              tags = "s")
                        tf = self.selected_rows_fg if self.highlighted_cells[r][1] is None else self.highlighted_cells[r][1]
                    elif r in self.highlighted_cells and (r in selected_rows or selected_cols):
                        c_1 = self.highlighted_cells[r][0] if self.highlighted_cells[r][0].startswith("#") else Color_Map_[self.highlighted_cells[r][0]]
                        self.create_rectangle(0,
                                              fr + 1,
                                              self.current_width - 1,
                                              sr,
                                              fill = (f"#{int((int(c_1[1:3], 16) + int(c_2[1:3], 16)) / 2):02X}" +
                                                      f"{int((int(c_1[3:5], 16) + int(c_2[3:5], 16)) / 2):02X}" +
                                                      f"{int((int(c_1[5:], 16) + int(c_2[5:], 16)) / 2):02X}"),
                                              outline = "",
                                              tags = "s")
                        tf = self.selected_cells_foreground if self.highlighted_cells[r][1] is None else self.highlighted_cells[r][1]
                    elif r in actual_selected_rows:
                        tf = self.selected_rows_fg
                    elif r in selected_rows or selected_cols:
                        tf = self.selected_cells_foreground
                    elif r in self.highlighted_cells:
                        self.create_rectangle(0, fr + 1, self.current_width - 1, sr, fill = self.highlighted_cells[r][0], outline = "", tags = "s")
                        tf = self.text_color if self.highlighted_cells[r][1] is None else self.highlighted_cells[r][1]
                    else:
                        tf = self.text_color
                    try:
                        if isinstance(self.MT.my_row_index, int):
                            if isinstance(self.MT.data_ref[r][self.MT.my_row_index], str):
                                lns = self.MT.data_ref[r][self.MT.my_row_index].split("\n")
                            else:
                                lns = (f"{self.MT.data_ref[r][self.MT.my_row_index]}", )
                        else:
                            if isinstance(self.MT.my_row_index[r], str):
                                lns = self.MT.my_row_index[r].split("\n")
                            else:
                                lns = (f"{self.MT.my_row_index[r]}", )
                    except:
                        lns = (f"{r + 1}", )
                    fl = lns[0]
                    y = fr + self.MT.fl_ins
                    if y + self.MT.half_txt_h > y1:
                        t = self.create_text(x, y, text = fl, fill = tf, font = self.MT.my_font, anchor = "center", tags = "t")
                        wd = self.bbox(t)
                        wd = wd[2] - wd[0]
                        if wd > mw:
                            tl = len(fl)
                            slce = tl - floor(tl * (mw / wd))
                            if slce % 2:
                                slce += 1
                            else:
                                slce += 2
                            slce = int(slce / 2)
                            fl = fl[slce:tl - slce]
                            self.itemconfig(t, text = fl)
                            wd = self.bbox(t)
                            while wd[2] - wd[0] > mw:
                                fl = fl[1: - 1]
                                self.itemconfig(t, text = fl)
                                wd = self.bbox(t)
                    if len(lns) > 1:
                        stl = int((y1 - y) / self.MT.xtra_lines_increment) - 1
                        if stl < 1:
                            stl = 1
                        y += (stl * self.MT.xtra_lines_increment)
                        if y + self.MT.half_txt_h < sr:
                            for i in range(stl, len(lns)):
                                txt = lns[i]
                                t = self.create_text(x, y, text = txt, fill = tf, font = self.MT.my_font, anchor = "center", tags = "t")
                                wd = self.bbox(t)
                                wd = wd[2] - wd[0]
                                if wd > mw:
                                    tl = len(txt)
                                    slce = tl - floor(tl * (mw / wd))
                                    if slce % 2:
                                        slce += 1
                                    else:
                                        slce += 2
                                    slce = int(slce / 2)
                                    txt = txt[slce:tl - slce]
                                    self.itemconfig(t, text = txt)
                                    wd = self.bbox(t)
                                    while wd[2] - wd[0] > mw:
                                        txt = txt[1: - 1]
                                        self.itemconfig(t, text = txt)
                                        wd = self.bbox(t)
                                y += self.MT.xtra_lines_increment
                                if y + self.MT.half_txt_h > sr:
                                    break
            elif self.align == "w":
                mw = self.current_width - 5
                x = 5
                for r in range(start_row, end_row - 1):
                    fr = self.MT.row_positions[r]
                    sr = self.MT.row_positions[r + 1]
                    if sr > sb:
                        sr = sb
                    if r in self.highlighted_cells and r in actual_selected_rows:
                        c_1 = self.highlighted_cells[r][0] if self.highlighted_cells[r][0].startswith("#") else Color_Map_[self.highlighted_cells[r][0]]
                        self.create_rectangle(0,
                                              fr + 1,
                                              self.current_width - 1,
                                              sr,
                                              fill = (f"#{int((int(c_1[1:3], 16) + int(c_3[1:3], 16)) / 2):02X}" +
                                                      f"{int((int(c_1[3:5], 16) + int(c_3[3:5], 16)) / 2):02X}" +
                                                      f"{int((int(c_1[5:], 16) + int(c_3[5:], 16)) / 2):02X}"),
                                              outline = "",
                                              tags = "s")
                        tf = self.selected_rows_fg if self.highlighted_cells[r][1] is None else self.highlighted_cells[r][1]
                    elif r in self.highlighted_cells and (r in selected_rows or selected_cols):
                        c_1 = self.highlighted_cells[r][0] if self.highlighted_cells[r][0].startswith("#") else Color_Map_[self.highlighted_cells[r][0]]
                        self.create_rectangle(0,
                                              fr + 1,
                                              self.current_width - 1,
                                              sr,
                                              fill = (f"#{int((int(c_1[1:3], 16) + int(c_2[1:3], 16)) / 2):02X}" +
                                                      f"{int((int(c_1[3:5], 16) + int(c_2[3:5], 16)) / 2):02X}" +
                                                      f"{int((int(c_1[5:], 16) + int(c_2[5:], 16)) / 2):02X}"),
                                              outline = "",
                                              tags = "s")
                        tf = self.selected_cells_foreground if self.highlighted_cells[r][1] is None else self.highlighted_cells[r][1]
                    elif r in actual_selected_rows:
                        tf = self.selected_rows_fg
                    elif r in selected_rows or selected_cols:
                        tf = self.selected_cells_foreground
                    elif r in self.highlighted_cells:
                        self.create_rectangle(0, fr + 1, self.current_width - 1, sr, fill = self.highlighted_cells[r][0], outline = "", tags = "s")
                        tf = self.text_color if self.highlighted_cells[r][1] is None else self.highlighted_cells[r][1]
                    else:
                        tf = self.text_color
                    try:
                        if isinstance(self.MT.my_row_index, int):
                            if isinstance(self.MT.data_ref[r][self.MT.my_row_index], str):
                                lns = self.MT.data_ref[r][self.MT.my_row_index].split("\n")
                            else:
                                lns = (f"{self.MT.data_ref[r][self.MT.my_row_index]}", )
                        else:
                            if isinstance(self.MT.my_row_index[r], str):
                                lns = self.MT.my_row_index[r].split("\n")
                            else:
                                lns = (f"{self.MT.my_row_index[r]}", )
                    except:
                        lns = (f"{r + 1}", )
                    y = fr + self.MT.fl_ins
                    if y + self.MT.half_txt_h > y1:
                        fl = lns[0]
                        t = self.create_text(x, y, text = fl, fill = tf, font = self.MT.my_font, anchor = "w", tags = "t")
                        wd = self.bbox(t)
                        wd = wd[2] - wd[0]
                        if wd > mw:
                            nl = int(len(fl) * (mw / wd)) - 1
                            self.itemconfig(t, text = fl[:nl])
                            wd = self.bbox(t)
                            while wd[2] - wd[0] > mw:
                                nl -= 1
                                self.dchars(t, nl)
                                wd = self.bbox(t)
                    if len(lns) > 1:
                        stl = int((y1 - y) / self.MT.xtra_lines_increment) - 1
                        if stl < 1:
                            stl = 1
                        y += (stl * self.MT.xtra_lines_increment)
                        if y + self.MT.half_txt_h < sr:
                            for i in range(stl, len(lns)):
                                txt = lns[i]
                                t = self.create_text(x, y, text = txt, fill = tf, font = self.MT.my_font, anchor = "w", tags = "t")
                                wd = self.bbox(t)
                                wd = wd[2] - wd[0]
                                if wd > mw:
                                    nl = int(len(txt) * (mw / wd)) - 1
                                    self.itemconfig(t, text = txt[:nl])
                                    wd = self.bbox(t)
                                    while wd[2] - wd[0] > mw:
                                        nl -= 1
                                        self.dchars(t, nl)
                                        wd = self.bbox(t)
                                y += self.MT.xtra_lines_increment
                                if y + self.MT.half_txt_h > sr:
                                    break
            self.create_line(self.current_width - 1, y1, self.current_width - 1, y_stop, fill = self.row_index_border_color, width = 1, tags = "v")
        except:
            return

    def GetCellCoords(self, event = None, r = None, c = None):
        pass

    
