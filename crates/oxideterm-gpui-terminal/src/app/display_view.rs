use super::*;

#[derive(Clone, Debug, Default)]
struct DisplayRowMap {
    source_rows: Vec<usize>,
    member_starts: Vec<usize>,
}

#[derive(Default)]
pub(super) struct DisplayView {
    snapshot: Option<TerminalSnapshot>,
    rows: Vec<DisplayRowMap>,
    source_generation: u64,
    source_scrollback_lines: usize,
    max_display_cols: usize,
    reset_generation: u64,
}

impl DisplayView {
    pub(super) fn active(&self) -> bool {
        self.snapshot.is_some()
    }

    pub(super) fn snapshot(&self) -> Option<&TerminalSnapshot> {
        self.snapshot.as_ref()
    }

    pub(super) fn invalidate(&mut self) {
        self.source_generation = 0;
    }

    pub(super) fn refresh(&mut self, base: &TerminalSnapshot, enabled: bool) -> bool {
        if !enabled {
            let reset = self.snapshot.is_some() || self.max_display_cols != 0;
            self.snapshot = None;
            self.rows.clear();
            self.source_scrollback_lines = base.scrollback_lines;
            self.max_display_cols = 0;
            self.reset_generation = base.buffer_reset_generation;
            return reset;
        }
        if self.source_generation == base.generation
            && self.source_scrollback_lines == base.scrollback_lines
            && self.reset_generation == base.buffer_reset_generation
            && self.snapshot.is_some()
        {
            return false;
        }
        let reset = self.reset_generation != base.buffer_reset_generation
            || base.scrollback_lines < self.source_scrollback_lines;
        if reset {
            self.max_display_cols = 0;
            self.reset_generation = base.buffer_reset_generation;
        }
        self.source_generation = base.generation;
        self.source_scrollback_lines = base.scrollback_lines;
        self.rows.clear();

        let mut result = base.clone();
        result.lines.clear();
        result.logical_context.clear();
        result.images.clear();
        result.cursor_row = usize::MAX;
        let mut pending_contexts = Vec::new();
        let mut source_row = 0;
        while source_row < base.lines.len() {
            let mut end = source_row + 1;
            while end < base.lines.len()
                && base.lines[end - 1].wrapped
                && base.lines[end].absolute_line == base.lines[end - 1].absolute_line + 1
            {
                end += 1;
            }
            let image_in_chain = base.images.iter().any(|image| {
                let image_end = image.row.saturating_add(image.rows);
                image.row < end && image_end > source_row
            });
            if end == source_row + 1 || image_in_chain {
                for physical in source_row..end {
                    let display_row = result.lines.len();
                    self.rows.push(DisplayRowMap {
                        source_rows: vec![physical],
                        member_starts: vec![0],
                    });
                    if physical == base.cursor_row {
                        result.cursor_row = display_row;
                        result.cursor_col = base.cursor_col;
                    }
                    self.max_display_cols = self
                        .max_display_cols
                        .max(display_width(&base.lines[physical]));
                    result.lines.push(base.lines[physical].clone());
                    self.map_images(base, physical, display_row, 0, &mut result.images);
                }
                source_row = end;
                continue;
            }

            let display_row = result.lines.len();
            let first = &base.lines[source_row];
            let mut row = first.clone();
            row.wrapped = false;
            row.trailing_wide_char_spacer = false;
            row.active_input = false;
            row.cells = Arc::new(Vec::new());
            let mut cells = Vec::new();
            let mut text = zeroize::Zeroizing::new(String::new());
            let mut columns = Vec::new();
            let mut map = DisplayRowMap::default();
            let mut hasher = DefaultHasher::new();
            for physical in source_row..end {
                let source = &base.lines[physical];
                source.source_id.hash(&mut hasher);
                source.signature.hash(&mut hasher);
                row.active_input |= source.active_input;
                map.member_starts.push(cells.len());
                map.source_rows.push(physical);
                let take = source
                    .cells
                    .len()
                    .saturating_sub(usize::from(source.trailing_wide_char_spacer));
                for cell in &source.cells[..take] {
                    let display_col = cells.len();
                    columns.push((text.len(), display_col));
                    text.push(cell.ch);
                    for ch in cell.zerowidth().chars() {
                        text.push(ch);
                        columns.push((text.len(), display_col));
                    }
                    cells.push(cell.clone());
                }
                if physical == base.cursor_row {
                    result.cursor_row = display_row;
                    result.cursor_col =
                        map.member_starts.last().copied().unwrap_or(0) + base.cursor_col;
                }
            }
            row.signature = hasher.finish();
            row.cells = Arc::new(cells);
            self.max_display_cols = self.max_display_cols.max(display_width(&row));
            let absolute_display_line = result
                .scrollback_lines
                .saturating_sub(result.window_display_offset())
                + display_row;
            pending_contexts.push(oxideterm_terminal::TerminalLogicalContext {
                text: Arc::new(text),
                signature: row.signature,
                cols: 0,
                members: Arc::new(Vec::new()),
                start_line: absolute_display_line,
                end_line: absolute_display_line,
                active_input: row.active_input,
                start_at_history_boundary: first.absolute_line == -(base.scrollback_lines as i64),
                rows: vec![oxideterm_terminal::TerminalLogicalContextRow {
                    source_id: row.source_id,
                    columns: Arc::new(columns),
                }],
            });
            result.lines.push(row);
            self.rows.push(map);
            source_row = end;
        }

        result.cols = self.max_display_cols;
        for mut context in pending_contexts {
            context.cols = result.cols;
            result.logical_context.push(Arc::new(context));
        }
        self.snapshot = Some(result);
        reset
    }

