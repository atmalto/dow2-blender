#ifndef HAVOK_SCENE_APP_DIALOG_FORM_UTILS_H
#define HAVOK_SCENE_APP_DIALOG_FORM_UTILS_H

class QGridLayout;
class QLabel;
class QSlider;
class QString;

namespace DialogFormUtils
{
    extern const float kPositionSliderScale;
    extern const float kRotationSliderScale;

    struct SliderRow
    {
        QSlider* slider;
        QLabel* value_label;
    };

    void assign_user_axes(float destination[3], float x_value, float y_value, float z_value);
    void extract_user_axes(const float source[3], float* x_value, float* y_value, float* z_value);
    SliderRow add_slider_row(
        QGridLayout* layout,
        int row,
        const QString& text,
        int minimum,
        int maximum,
        int value,
        int tick_interval);
}

#endif