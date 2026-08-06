from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict


class MaterialNodeLayoutEngine:
    """Applies a compact graph layout that avoids overlapping node stacks."""

    column_spacing = 150.0
    row_spacing = 110.0
    min_node_height = 150.0

    def organize(self, ctx: Any) -> None:
        node_list = [node for node in ctx.nodes if getattr(node, 'parent', None) is None]
        if not node_list:
            return

        upstream = defaultdict(set)
        downstream = defaultdict(set)
        for link in ctx.links:
            if link.from_node == link.to_node:
                continue
            upstream[link.to_node].add(link.from_node)
            downstream[link.from_node].add(link.to_node)

        columns: Dict[Any, int] = {ctx.output: 0}
        queue = deque([ctx.output])
        while queue:
            node = queue.popleft()
            node_column = columns[node]
            for source_node in upstream.get(node, ()): 
                next_column = node_column + 1
                if next_column > columns.get(source_node, -1):
                    columns[source_node] = next_column
                    queue.append(source_node)

        max_column = max(columns.values(), default=1)
        for node in node_list:
            if node in columns:
                continue
            linked_columns = [columns[target] + 1 for target in downstream.get(node, ()) if target in columns]
            if linked_columns:
                columns[node] = max(linked_columns)
                continue
            if node.bl_idname == 'ShaderNodeTexImage':
                columns[node] = max_column + 1
            elif node.bl_idname == 'ShaderNodeUVMap':
                columns[node] = max_column + 2
            else:
                columns[node] = max_column + 1

        fixed_positions = {
            ctx.output: (float(ctx.output.location.x), float(ctx.output.location.y)),
        }

        columns_by_index = defaultdict(list)
        for node, column in columns.items():
            if node in fixed_positions:
                continue
            columns_by_index[column].append(node)

        max_widths = {
            column: max(self._estimate_node_width(node) for node in column_nodes)
            for column, column_nodes in columns_by_index.items()
        }
        x_positions = {0: float(ctx.output.location.x)}
        max_column_index = max(columns.values(), default=0)
        for column in range(1, max_column_index + 1):
            x_positions[column] = (
                x_positions[column - 1]
                - max_widths.get(column, 200.0)
                - self.column_spacing
            )

        for column, column_nodes in columns_by_index.items():
            column_nodes.sort(key=lambda node: (-float(node.location.y), self._node_sort_key(node)))
            total_height = sum(self._estimate_node_height(node) for node in column_nodes)
            total_height += self.row_spacing * max(len(column_nodes) - 1, 0)
            center_y = sum(float(node.location.y) for node in column_nodes) / max(len(column_nodes), 1)
            y_cursor = center_y + (total_height / 2.0)
            x_position = x_positions.get(column, float(ctx.output.location.x) - (column * 320.0))

            for node in column_nodes:
                node_height = self._estimate_node_height(node)
                node.location = (x_position, y_cursor)
                y_cursor -= node_height + self.row_spacing

        for node, location in fixed_positions.items():
            node.location = location

    def _estimate_node_height(self, node: Any) -> float:
        dimensions = getattr(node, 'dimensions', None)
        if dimensions is not None:
            measured = float(getattr(dimensions, 'y', 0.0) or 0.0)
            if measured > 1.0:
                return max(measured, self.min_node_height)
        socket_count = max(len(getattr(node, 'inputs', ())), len(getattr(node, 'outputs', ())), 3)
        estimated = 70.0 + (socket_count * 26.0)
        height = float(getattr(node, 'height', self.min_node_height) or self.min_node_height)
        return max(height, estimated, self.min_node_height)

    @staticmethod
    def _estimate_node_width(node: Any) -> float:
        dimensions = getattr(node, 'dimensions', None)
        if dimensions is not None:
            measured = float(getattr(dimensions, 'x', 0.0) or 0.0)
            if measured > 1.0:
                return max(measured, 180.0)
        width = float(getattr(node, 'width', 180.0) or 180.0)
        return max(width, 180.0)

    @staticmethod
    def _node_sort_key(node: Any) -> tuple[int, str]:
        priority = 0
        if node.bl_idname == 'ShaderNodeTexImage':
            priority = 2
        elif node.bl_idname == 'ShaderNodeUVMap':
            priority = 1
        return (priority, getattr(node, 'name', ''))


def organize_material_nodes(ctx: Any) -> None:
    MaterialNodeLayoutEngine().organize(ctx)


__all__ = [
    "MaterialNodeLayoutEngine",
    "organize_material_nodes",
]