    fn map_images(
        &self,
        base: &TerminalSnapshot,
        source_row: usize,
        display_row: usize,
        display_col: usize,
        images: &mut Vec<TerminalImageSnapshot>,
    ) {
        images.extend(base.images.iter().filter_map(|image| {
            (image.row == source_row).then(|| {
                let mut image = image.clone();
                image.row = display_row;
                image.col += display_col;
                image
            })
        }));
    }

    pub(super) fn physical_point(&self, point: TerminalPoint) -> Option<TerminalPoint> {
        let map = self.rows.get(point.row)?;
        let member = map
            .member_starts
            .partition_point(|start| *start <= point.col)
            .saturating_sub(1);
        let source_row = *map.source_rows.get(member)?;
        let start = *map.member_starts.get(member)?;
        let source = self.snapshot.as_ref()?.lines.get(point.row)?;
        let next_start = map
            .member_starts
            .get(member + 1)
            .copied()
            .unwrap_or(source.cells.len());
        let source_len = next_start.saturating_sub(start);
        Some(TerminalPoint {
            row: source_row,
            col: point
                .col
                .saturating_sub(start)
                .min(source_len.saturating_sub(1)),
        })
    }

    pub(super) fn display_point(&self, point: TerminalPoint) -> Option<TerminalPoint> {
        self.rows.iter().enumerate().find_map(|(row, map)| {
            let member = map
                .source_rows
                .iter()
                .position(|source| *source == point.row)?;
            let start = *map.member_starts.get(member)?;
            Some(TerminalPoint {
                row,
                col: start + point.col,
            })
        })
    }

    pub(super) fn physical_row(&self, display_row: usize) -> Option<usize> {
        self.rows.get(display_row)?.source_rows.first().copied()
    }
}

fn display_width(row: &TerminalRow) -> usize {
    row.cells
        .iter()
        .rposition(|cell| cell.cursor || terminal_cell_has_content(cell))
        .map_or(0, |column| column + 1)
}

#[cfg(test)]
mod tests {
    use super::*;
    use oxideterm_terminal::{TerminalAttrs, TerminalColor, TerminalStyleOrigin};

