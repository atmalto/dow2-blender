import re


def float_list_from_text(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [float(item) for item in value]
    return [float(item) for item in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", str(value))]


def transform_rows_and_translation(transform_values):
    values = list(transform_values or [])
    if len(values) < 12:
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], [0.0, 0.0, 0.0]
    rows = [values[0:3], values[3:6], values[6:9]]
    translation = values[9:12]
    return rows, translation


def matrix3x3_to_quat(matrix_rows):
    trace = matrix_rows[0][0] + matrix_rows[1][1] + matrix_rows[2][2]

    if trace > 0:
        scale = 0.5 / (trace + 1.0) ** 0.5
        w = 0.25 / scale
        x = (matrix_rows[2][1] - matrix_rows[1][2]) * scale
        y = (matrix_rows[0][2] - matrix_rows[2][0]) * scale
        z = (matrix_rows[1][0] - matrix_rows[0][1]) * scale
    elif matrix_rows[0][0] > matrix_rows[1][1] and matrix_rows[0][0] > matrix_rows[2][2]:
        scale = 2.0 * (1.0 + matrix_rows[0][0] - matrix_rows[1][1] - matrix_rows[2][2]) ** 0.5
        w = (matrix_rows[2][1] - matrix_rows[1][2]) / scale
        x = 0.25 * scale
        y = (matrix_rows[0][1] + matrix_rows[1][0]) / scale
        z = (matrix_rows[0][2] + matrix_rows[2][0]) / scale
    elif matrix_rows[1][1] > matrix_rows[2][2]:
        scale = 2.0 * (1.0 + matrix_rows[1][1] - matrix_rows[0][0] - matrix_rows[2][2]) ** 0.5
        w = (matrix_rows[0][2] - matrix_rows[2][0]) / scale
        x = (matrix_rows[0][1] + matrix_rows[1][0]) / scale
        y = 0.25 * scale
        z = (matrix_rows[1][2] + matrix_rows[2][1]) / scale
    else:
        scale = 2.0 * (1.0 + matrix_rows[2][2] - matrix_rows[0][0] - matrix_rows[1][1]) ** 0.5
        w = (matrix_rows[1][0] - matrix_rows[0][1]) / scale
        x = (matrix_rows[0][2] + matrix_rows[2][0]) / scale
        y = (matrix_rows[1][2] + matrix_rows[2][1]) / scale
        z = 0.25 * scale

    length = (x * x + y * y + z * z + w * w) ** 0.5
    if length > 0:
        x /= length
        y /= length
        z /= length
        w /= length

    return (x, y, z, w)