    fn row(absolute_line: i64, text: &str, wrapped: bool, trailing_spacer: bool) -> TerminalRow {
        let mut row = TerminalRow {
            line_id: absolute_line.max(0) as u64 + 1,
            source_id: absolute_line.max(0) as usize + 1,
            absolute_line,
            cells: Arc::new(
                text.chars()
                    .map(|ch| TerminalCell {
                        ch,
                        wide: false,
                        fg: TerminalColor::rgb(0xff, 0xff, 0xff),
                        bg: TerminalColor::rgb(0, 0, 0),
                        style_origin: TerminalStyleOrigin::default(),
                        attrs: TerminalAttrs::default(),
                        extra: None,
                        cursor: false,
                    })
                    .collect(),
            ),
            wrapped,
            trailing_wide_char_spacer: trailing_spacer,
            active_input: false,
            signature: 0,
        };
        row.refresh_signature();
        row
    }

    fn snapshot(lines: Vec<TerminalRow>) -> TerminalSnapshot {
        TerminalSnapshot {
            logical_context: Vec::new(),
            generation: 1,
            buffer_reset_generation: 0,
            cols: 4,
            rows: 2,
            cursor_col: 0,
            cursor_row: 1,
            cursor_shape: oxideterm_terminal::TerminalCursorShape::Block,
            display_offset: 0,
            scrollback_lines: 0,
            lines,
            images: Vec::new(),
        }
    }

    #[test]
    fn joined_row_drops_only_the_wrap_spacer_and_maps_both_directions() {
        let base = snapshot(vec![
            row(0, "abcd ", true, true),
            row(1, "界 ", false, false),
        ]);
        let mut view = DisplayView::default();
        view.refresh(&base, true);
        let displayed = view.snapshot().unwrap();
        assert_eq!(displayed.lines.len(), 1);
        assert_eq!(displayed.lines[0].text(), "abcd界 ");
        assert_eq!((displayed.cursor_row, displayed.cursor_col), (0, 4));
        assert_eq!(
            view.physical_point(TerminalPoint { row: 0, col: 4 }),
            Some(TerminalPoint { row: 1, col: 0 })
        );
        assert_eq!(
            view.display_point(TerminalPoint { row: 1, col: 1 }),
            Some(TerminalPoint { row: 0, col: 5 })
        );
    }

    #[test]
    fn changing_any_chain_member_invalidates_the_joined_signature() {
        let mut base = snapshot(vec![
            row(0, "abcd", true, false),
            row(1, "efgh", false, false),
        ]);
        let mut view = DisplayView::default();
        view.refresh(&base, true);
        let before = view.snapshot().unwrap().lines[0].signature;
        base.generation = 2;
        base.lines[1].cells_mut()[0].ch = 'x';
        base.lines[1].refresh_signature();
        view.refresh(&base, true);
        assert_ne!(view.snapshot().unwrap().lines[0].signature, before);
        assert_eq!(view.snapshot().unwrap().lines[0].text(), "abcdxfgh");
    }

    #[test]
    fn no_wrap_width_ignores_blank_grid_and_keeps_styled_blanks() {
        let mut base = snapshot(vec![row(0, "ab   ", false, false)]);
        let mut view = DisplayView::default();
        view.refresh(&base, true);
        assert_eq!(view.snapshot().unwrap().cols, 2);

        base.generation = 2;
        base.lines[0].cells_mut()[4].style_origin =
            oxideterm_terminal::TerminalStyleOrigin::new(false, true);
        base.lines[0].refresh_signature();
        view.refresh(&base, true);
        assert_eq!(view.snapshot().unwrap().cols, 5);
    }

    #[test]
    fn scrollback_shrink_resets_the_horizontal_high_water() {
        let mut base = snapshot(vec![
            row(-1, "abcd", true, false),
            row(0, "efgh", false, false),
        ]);
        base.scrollback_lines = 8;
        let mut view = DisplayView::default();
        view.refresh(&base, true);
        assert_eq!(view.snapshot().unwrap().cols, 8);

        base.generation = 2;
        base.lines = vec![row(0, "ab", false, false)];
        base.cursor_row = 0;
        assert!(!view.refresh(&base, true));
        assert_eq!(view.snapshot().unwrap().cols, 8);

        base.generation = 3;
        base.scrollback_lines = 4;
        assert!(view.refresh(&base, true));
        assert_eq!(view.snapshot().unwrap().cols, 4);
    }
}
